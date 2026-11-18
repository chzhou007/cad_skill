"""Apply exact received omission replies to independently replayed native valves."""
import argparse,copy,sys
from pathlib import Path
for skill in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/skill/'scripts'))
from confirm_crossview_paths import load,sha,encode
import received_projected_circle_authority as received
import rebuild_fragment_component_index as original
from fragment_component_index import build,restore,AUDIT
from source_readability import read_source

MODE='received_native_fragment_component_detail_index_v1'
POSITIVE_ANSWERS={'两组均为平面省略，实物按11各两阀','两组均为平面省略，实物按轴测各两阀'}


def apply_classifications(previous,inventory,native,bindings,record,intake_spec):
    if record['explicit_answer']['decision']not in POSITIVE_ANSWERS or len(bindings)!=2 or {b['system']for b in bindings}!={'supply','return'}:
        raise ValueError('explicit paired supply/return two-valve omission answer required')
    result=copy.deepcopy(previous);rows={r['source_handle']:r for r in result}
    if len(rows)!=len(result):raise ValueError('duplicate native fragment classification')
    components={r['source_top_handle']:r for r in inventory['added_components']}
    source_rows={r['source_handle']:r for r in inventory['records']}
    edges={e['edge_id']:e for e in native['edges']};seen=set()
    for binding in bindings:
        handle=binding['source_handle'];oldhandle=binding['existing_source_handle'];eid=binding['axis_edge_id']
        if handle in seen or handle not in rows or handle not in components:
            raise ValueError('unique reviewed native component required')
        seen.add(handle);row=rows[handle];component=components[handle]
        if (row.get('status')!='source_detail_profile_difference'or row.get('adopted')is not False
            or row.get('domain')!='separate_named_external_port'or row.get('axis_edge_id')!=eid
            or row.get('plan_edges')!=binding['plan_edges']or row.get('floor')!=binding['floor']
            or row.get('new_correspondence_assigned')is not False or not row.get('mapping_id')
            or edges[eid]['system']!=binding['system']or component['edge_id']!=eid
            or component['system_hint']!=binding['system']or component['equipment_type']!='球阀'):
            raise ValueError('reviewed component identity or existing scope differs')
        if not {handle,oldhandle}<=set(record['source_evidence']['source_handles']):
            raise ValueError('reply does not name both original source components')
        owners=[r for r in inventory['components']if r.get('source_top_handle')==oldhandle]
        old=source_rows.get(oldhandle,{})
        if (len(owners)!=1 or owners[0]['edge_id']!=eid or owners[0]['equipment_type']!='球阀'
            or old.get('status')!='existing_owner_independently_agrees'
            or {r['system']for r in old.get('native_candidates',[])}!={binding['system']}):
            raise ValueError('original valve owner not independently proved on same system')
        p,a=row['plan_profile'],row['axis_profile']
        if (len(p)!=1 or len(a)!=1 or p[0].get('ball_valve')!=1 or a[0].get('ball_valve')!=2
            or {k:v for k,v in p[0].items()if k!='ball_valve'}!={k:v for k,v in a[0].items()if k!='ball_valve'}):
            raise ValueError('reply only resolves the single omitted plan ball valve')
        prior=copy.deepcopy(row)
        row.update(status='explicit_received_plan_omission_axis_two_valves',adopted=True,
            original_classification=prior,received_detail_expression=dict(question_id=record['question_id'],
                answer=copy.deepcopy(record['explicit_answer']),intake=copy.deepcopy(intake_spec),
                source_handles=[handle,oldhandle],original_plan_profile=copy.deepcopy(p),original_axis_profile=copy.deepcopy(a),
                profiles_claimed_equal=False,missing_plan_symbol_position=None,source_instances_merged=False,
                physical_parameters_assigned=0,human_accepted=False))
    if not seen:raise ValueError('explicit native detail bindings required')
    if any(rows[r['source_handle']]!=r for r in previous if r['source_handle']not in seen):
        raise ValueError('unreviewed fragment classification changed')
    return result


def preserve_current(current,reconstructed,new_handles):
    old={r['id']:r for r in current['instances']};new={r['id']:r for r in reconstructed['instances']}
    if len(old)!=len(current['instances'])or len(new)!=len(reconstructed['instances'])or not old.keys()<=new.keys():
        raise ValueError('reviewed component inventory changed old identities')
    if any(new[k]!=v for k,v in old.items()):raise ValueError('old native component instance changed')
    added=[r for r in reconstructed['instances']if r['id']not in old]
    if len(added)!=len(new_handles)or {r['source_top_handle']for r in added}!=set(new_handles):
        raise ValueError('extra or missing reviewed source instance')
    if restore(current)!=restore(reconstructed):raise ValueError('both component overlays must restore the exact same attribute base')
    reverted=copy.deepcopy(reconstructed);reverted['instances']=copy.deepcopy(current['instances'])
    old_edges={e['edge_id']:e for e in current['edges']}
    changed_edges={r['edge_id']for r in added}
    for edge in reverted['edges']:
        if edge['edge_id']not in changed_edges and edge['equipment_inventory']!=old_edges[edge['edge_id']]['equipment_inventory']:
            raise ValueError('unreviewed component inventory changed')
        edge['equipment_inventory']=copy.deepcopy(old_edges[edge['edge_id']]['equipment_inventory'])
    reverted[AUDIT]=copy.deepcopy(current[AUDIT])
    if reverted!=current:raise ValueError('new component overlay changed a pipe or other graph property')
    return dict(old_instances_preserved=len(old),new_instances=len(added),current_instances=len(new),
        source_handles=sorted(new_handles),exact_original_attribute_parent_restored=True,
        pipe_geometry_and_all_noninventory_attributes_exact=True)


def compute(manifest):
    inputs=manifest['inputs']
    for spec in inputs.values():received.checked(spec)
    path=Path(inputs['original_index']['path']);proof=original.verify_output(path.parent)
    if encode(proof)!=path.read_bytes():raise ValueError('original native index source replay differs')
    current=load(inputs['current_graph']['path']);original_graph=load(path.parent/'graph.json')
    if current!=original_graph:raise ValueError('current rendered component parent differs from native original index')
    definitions,records=received.replay_intake(inputs['intake_receipt'],manifest['page_root'])
    selected=[r for r in records if r['question_id']==manifest['question_id']]
    if len(selected)!=1:raise ValueError('one explicit received native-detail reply required')
    record=selected[0];evidence=record['source_evidence']
    if (manifest['expected_decision']not in POSITIVE_ANSWERS or record['explicit_answer']['decision']!=manifest['expected_decision']
        or manifest['expected_decision']not in record['options']or evidence['native_component_index']!=inputs['original_index']):
        raise ValueError('reviewed detail answer or original source index differs')
    received.checked(evidence['source_pair_audit'])
    source_inputs=evidence['source_inputs'];provider=load(proof['inputs']['provider']['path'])
    if load(evidence['source_pair_audit']['path'])['source_inputs']!=source_inputs:raise ValueError('reviewed Pair source audit differs')
    for k,spec in source_inputs.items():
        received.checked(spec)
        if provider['inputs'][k]!=spec:raise ValueError('reviewed detail sources differ from original mapped scope')
    inventory=load(proof['inputs']['source_inventory']['path']);native=load(inventory['inputs']['graph']['path'])
    for k,ours in[('source','axis_source'),('graph','axis_graph')]:
        if inventory['inputs'][k]!=source_inputs[ours]:raise ValueError('native component source changed')
    classes=apply_classifications(proof['classifications'],inventory,native,manifest['bindings'],record,inputs['intake_receipt'])
    doc,readability=read_source(inventory['inputs']['source']['path']);parent=load(proof['inputs']['parent_graph']['path'])
    graph,audit=build(parent,native,inventory,classes,doc,proof['inputs']['parent_graph']['sha256'],proof['inputs']['source_inventory']['sha256'])
    conservation=preserve_current(current,graph,[b['source_handle']for b in manifest['bindings']])
    result=copy.deepcopy(proof);result.update(application_mode=MODE,received_detail_inputs=copy.deepcopy(inputs),
        previous_classifications=copy.deepcopy(proof['classifications']),classifications=classes,audit=audit,
        pending_source_components=[r for r in classes if not r['adopted']],received_detail_question=copy.deepcopy(record),
        source_preflight=readability,current_component_conservation=conservation,
        profiles_claimed_equal=False,missing_plan_component_positions_assigned=0,source_instances_merged=False)
    for spec in inputs.values():received.checked(spec)
    for spec in [*proof['inputs'].values(),*source_inputs.values(),*inventory['inputs'].values()]:received.checked(spec)
    return graph,result


def implementations():return dict(entry=sha(__file__),original_index=original.implementations(),received_intake=received.implementations())


def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementations();graph,result=compute(load(manifest))
    if implementations()!=code:raise ValueError('reviewed native detail implementation changed')
    output.mkdir(parents=True);target=output/'graph.json';target.write_bytes(encode(graph));result['rendered_graph_sha256']=sha(target)
    proof=output/'fragment-component-index.json';proof.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,graph_sha256=sha(target),proof_sha256=sha(proof))))
    return result


def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');target=output/'graph.json';proof=output/'fragment-component-index.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementations()or sha(target)!=r['graph_sha256']or sha(proof)!=r['proof_sha256']:
        raise ValueError('reviewed native detail receipt changed')
    received.checked(r['manifest']);graph,result=compute(load(r['manifest']['path']));result['rendered_graph_sha256']=sha(target)
    if encode(graph)!=target.read_bytes()or encode(result)!=proof.read_bytes():raise ValueError('reviewed native detail independent replay differs')
    return result


def main():
    p=argparse.ArgumentParser()
    for n in('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(a.verify_output)if a.verify_output else produce(a.manifest,a.output)
    print(dict(mode=MODE,current_instances=r['audit']['current_instances'],pending=len(r['pending_source_components'])),flush=True)
if __name__=='__main__':main()
