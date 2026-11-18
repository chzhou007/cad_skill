"""Measure witnessed plan fragments of a reviewed unequal-cardinality route.

Group correspondence never allocates the sum to individual axis edges. A
calibration window is widened only over the replayed source route itself;
native units/title/dimensions and all omitted spans retain their old owners.
"""
import argparse,copy,importlib,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from native_plan_projection_lengths import unit_evidence,lengths
from source_readability import read_source
from reviewed_expression_scope import verify_output as verify_scope,MODE as SCOPE_MODE

MODE='reviewed_native_expression_group_plan_fragment_metrics_v1'

def measure(scope,graph,units):
    if scope['status']!='native_bounded_range_correspondence':raise ValueError('both local source topologies must pass first')
    if units.get('status')!='native_mm_units_corroborated_not_pipe_dimension_assignment':raise ValueError('native plan unit calibration required')
    view=scope['views']['plan'];route=view['route'];iso=scope['views']['iso']['route']
    if len(set(route['edges']))!=len(route['edges'])or len(set(iso['edges']))!=len(iso['edges']):raise ValueError('repeated route member')
    if len(route['nodes'])!=len(route['edges'])+1 or len(iso['nodes'])!=len(iso['edges'])+1:raise ValueError('complete ordered boundary path required')
    edges={e['edge_id']:e for e in graph['edges']};audits={e['edge_id']:e for e in view['path_coverage']['edges']}
    if view['path_coverage']['unresolved']or view['junction_failures']or view['path_failures']:raise ValueError('unresolved plan source evidence')
    snapshots={e['edge_id']:e for e in view['source_snapshot']['edges']}
    if set(snapshots)!=set(route['edges']):raise ValueError('source snapshot does not cover route')
    points=[]
    for index,eid in enumerate(route['edges']):
        e=edges[eid];a=audits[eid]
        if e!=snapshots[eid]or e['system']!=scope['system']or a['system']!=scope['system']:raise ValueError('source edge scope or system changed')
        if {e['start_node_id'],e['end_node_id']}!={route['nodes'][index],route['nodes'][index+1]}:raise ValueError('disconnected route order')
        if e.get('source_view_context')or e.get('source_wave_omission')or e.get('source_flexible_joints'):raise ValueError('detail, wave and inline spans require their own metric owners')
        for keys in [('start_floor','floor_start'),('end_floor','floor_end')]:
            floors=[e[k]for k in keys if k in e]
            if not floors or any(f!=scope['floor']for f in floors):raise ValueError('same calibrated floor required')
        expected={(pi,si)for pi,p in enumerate(e['attribute_paths'])for si in range(len(p)-1)}
        actual={(s.get('path_index',0),s['index'])for s in a['segments']}
        if len(actual)!=len(a['segments'])or actual!=expected:raise ValueError('complete unique native fragment census required')
        for s in a['segments']:
            pi,si=s.get('path_index',0),s['index']
            if (s['status']!='single_source_line_covers'or len(s['witnesses'])!=1 or s['witnesses'][0]['scope']!='modelspace'
                or e['attribute_paths'][pi][si:si+2]!=[s['start'],s['end']]):raise ValueError('native modelspace LINE fragment required')
        points.extend(p for path in e['attribute_paths']for p in path)
    if not points or any(len(p)<2 or any(isinstance(v,bool)or not isinstance(v,(int,float))or not math.isfinite(v)for v in p[:2])for p in points):raise ValueError('finite native plan coordinates required')
    old=units['plan_window'];window=[min(old[0],*(p[0]for p in points)),max(old[1],*(p[0]for p in points)),min(old[2],*(p[1]for p in points)),max(old[3],*(p[1]for p in points))]
    local_units=copy.deepcopy(units);local_units['plan_window']=window;fragments=[];unknown=[]
    for eid in route['edges']:
        e=edges[eid];audit=audits[eid]
        if len(e['attribute_paths'])>1:unknown.append(dict(plan_edge=eid,reason='separate_native_source_paths_gap_not_measured',physical_connector_length_mm=None))
        for pi,path in enumerate(e['attribute_paths']):
            segments=[copy.deepcopy(s)for s in audit['segments']if s.get('path_index',0)==pi]
            for s in segments:s['path_index']=0
            private=dict(graph,edges=[dict(e,attribute_paths=[copy.deepcopy(path)])]);coverage=dict(edges=[dict(audit,segments=segments)])
            value=lengths(private,coverage,dict(plan_edges=[eid],system=scope['system']),local_units)
            for p in value['pieces']:p['path_index']=pi;fragments.append(p)
    if len({(p['plan_edge'],p['path_index'],p['segment_index'])for p in fragments})!=len(fragments):raise ValueError('source fragment double counted')
    return dict(scope_id=scope['scope_id'],floor=scope['floor'],system=scope['system'],plan_edges=copy.deepcopy(route['edges']),axis_edges=copy.deepcopy(iso['edges']),
        plan_boundary_nodes=[route['nodes'][0],route['nodes'][-1]],axis_boundary_nodes=[iso['nodes'][0],iso['nodes'][-1]],
        measurement_kind='sum_of_native_floor_plan_LINE_fragments_not_installed_length',known_plan_XY_fragment_sum_mm=sum(p['length_mm']for p in fragments),pieces=fragments,
        original_calibration_window=copy.deepcopy(old),source_checked_route_window=window,unit_calibration_evidence_unchanged=True,
        omitted_span_evidence=unknown,complete_group_physical_length_mm=None,per_axis_edge_length_allocation=None,per_axis_edge_DN_assignment=None,
        internal_node_identities_assigned=False,graph_mutated=False,human_accepted=False)

def compute(manifest):
    inputs=manifest['inputs']
    def checked():
        if any(sha(v['path'])!=v['sha256']for v in inputs.values()):raise ValueError('fixed input changed')
    checked();parent=verify_scope(Path(inputs['scope_proof']['path']).parent)
    if parent['mode']!=SCOPE_MODE or encode(parent)!=Path(inputs['scope_proof']['path']).read_bytes():raise ValueError('source group replay differs')
    for k in ['plan_graph','plan_source']:
        if inputs[k]!=parent['inputs'][k]:raise ValueError('source graph or drawing differs from reviewed scope')
    doc,preflight=read_source(inputs['plan_source']['path']);units=unit_evidence(doc,load(inputs['unit_policy']['path']));graph=load(inputs['plan_graph']['path']);records=[];held=[]
    for scope in parent['records']:
        if scope['status']!='native_bounded_range_correspondence':held.append(dict(scope_id=scope['scope_id'],status=scope['status'],failures=copy.deepcopy(scope['failures'])));continue
        records.append(measure(scope,graph,units))
    checked();return dict(mode=MODE,inputs=inputs,records=records,held=held,units=units,source_preflight=preflight,original_native_group_owner_reexecuted=True,
        original_plan_metric_reader_reused=True,all_scope_records_screened=len(parent['records']),per_axis_edge_values_assigned=0,physical_lengths_assigned=0,DN_values_assigned=0,human_accepted=False,whole_goal_complete=False)

def implementations():return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in ['reviewed_expression_scope','native_plan_projection_lengths','source_readability']})
def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementations();r=compute(load(manifest))
    if code!=implementations():raise ValueError('implementation changed')
    output.mkdir(parents=True);p=output/'reviewed-expression-metrics.json';p.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))))
    return r
def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');p=output/'reviewed-expression-metrics.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementations()or sha(r['manifest']['path'])!=r['manifest']['sha256']or sha(p)!=r['output_sha256']:raise ValueError('metric receipt differs')
    fresh=compute(load(r['manifest']['path']))
    if encode(fresh)!=p.read_bytes():raise ValueError('fresh group metric replay differs')
    return fresh
def main():
    p=argparse.ArgumentParser()
    for n in ['manifest','output','verify-output']:p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(a.verify_output)if a.verify_output else produce(a.manifest,a.output)
    print(dict(mode=MODE,measured_groups=len(r['records']),held_groups=len(r['held']),per_axis_edge_values_assigned=0),flush=True)
if __name__=='__main__':main()
