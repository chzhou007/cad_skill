"""Find source-wave omission candidates without changing topology.

The native block and expert control are deliberately explicit inputs.  A wave
mark can also be a terminal, so a screen result is never an accepted join.
"""
import hashlib
import json
import math
from pathlib import Path
from ezdxf import bbox


def block_fingerprint(block):
    entities=[]
    for entity in block:
        if entity.dxftype() != 'LWPOLYLINE':
            raise ValueError('wave block has unsupported geometry')
        entities.append({'type':'LWPOLYLINE', 'closed':entity.closed,
                         'points':[list(map(float,p)) for p in entity.get_points('xyb')]})
    if len(entities)!=1 or len(entities[0]['points'])!=3:
        raise ValueError('wave block fingerprint is not calibrated')
    return hashlib.sha256(json.dumps(entities,sort_keys=True).encode('utf8')).hexdigest()


def screen(doc, graph, *, block_name, expected_fingerprint, max_gap,
           contact_tolerance=.5, axis_cosine=.9999):
    if not 0 < contact_tolerance <= 1 or not 0 < max_gap <= 350 or not .99 <= axis_cosine <= 1:
        raise ValueError('invalid candidate-screen tolerances')
    block=doc.blocks.get(block_name)
    if block is None or block_fingerprint(block)!=expected_fingerprint:
        raise ValueError('wave source block differs from calibrated control')
    waves=[i for i in doc.modelspace().query('INSERT') if i.dxf.name==block_name]
    edges=graph['edges']; endpoints=[]
    for n in graph['nodes']:
        if n.get('subtype')!='unresolved_source_terminal' or n.get('system') not in ('supply','return'):
            continue
        incident=[e for e in edges if n['node_id'] in (e['start_node_id'],e['end_node_id'])]
        if len(incident)!=1 or incident[0].get('system')!=n['system']:
            continue
        e=incident[0]; path=e.get('path_points') or e.get('path') or []
        if e['end_node_id']==n['node_id']: path=list(reversed(path))
        p=(n['x'],n['y'])
        if not path or math.dist(p,path[0][:2])>contact_tolerance: continue
        q=next((x[:2] for x in path[1:] if math.dist(p,x[:2])>contact_tolerance),None)
        if q is None: continue
        norm=math.dist(p,q);outward=((p[0]-q[0])/norm,(p[1]-q[1])/norm)
        matches=[]
        for wave in waves:
            if math.hypot(wave.dxf.insert.x-p[0],wave.dxf.insert.y-p[1])>contact_tolerance:continue
            parts=list(wave.virtual_entities())
            if len(parts)!=1 or parts[0].dxftype()!='LWPOLYLINE' or len(parts[0])!=3:continue
            box=bbox.extents(parts)
            if box.extmin.x-contact_tolerance<=p[0]<=box.extmax.x+contact_tolerance and box.extmin.y-contact_tolerance<=p[1]<=box.extmax.y+contact_tolerance:
                matches.append(wave.dxf.handle)
        if len(matches)==1:
            endpoints.append({'node_id':n['node_id'],'system':n['system'],'floor':n.get('floor'),
                              'xy':p,'outward':outward,'edge_id':e['edge_id'],
                              'pipe_handles':n.get('source_handles',[]),'wave_handle':matches[0]})
    candidates=[]
    for index,a in enumerate(endpoints):
        for b in endpoints[index+1:]:
            if a['system']!=b['system'] or a['floor']!=b['floor'] or a['edge_id']==b['edge_id']:continue
            dx=b['xy'][0]-a['xy'][0];dy=b['xy'][1]-a['xy'][1];gap=math.hypot(dx,dy)
            if not contact_tolerance<gap<=max_gap:continue
            u=(dx/gap,dy/gap)
            if sum(x*y for x,y in zip(a['outward'],u))<axis_cosine:continue
            if sum(x*y for x,y in zip(b['outward'],u))>-axis_cosine:continue
            candidates.append({'a':a['node_id'],'b':b['node_id'],'system':a['system'],
                               'wave_handles':[a['wave_handle'],b['wave_handle']],
                               'gap_native_units':gap,'status':'candidate_only'})
    degree={n['node_id']:sum(n['node_id'] in (p['a'],p['b']) for p in candidates) for n in endpoints}
    for p in candidates:p['unique_for_each_endpoint']=degree[p['a']]==degree[p['b']]==1
    return {'wave_endpoints':endpoints,'candidate_pairs':candidates,'graph_mutated':False,
            'human_accepted':False,'physical_omission_length':'unknown'}


def main():
    import argparse
    from source_readability import read_source
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--graph',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--block-name',required=True)
    parser.add_argument('--fingerprint',required=True)
    parser.add_argument('--max-gap',type=float,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    doc,proof=read_source(args.source)
    graph_bytes=args.graph.read_bytes()
    graph=json.loads(graph_bytes.decode('utf8'))
    result=screen(doc,graph,block_name=args.block_name,expected_fingerprint=args.fingerprint,max_gap=args.max_gap)
    result.update(source_sha256=proof['source_sha256'],graph_sha256=hashlib.sha256(graph_bytes).hexdigest(),
                  source_block_name=args.block_name,source_block_fingerprint=args.fingerprint,
                  max_gap_native_units=args.max_gap)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'candidate_pairs':len(result['candidate_pairs']),'wave_endpoints':len(result['wave_endpoints']),
                      'graph_mutated':False},ensure_ascii=False))

if __name__=='__main__':main()
