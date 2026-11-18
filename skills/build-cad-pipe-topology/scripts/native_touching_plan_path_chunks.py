"""Read exactly touching chunks of an existing floor-plan edge privately.

No graph connections, source geometry, gap spans or physical nodes are added.
The historical native coverage and metric kernels run on a private continuous
path; every resulting piece is mapped back to its original path/segment ID.
"""
import argparse,copy,hashlib,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_path_coverage_audit import audit as native_audit
from native_plan_projection_lengths import unit_evidence,lengths

MODE='native_exactly_touching_floor_plan_path_chunks_v1'


def project(graph,selected,floor):
    if isinstance(floor,bool) or not isinstance(floor,int) or not selected or len(set(selected))!=len(selected):
        raise ValueError('explicit distinct edges and one floor required')
    nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']}
    if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']):raise ValueError('duplicate graph identity')
    out=copy.deepcopy(graph);target={e['edge_id']:e for e in out['edges']};proof=[];locations={}
    for eid in selected:
        edge=edges.get(eid)
        if (not edge or edge.get('system') not in ('supply','return') or edge.get('source_view_context') is not None
            or 'source_wave_omission' in edge or 'omission' in (edge.get('connection_mode') or '')
            or any(nodes.get(edge.get(k),{}).get('floor')!=floor for k in ('start_node_id','end_node_id'))):
            raise ValueError('only current same-floor pipe edges without omitted/detail scope are supported')
        paths=edge.get('attribute_paths',[])
        if not paths or any(len(p)<2 for p in paths):raise ValueError('empty path chunk')
        if any(any(len(p)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in p) for p in path) for path in paths):
            raise ValueError('invalid native path point')
        if any(a[-1]!=b[0] for a,b in zip(paths,paths[1:])):raise ValueError('path chunks do not touch exactly; no gap recovery here')
        joined=list(paths[0]);mapping=[];segments=[]
        for pi,path in enumerate(paths):
            if pi:joined.extend(path[1:])
            for si,(a,b) in enumerate(zip(path,path[1:])):
                if math.dist(a,b)<=.05:raise ValueError('zero or short repeated path segment')
                for c,d in segments:
                    u=[b[i]-a[i] for i in range(2)];v=[d[i]-c[i] for i in range(2)];lu=math.dist(a,b);lv=math.dist(c,d)
                    cross=lambda x,y:x[0]*y[1]-x[1]*y[0]
                    if abs(cross(u,v))<=1e-9*lu*lv and abs(cross([c[i]-a[i] for i in range(2)],u))/lu<=.05:
                        ts=sorted(sum((p[i]-a[i])*u[i] for i in range(2))/lu for p in (c,d))
                        if min(lu,ts[1])-max(0,ts[0])>.05:raise ValueError('overlapping or retraced path pieces would double count')
                index=len(mapping);mapping.append(dict(projection_segment_index=index,path_index=pi,segment_index=si,points=[a,b]))
                locations[(eid,index)]=mapping[-1];segments.append((a,b))
        target[eid]['attribute_paths']=[joined]
        proof.append(dict(edge_id=eid,original_attribute_paths=copy.deepcopy(paths),projection_path=joined,segment_map=mapping,
            join_points=[a[-1] for a in paths[:-1]],added_span_units=0,physical_nodes_added=0,physical_edges_added=0))
    return out,proof,locations


def evaluate(doc,graph,policy,source_hash,graph_hash):
    if (policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash
        or graph.get('metadata',{}).get('source_sha256')!=source_hash or policy.get('view_kind')!='floor_plan'):
        raise ValueError('native floor-plan source scope differs')
    projection,proof,locations=project(graph,policy['edges'],policy['floor'])
    ph=hashlib.sha256(encode(projection)).hexdigest()
    coverage=native_audit(doc,projection,dict(source_sha256=source_hash,graph_sha256=ph,edges=policy['edges']),source_hash,ph)
    if any(s['status']!='single_source_line_covers' for e in coverage['edges'] for s in e['segments']):
        raise ValueError('touching path pieces lack unique native same-system LINE coverage')
    return projection,dict(mode=MODE,status='native_touching_chunks_read_only_geometry_replayed_not_connectivity_acceptance',
        source_sha256=source_hash,graph_sha256=graph_hash,private_projection_sha256=ph,normalizations=proof,coverage=coverage,
        local_graph_mutated=False,physical_connections_added=0,installed_lengths_assigned=0,human_accepted=False),locations


def collect(doc,graph,policy,source_hash,graph_hash):
    return evaluate(doc,graph,policy,source_hash,graph_hash)[1]


def measured_scopes(doc,graph,policy,metric_policy,source_hash,graph_hash):
    projection,proof,locations=evaluate(doc,graph,policy,source_hash,graph_hash)
    units=unit_evidence(doc,metric_policy);records=policy.get('records',[])
    claimed=[eid for row in records for eid in row['plan_edges']]
    if not records or len(set(claimed))!=len(claimed) or set(claimed)!=set(policy['edges']):raise ValueError('exact non-overlapping metric records required')
    measured=[];edges={e['edge_id']:e for e in graph['edges']}
    for row in records:
        if isinstance(row.get('floor'),bool) or row.get('floor')!=policy['floor']:raise ValueError('metric record floor differs')
        result=lengths(projection,proof['coverage'],row,units)
        for piece in result['pieces']:
            original=locations[(piece['plan_edge'],piece['segment_index'])]
            if original['points']!=piece['points']:raise ValueError('private metric no longer matches original segment')
            piece.update(projection_segment_index=piece['segment_index'],path_index=original['path_index'],segment_index=original['segment_index'])
            if edges[piece['plan_edge']]['attribute_paths'][piece['path_index']][piece['segment_index']:piece['segment_index']+2]!=piece['points']:
                raise ValueError('metric piece lost original path identity')
        measured.append(dict(scope_id=row['scope_id'],system=row['system'],floor=row['floor'],plan_edges=row['plan_edges'],horizontal_projection=result,
            added_span_units=0,installed_whole_edge_length_mm=None,human_accepted=False))
    return dict(proof,metric_evidence=units,measured_scopes=measured)


def compute(paths):
    policy=load(paths['policy'])
    for key in ('source','graph','metric_policy'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('touching path input changed '+key)
    doc,preflight=read_source(paths['source'])
    result=measured_scopes(doc,load(paths['graph']),policy,load(paths['metric_policy']),sha(paths['source']),sha(paths['graph']))
    return dict(result,source_preflight=preflight)


def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in ('native_touching_plan_path_chunks.py','native_path_coverage_audit.py',
        'native_plan_projection_lengths.py','native_line_path_evidence.py','source_readability.py')}


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'touching-path-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('touching path implementation changed')
    for row in receipt['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('touching path evidence input changed')
    result=compute({k:v['path'] for k,v in receipt['inputs'].items()});target=directory/'touching-path-evidence.json'
    if encode(result)!=target.read_bytes() or sha(target)!=receipt['output_sha256']:raise ValueError('touching path native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','policy','metric-policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths={k:getattr(a,k) for k in ('source','graph','policy','metric_policy')}
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths);a.output.mkdir(parents=True);target=a.output/'touching-path-evidence.json';target.write_bytes(encode(result))
    (a.output/'touching-path-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(dict(measured_scopes=len(result['measured_scopes']),original_graph_mutated=False,physical_connections_added=0),flush=True)


if __name__=='__main__':main()
