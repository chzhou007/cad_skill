"""Reuse native metric/prefix/DN kernels on newly qualified complete ranges.

The full range correspondence stays intact. A contiguous attribute candidate
prefix stops before an unresolved direction; it creates no endpoint mapping.
"""
import argparse,copy,importlib
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
import reviewed_uniform_subroute_DN as original
import reviewed_expression_metrics as metrics
import rebuild_received_circle_expression_scopes as received_scope
from native_plan_projection_lengths import unit_evidence
from source_readability import read_source
from refresh_reviewed_ring_partition_DN import effective
from reapply_candidate_ring_crossview_DN import attribute_graph_binding

MODE='native_received_scope_group_metric_and_uniform_DN_reapplication_v1'


def candidate_prefix(scope,routing):
    """A real ordered prefix inside a separately proved full source range."""
    before=encode(scope);route=scope['views']['iso']['route'];edges=route['edges'];nodes=route['nodes']
    if len(nodes)!=len(edges)+1 or len(set(edges))!=len(edges):raise ValueError('complete unique ordered full route required')
    stop=len(edges);held=[]
    for index,eid in enumerate(edges[1:],1):
        domains=routing[eid]['segment_domains']
        if not domains:raise ValueError('direction inventory missing')
        unresolved=[s for s in domains if s['direction_class']not in('horizontal','vertical')]
        if unresolved:
            stop=index
            held=[dict(edge_id=x,reason='unresolved_original_axis_direction'if j==0 else'beyond_first_unqualified_attribute_edge',
                unresolved_domains=copy.deepcopy(unresolved)if j==0 else[],direction_reclassified=False,
                physical_length_mm=None,new_DN_assigned=None)for j,x in enumerate(edges[index:])]
            break
    if stop<2:raise ValueError('no lower attribute candidate prefix before unresolved direction')
    result=copy.deepcopy(scope);result['views']['iso']['route']=dict(copy.deepcopy(route),edges=edges[:stop],nodes=nodes[:stop+1])
    selection=dict(kind='contiguous_attribute_candidate_prefix_within_qualified_full_range',
        full_range_scope_id=scope['scope_id'],full_axis_edges=copy.deepcopy(edges),full_axis_nodes=copy.deepcopy(nodes),
        candidate_axis_edges=copy.deepcopy(edges[:stop]),candidate_axis_nodes=copy.deepcopy(nodes[:stop+1]),
        excluded_axis_suffix=copy.deepcopy(edges[stop:]),new_endpoint_correspondence_assigned=False,
        full_source_range_correspondence_changed=False,original_direction_thresholds_unchanged=True)
    if encode(scope)!=before:raise ValueError('full source scope mutated')
    return result,selection,held


def check_values(records,values,rendered):
    edges={e['edge_id']:e for e in rendered['edges']}
    for r in records:
        eid=r['axis_edge_id'];e=edges[eid]
        if any(e[k]!=r[ours]for k,ours in[('system','system'),('attribute_paths','axis_attribute_paths')]):
            raise ValueError('current rendered source geometry differs')
        if [e['start_node_id'],e['end_node_id']]!=r['axis_nodes']or [e['floor_start'],e['floor_end']]!=[r['floor'],r['floor']]:
            raise ValueError('current rendered endpoints or floor differ')
        old=values[eid].get('diameter_nominal_mm')
        if old not in(None,'')and old!=r['nominal_mm']:raise ValueError('old known axis DN conflicts; do not overwrite')
        r['old_known_nominal_mm']=old


def compute(manifest):
    inputs=manifest['inputs']
    def checked():
        if any(sha(v['path'])!=v['sha256']for v in inputs.values()):raise ValueError('received scope attribute input changed')
    checked();prior=original.verify_output(Path(inputs['original_uniform_proof']['path']).parent)
    if encode(prior)!=Path(inputs['original_uniform_proof']['path']).read_bytes():raise ValueError('original uniform owner replay differs')
    scope=received_scope.verify_output(Path(inputs['received_scope_proof']['path']).parent)
    if encode(scope)!=Path(inputs['received_scope_proof']['path']).read_bytes():raise ValueError('received scope owner replay differs')
    old=prior['inputs'];group=load(old['group_metric_proof']['path']);members=load(old['member_proof']['path']);origin=load(old['atom_proof']['path'])
    intervals=load(old['interval_proof']['path']);partition=load(old['partition_proof']['path']);route=load(old['routing_proof']['path']);si=scope['inputs']
    for key in('plan_source','plan_graph'):
        if group['inputs'][key]!=si[key]:raise ValueError('received range changed the original native plan namespace')
    for data in(members,intervals):
        for key,sourcekey in[('plan_source','plan_source'),('plan_graph','plan_graph'),('axis_source','iso_source'),('axis_graph','iso_graph')]:
            if data['inputs'][key]!=si[sourcekey]:raise ValueError('received range changed the native member namespace')
    if route['inputs']['graph']!=si['iso_graph']or route['inputs']['source']!=si['iso_source']:raise ValueError('native direction source differs')
    plan=load(si['plan_graph']['path']);axis=load(si['iso_graph']['path']);rendered=load(inputs['rendered_graph']['path']);vm=load(inputs['viewer_manifest']['path'])
    inherited=attribute_graph_binding(rendered,vm,dict(rendered_graph=inputs['rendered_graph'],attribute_context_graph=inputs['attribute_context_graph'],component_overlay_proof=inputs['component_overlay_proof']))
    viewer=Path(inputs['viewer_manifest']['path']).parents[2];actual=effective(viewer)
    if encode(actual)!=Path(inputs['current_effective']['path']).read_bytes():raise ValueError('actual current viewer values differ')
    values={r['edge_id']:r['values']for r in actual};provider=load(inputs['provider']['path'])
    if provider['counts']['rendered_component_instances']!=len(rendered['instances']):raise ValueError('current provider lost component adoptions')
    docs={};preflight={}
    for v in('plan','iso'):docs[v],preflight[v]=read_source(si[v+'_source']['path'])
    units=unit_evidence(docs['plan'],load(group['inputs']['unit_policy']['path']))
    if units!=group['units']:raise ValueError('original native unit calibration changed')
    dn={r['edge_id']:r for r in partition['after_inherited_kernel']['records']}
    routing={r['edge_id']:dict(r,segment_domains=[s for s in route['records']if s['edge_id']==r['edge_id']])for r in route['edges']}
    caps={v:original.captions(d)for v,d in docs.items()};oldmetrics={r['scope_id']:r for r in group['records']};oldgroups={r['scope_id']:r for r in prior['groups']}
    measured=[];newmetrics=[];uniform=[];selections=[];held=[];pending=[]
    for current in scope['records']:
        metric=metrics.measure(current,plan,units);measured.append(metric)
        if metric['scope_id']in oldmetrics:
            if metric!=oldmetrics[metric['scope_id']]:raise ValueError('previously published range metric changed')
        else:newmetrics.append(metric)
        candidates=[r for r in members['records']if r['system']==current['system']and r['floor']==current['floor']]
        if len(candidates)!=1:raise ValueError('one independently replayed member prefix required')
        member=candidates[0];me={e['edge_id'].rsplit(':',1)[1]:e for e in member['scoped_graph']['edges']}
        prefix=[r for r in intervals['member_records']if r['member_scope_id']==member['scope_id']and r['member_kind']=='approach']
        if len(prefix)!=1:raise ValueError('one original prefix interval required')
        pg=original.departure_guard(docs['plan'],me['approach'],me['departure'],caps['plan'],origin['floors'][str(current['floor'])])
        ids=current['views']['iso']['route']['edges'][1:];cov=original.coverage(docs['iso'],axis,ids,si['iso_source']['sha256'],si['iso_graph']['sha256'])
        if cov['unresolved']or any(s['status']!='single_source_line_covers'or len(s['witnesses'])!=1 for e in cov['edges']for s in e['segments']):
            raise ValueError('complete full-range native source coverage required')
        handles={w['source_handle']for e in cov['edges']for s in e['segments']for w in s['witnesses']}
        ag=original.native_label_guard(docs['iso'],handles,me['departure']['member']['nominal_mm'],caps['iso'])
        selected,selection,direction_holds=candidate_prefix(current,routing)
        report=original.select(selected,member,prefix[0],plan,axis,routing,dn,pg,ag)
        check_values(report['records'],values,rendered)
        if current['scope_id']in oldgroups:
            # Old published records remain the authoritative old provenance.
            previous={r['axis_edge_id']:r for r in oldgroups[current['scope_id']]['records']}
            if {r['axis_edge_id']for r in report['records']}!=set(previous):raise ValueError('old uniform coverage regressed')
            for r in report['records']:
                oldrow=previous[r['axis_edge_id']]
                for k in('nominal_mm','scope_paths','horizontal_segment_domains','whole_horizontal_edge','axis_nodes','axis_attribute_paths'):
                    if r[k]!=oldrow[k]:raise ValueError('old uniform source value or domain changed')
        else:
            for r in report['records']:r['attribute_candidate_selection']=copy.deepcopy(selection)
            uniform.append(report);selections.append(selection);held.extend(direction_holds)
    records=[r for g in uniform for r in g['records']]
    if len({r['axis_edge_id']for r in records})!=len(records):raise ValueError('competing received uniform writers')
    checked()
    return dict(mode=MODE,inputs=copy.deepcopy(inputs),source_inputs=copy.deepcopy(si),source_preflight=preflight,
        units=units,metric_records=measured,new_metric_records=newmetrics,uniform_groups=uniform,records=records,
        attribute_candidate_selections=selections,held_direction_edges=held,pending=pending,inherited_attribute_graph_binding=inherited,
        counts=dict(qualified_source_ranges=len(scope['records']),new_metric_groups=len(newmetrics),new_uniform_records=len(records),
            new_unknown_whole_DN=sum(r['whole_horizontal_edge']and r['old_known_nominal_mm']in(None,'')for r in records),
            new_mixed_scopes=sum(not r['whole_horizontal_edge']for r in records),held_direction_edges=len(held)),
        original_native_group_member_gate_caption_and_DN_owners_reexecuted=True,all_old_group_metrics_and_uniform_domains_preserved=True,
        graph_mutated=False,components_changed=False,physical_lengths_assigned=0,vertical_values_assigned=0,
        internal_node_identities_assigned=False,human_accepted=False,whole_goal_complete=False)


def implementations():return dict(entry=sha(__file__),original_uniform=original.implementations(),original_metrics=metrics.implementations(),received_scope=received_scope.implementations(),
    attribute_binding=sha(importlib.import_module('reapply_candidate_ring_crossview_DN').__file__))


def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementations();r=compute(load(manifest))
    if implementations()!=code:raise ValueError('received range attribute implementation changed')
    output.mkdir(parents=True);target=output/'received-scope-attributes.json';target.write_bytes(encode(r))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(target))))
    return r


def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');target=output/'received-scope-attributes.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementations()or sha(target)!=r['output_sha256']or sha(r['manifest']['path'])!=r['manifest']['sha256']:
        raise ValueError('received scope attribute receipt changed')
    fresh=compute(load(r['manifest']['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('received scope attribute native replay differs')
    return fresh


def main():
    p=argparse.ArgumentParser()
    for n in('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(a.verify_output)if a.verify_output else produce(a.manifest,a.output)
    print(dict(mode=MODE,counts=r['counts']),flush=True)
if __name__=='__main__':main()
