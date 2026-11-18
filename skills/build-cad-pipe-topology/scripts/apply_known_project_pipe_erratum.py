"""Replay an explicitly pinned project drawing erratum; no general circle rule.

The geometry/component implementation inherits the source-checked SH16 corner
repair, parameterized by an explicit expert context and bounded pair policy.
"""
import argparse,copy,csv,io,json,math
from collections import Counter
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from edge_endpoint_semantics import reconcile
from native_line_path_evidence import LAYERS

MODE='explicit_project_circle_erratum'

def repair(doc,graph,rows,issue,context,policy,issue_digest):
    source_hash=policy["source_sha256"];specs=policy["pairs"];project=policy["project_scope"]
    if graph.get('metadata',{}).get('source_sha256')!=source_hash or issue['sourceHashes']['main_dxf']!=source_hash:
        raise ValueError('SH16-10 native source identity mismatch')
    if issue['issue']['id']!=policy['issue_id'] or not issue['issue']['note']:
        raise ValueError('missing project-specific expert erratum')
    g=copy.deepcopy(graph);rows=copy.deepcopy(rows)
    nodes={n['node_id']:n for n in g['nodes']};edges={e['edge_id']:e for e in g['edges']}
    old_nodes={n['node_id']:n for n in context['nodes']};old_edges={e['edge_id']:e for e in context['edges']}
    mapping={};retired=[];records=[]
    for spec in specs:
        u,v=(nodes[n] for n in spec['nodes']);left,right=(edges[e] for e in spec['edges'])
        for n,e,h in zip((u,v),(left,right),spec['lines']):
            if n['node_id'] not in issue['issue']['nodes'] or e['edge_id'] not in issue['issue']['edges']:
                raise ValueError('outside explicitly marked scope')
            before=old_nodes[n['node_id']]
            if any(n.get(k)!=before.get(k) for k in ('node_id','system','x','y','source_handles')):
                raise ValueError('node no longer matches expert context')
            if any(e.get(k)!=old_edges[e['edge_id']].get(k) for k in ('start_node_id','end_node_id','system','path','attribute_paths','source_handles')):
                raise ValueError('edge no longer matches expert context')
            if n.get('subtype')!='unresolved_source_terminal' or n.get('system')!=spec['system'] or e['system']!=spec['system']:
                raise ValueError('wrong system or physical endpoint')
            if sum(n['node_id'] in (x['start_node_id'],x['end_node_id']) for x in edges.values())!=1:
                raise ValueError('erratum endpoint is not a leaf')
            native=doc.entitydb.get(h)
            if (not native or native.dxftype()!='LINE' or native not in doc.modelspace()
                or native.dxf.layer!=LAYERS[spec['system']] or h not in e['source_handles']
                or min(math.dist([p.x,p.y],[n['x'],n['y']]) for p in (native.dxf.start,native.dxf.end))>.05):
                raise ValueError('native pipe contact changed')
            if any(k.startswith('diameter_') or k in ('pipe_diameter','source_segment_dimensions','source_path_coverage') for k in e):
                raise ValueError('new attributes require explicit remapping')
        circle=doc.entitydb.get(spec['circle'])
        if (not circle or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace()
            or circle.dxf.layer!=LAYERS[spec['system']] or abs(circle.dxf.radius-100)>.05
            or math.dist([circle.dxf.center.x,circle.dxf.center.y],[v['x'],v['y']])>.05
            or abs(math.dist([u['x'],u['y']],[v['x'],v['y']])-100)>.05):
            raise ValueError('native redundant-circle geometry changed')
        def other(e,n):return e['end_node_id'] if e['start_node_id']==n else e['start_node_id']
        a,b=other(left,u['node_id']),other(right,v['node_id'])
        if a==b:raise ValueError('would create unintended loop')
        def path_from(e,start):return copy.deepcopy(e['path'] if e['start_node_id']==start else list(reversed(e['path'])))
        merged=copy.deepcopy(left)
        # The original paths stay separate; their unshown connector is logical
        # and has no inferred installed length.
        path=path_from(left,a)+path_from(right,v['node_id'])
        for key,value in right.items():
            if key not in merged:merged[key]=copy.deepcopy(value)
        for key in ('source_flexible_joints','source_riser_interfaces','source_expert_riser_connections','source_normalized_crossovers'):
            combined=copy.deepcopy(left.get(key,[])+right.get(key,[]))
            if combined:merged[key]=combined
        merged.update(start_node_id=a,end_node_id=b,path=path,path_points=copy.deepcopy(path),
                      attribute_paths=copy.deepcopy(left['attribute_paths']+right['attribute_paths']),
                      source_handles=list(dict.fromkeys(left['source_handles']+right['source_handles'])),
                      path_length=left['path_length']+right['path_length'],path_length_complete=False,
                      physical_length='unknown',path_length_scope='source_drawn_pipe_only_project_erratum_and_existing_omissions_unknown',
                      connection_mode='expert_confirmed_project_drawing_erratum',
                      equipment_names=left['equipment_names']+right['equipment_names'],
                      equipment_counts=dict(Counter(left['equipment_counts'])+Counter(right['equipment_counts'])),
                      edge_type='tee_to_virtual_equipment' if any(nodes[n]['node_type']=='virtual_equipment' for n in (a,b)) else 'tee_to_tee')
        for key in ('start_port_id','end_port_id'):merged.pop(key,None)
        merged['source_drafting_erratum']=dict(project_scope=project,issue_id=issue['issue']['id'],
             issue_sha256=issue_digest,source_sha256=source_hash,source_circle_handle=spec['circle'],
             source_endpoints=[[u['x'],u['y']],[v['x'],v['y']]],retired_node_ids=spec['nodes'],
             prior_edge_ids=spec['edges'],physical_length='unknown',rule_scope='explicit_project_known_issue_only')
        edges[left['edge_id']]=merged;del edges[right['edge_id']]
        mapping[right['edge_id']]=left['edge_id'];retired.extend(spec['nodes'])
        records.append(dict(system=spec['system'],retained_edge=left['edge_id'],retired_edge=right['edge_id'],retired_nodes=spec['nodes'],circle_handle=spec['circle']))
        for n in spec['nodes']:del nodes[n]
    for row in rows:row['edge_id']=mapping.get(row['edge_id'],row['edge_id'])
    for e in edges.values():
        assigned=[r for r in rows if r['edge_id']==e['edge_id']]
        if Counter(r['device_name'] for r in assigned)!=Counter(e.get('equipment_names',[])):
            raise ValueError('component names not conserved')
        if Counter(r['equipment_type'] for r in assigned)!=Counter(e.get('equipment_counts',{})):
            raise ValueError('component types not conserved')
    g['nodes']=list(nodes.values());g['edges']=list(edges.values())
    g['virtual_equipment_ports']=[p for p in g.get('virtual_equipment_ports',[]) if p.get('virtual_equipment_id') not in retired]
    g,_=reconcile(g)
    g.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_project_known_erratum')
    g['sourceDraftingErrata']=dict(project_scope=project,issue_id=issue['issue']['id'],issue_sha256=issue_digest,
       source_sha256=source_hash,records=records,edge_id_mapping=mapping,retired_node_ids=retired,
       prior_reviews='historical_not_inherited',general_circle_rule_added=False)
    return g,rows,g['sourceDraftingErrata']


def csv_bytes(rows,fields):
    text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    return text.getvalue().encode('utf-8-sig')


def graph_bytes(graph,policy):
    ending=policy.get('graph_newline','LF')
    if ending not in ('LF','CRLF'):raise ValueError('unsupported graph serialization')
    data=encode(graph)
    return data.replace(b'\n',b'\r\n') if ending=='CRLF' else data


def compute(paths,policy):
    if policy.get('rule_scope')!='explicit_project_known_issue_only' or not policy.get('pairs'):raise ValueError('explicit project issue policy required')
    for key in ('source','graph','devices','issue','context'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('project erratum input changed '+key)
    if len({n for s in policy['pairs'] for n in s['nodes']})!=2*len(policy['pairs']) or len({e for s in policy['pairs'] for e in s['edges']})!=2*len(policy['pairs']):raise ValueError('duplicate project erratum scopes')
    from reconstruct_batch_circle_junctions import verify_output as verify_parent
    if verify_parent(Path(paths['graph']).parent)['output_graph_sha256']!=sha(paths['graph']):raise ValueError('project erratum parent differs')
    doc,preflight=read_source(paths['source'])
    with Path(paths['devices']).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    graph,rows,proof=repair(doc,load(paths['graph']),rows,load(paths['issue']),load(paths['context']),policy,sha(paths['issue']))
    return graph,csv_bytes(rows,fields),dict(source_preflight=preflight,records=proof['records'])


def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in ('apply_known_project_pipe_erratum.py','reconstruct_batch_circle_junctions.py','repair_confirmed_circle_junctions.py','edge_endpoint_semantics.py','source_readability.py')}


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'project-known-erratum-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('stale project erratum implementation')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('stale project erratum dependency')
    paths={k:v['path'] for k,v in audit['inputs'].items() if k!='policy'};policy=load(audit['inputs']['policy']['path']);graph,devices,proof=compute(paths,policy)
    if graph_bytes(graph,policy)!=(directory/'graph_with_edges.json').read_bytes() or devices!=(directory/'assigned_edge_device_instances.csv').read_bytes() or audit['output_graph_sha256']!=sha(directory/'graph_with_edges.json') or any(audit[k]!=v for k,v in proof.items()):raise ValueError('project erratum native replay differs')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','devices','issue','context','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths={k:getattr(a,k) for k in ('source','graph','devices','issue','context')}
    if a.output.exists():raise FileExistsError(a.output)
    policy=load(a.policy);graph,devices,proof=compute(paths,policy);a.output.mkdir(parents=True)
    (a.output/'graph_with_edges.json').write_bytes(graph_bytes(graph,policy));(a.output/'assigned_edge_device_instances.csv').write_bytes(devices);paths['policy']=a.policy
    audit=dict(mode=MODE,**proof,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        parent_graph=dict(path=str(a.graph.resolve()),sha256=sha(a.graph)),implementation_sha256=implementation_hashes(),output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'project-known-erratum-audit.json').write_bytes(encode(audit));print(json.dumps(dict(nodes=len(graph['nodes']),edges=len(graph['edges']),records=len(proof['records']),human_accepted=False)))


if __name__=='__main__':main()

