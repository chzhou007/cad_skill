"""Route each axis pipe segment by drawing direction, never by edge floors.

This is an attribute-source inventory, not a connection, length or mapping proof.
Every vertical segment uses the axis source, including local same-floor rises.
Mixed graph edges retain separate horizontal, vertical and unresolved spans.
"""
import argparse,collections,math,importlib
from pathlib import Path
MODE='axis_segment_attribute_source_routing_v1'
def collect(graph,policy):
    angles=policy.get('isometric_horizontal_directions_degrees');tol=policy.get('direction_tolerance_degrees',.1)
    if not angles or not isinstance(tol,(int,float))or isinstance(tol,bool)or not 0<tol<=.1 or not policy.get('source_rule_evidence'):raise ValueError('explicit direction policy and expert source rule required')
    distance=lambda a,b:min(abs(a%180-b%180),180-abs(a%180-b%180))
    if any(not isinstance(a,(int,float))or isinstance(a,bool)or not math.isfinite(a)or distance(a,90)<=tol for a in angles):raise ValueError('horizontal policy must exclude axis vertical direction')
    rows=[];edges=[];seen=set()
    for edge in graph['edges']:
        eid=edge['edge_id']
        if eid in seen:raise ValueError('duplicate graph edge identity')
        seen.add(eid);local=[]
        for pi,path in enumerate(edge.get('attribute_paths',[])):
            if len(path)<2:raise ValueError('empty native source path')
            for si,(a,b)in enumerate(zip(path,path[1:])):
                if any(len(p)!=2 or any(isinstance(v,bool)or not isinstance(v,(int,float))or not math.isfinite(v)for v in p)for p in(a,b)):raise ValueError('finite original XY path required')
                size=math.dist(a,b)
                if size<=.05:kind='degenerate';direction=None
                else:
                    direction=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))%180
                    kind='vertical'if distance(direction,90)<=tol else'horizontal'if any(distance(direction,v)<=tol for v in angles)else'undetermined'
                source='axis_11_native_vertical'if kind=='vertical'else'corresponding_floor_plan_horizontal'if kind=='horizontal'else'original_source_direction_review'
                row=dict(edge_id=eid,path_index=pi,segment_index=si,scope_points=[list(a),list(b)],system=edge.get('system'),floor_start=edge.get('floor_start',edge.get('start_floor')),floor_end=edge.get('floor_end',edge.get('end_floor')),
                    drawing_direction_degrees=direction,direction_class=kind,DN_source_route=source,length_source_route=source,
                    source_line_coverage_checked=False,connection_proved_by_direction=False,physical_length_mm=None,DN_assigned=None,human_accepted=False)
                local.append(row);rows.append(row)
        kinds={r['direction_class']for r in local};classification='horizontal_only'if kinds=={'horizontal'}else'vertical_only'if kinds=={'vertical'}else'mixed_horizontal_vertical'if kinds=={'horizontal','vertical'}else'unresolved_direction_or_path'
        edges.append(dict(edge_id=eid,classification=classification,segments=len(local),horizontal_segments=sum(r['direction_class']=='horizontal'for r in local),vertical_segments=sum(r['direction_class']=='vertical'for r in local),
            floor_fields_used_to_choose_attribute_source=False,whole_edge_physical_length_mm=None))
    return dict(mode=MODE,status='drawing_segment_attribute_source_routes_not_native_connectivity_or_physical_values',records=rows,edges=edges,
        segment_counts=dict(collections.Counter(r['direction_class']for r in rows)),edge_counts=dict(collections.Counter(e['classification']for e in edges)),
        source_rule_evidence=policy['source_rule_evidence'],direction_policy=angles,graph_mutated=False,whole_edge_DN_assigned=0,physical_lengths_assigned=0,human_accepted=False)

def implementation_hashes():
    from confirm_crossview_paths import sha
    return {n:sha(importlib.import_module(n).__file__)for n in('axis_attribute_source_routing','batch_native_path_coverage','native_path_coverage_audit','native_line_path_evidence','source_readability')}

def compute(source,graph_path,policy_path):
    from confirm_crossview_paths import load,sha
    from source_readability import read_source
    from batch_native_path_coverage import collect as coverage
    paths=dict(source=Path(source),graph=Path(graph_path),policy=Path(policy_path));before={k:dict(path=str(p.resolve()),sha256=sha(p))for k,p in paths.items()}
    graph=load(graph_path);doc,preflight=read_source(Path(source))
    if graph.get('metadata',{}).get('source_sha256')!=sha(source):raise ValueError('routing graph belongs to another native CAD source')
    result=collect(graph,load(policy_path));proof=coverage(doc,graph,[e['edge_id']for e in graph['edges']],sha(source),sha(graph_path));lookup={(e['edge_id'],s.get('path_index',0),s['index']):s for e in proof['edges']for s in e['segments']}
    for row in result['records']:
        s=lookup.get((row['edge_id'],row['path_index'],row['segment_index']))
        if s is None or row['scope_points']!=[s['start'],s['end']]:raise ValueError('routing native source segment identity differs')
        row.update(native_source_status=s['status'],source_line_coverage_checked=True,native_witnesses=s['witnesses'])
    if any(sha(p)!=before[k]['sha256']for k,p in paths.items()):raise ValueError('routing input changed during native reading')
    result.update(inputs=before,source_preflight=preflight,native_segment_status_counts=dict(collections.Counter(r['native_source_status']for r in result['records'])),
        native_direction_status_counts=[dict(direction=direction,status=status,segments=count)for(direction,status),count in sorted(collections.Counter((r['direction_class'],r['native_source_status'])for r in result['records']).items())])
    return result

def produce(source,graph,policy,output):
    from confirm_crossview_paths import encode,sha
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(source,graph,policy);output.mkdir(parents=True);target=output/'axis-source-routing.json';target.write_bytes(encode(result));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,inputs=result['inputs'],implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    return result

def verify_output(output):
    from confirm_crossview_paths import load,sha,encode
    output=Path(output);receipt=load(output/'receipt.json');target=output/'axis-source-routing.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(target)!=receipt['output_sha256']or any(sha(r['path'])!=r['sha256']for r in receipt['inputs'].values()):raise ValueError('routing implementation, input or artifact changed')
    i=receipt['inputs'];result=compute(i['source']['path'],i['graph']['path'],i['policy']['path'])
    if encode(result)!=target.read_bytes():raise ValueError('independent native segment routing reconstruction differs')
    return result

def main():
    p=argparse.ArgumentParser()
    for name in('source','graph','policy','output','verify-output'):p.add_argument('--'+name,type=Path)
    a=p.parse_args()
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:result=verify_output(a.verify_output)
        else:
            if any(getattr(a,k)is None for k in('source','graph','policy','output')):p.error('all native source inputs and new output required')
            result=produce(a.source,a.graph,a.policy,a.output)
    print(dict(edge_counts=result['edge_counts'],segment_counts=result['segment_counts'],native_segment_status_counts=result['native_segment_status_counts']),flush=True)
if __name__=='__main__':main()
