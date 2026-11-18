"""Add complete extents under the existing bounded-main attribute owner."""
import copy,sys
from pathlib import Path
for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/name/'scripts'))
from confirm_crossview_paths import load,sha
from native_replay_session import verify_once
from rebuild_bounded_main_complete_extents import verify_output,MODE as SOURCE_MODE
from noncompound_main_extent_context import component_identities
from native_paired_end_labels import level_key
MODE='qualified_native_bounded_main_complete_extents_v1'


def collect(raw,rendered,proof,bindings,prior):
    if proof.get('mode')!=SOURCE_MODE or any(proof.get(k)is not True for k in('current_provider_inventory_replayed','bounded_ancestor_native_replayed','selected_old_and_current_plan_scopes_exact','existing_correspondences_unchanged','DN_observations_preserved')) or any(proof.get(k)is not False for k in('local_graphs_mutated','source_paths_mutated','human_accepted')):
        raise ValueError('native bounded extent proof not qualified')
    if proof.get('installed_lengths_assigned')!=0 or proof.get('net_pipe_cut_lengths_assigned')!=0:
        raise ValueError('installed/net length promotion forbidden')
    parent=prior['anchor_bounded_mains']
    if 'complete_main_extents'in parent or parent['source_bindings']['native_proof']!=bindings['bounded_parent_proof']:
        raise ValueError('bounded parent owner changed or extension already present')
    original={e['edge_id']:e for e in raw['edges']};view={e['edge_id']:e for e in rendered['edges']};records=[];quarantined=[]
    for r in proof['records']+proof.get('quarantined_records',[]):
        eid=r['axis_edge_id'];old=[v for v in parent['records']if v['axis_edge_id']==eid]
        if len(old)!=1 or old[0]!=r['prior_bounded_scope']:raise ValueError('prior bounded source scope changed')
        if r['whole_installed_length_mm']is not None or r['net_pipe_cut_length_mm']is not None:raise ValueError('physical length promoted')
        edge=original[eid]
        if any(edge.get(k)!=view[eid].get(k)or edge.get(k)!=r[v]for k,v in(('system','system'),('start_node_id','axis_start_node'),('end_node_id','axis_end_node'),('attribute_paths','axis_attribute_paths'))):
            raise ValueError('current bounded axis identity differs')
        blocked=r in proof.get('quarantined_records',[])
        fragment=r.get('compound_fragment_scope',{})
        excluded=fragment.get('excluded_unbound_fragment_proposals',[])
        if excluded and not blocked:
            direct=fragment.get('direct_native_evidence',{}).get('observations',[])
            if len(direct)!=1 or direct[0].get('parenthesized_source_value')is None:raise ValueError('fragment scope needs independent local level literal')
            literal=level_key(direct[0]['parenthesized_source_value'])
            members=[m for e in excluded for m in e['declaration']['members']]
            if not members or any(m.get('source_level_text')is None or level_key(m['source_level_text'])==literal for m in members):raise ValueError('local literal does not separate the discarded compound annotation domain')
        length=r.get('candidate_T_to_T_projection_mm')if blocked else r['complete_horizontal_centerline_route_mm']
        if r['nominal_mm']!=old[0]['nominal_mm'] or length is None or abs(length-old[0]['plan_horizontal_projection']['value_mm'])>.0001:
            raise ValueError('qualified DN or centreline differs')
        keys=('mapping_id','axis_edge_id','plan_edge_id','floor','system','nominal_mm','endpoint_relations','axis_start_node','axis_end_node','axis_attribute_paths','plan_nodes','axis_nodes','complete_horizontal_centerline_route_mm','source_projection','whole_installed_length_mm','net_pipe_cut_length_mm','source_paths_mutated','mapping','source_hashes','prior_bounded_scope')
        value={k:copy.deepcopy(r[k])for k in keys}
        if 'compound_fragment_scope'in r:value['compound_fragment_scope']=copy.deepcopy(r['compound_fragment_scope'])
        value.update(component_instance_identities=component_identities(edge,view[eid],rendered),related_HIL_confirmation_inherited=False,human_accepted=False)
        if blocked:
            if r.get('reason')!='compound_carrier_requires_its_member_identity_not_scalar_main_extent' or not r.get('carrier_evidence')or r['complete_horizontal_centerline_route_mm']is not None:raise ValueError('carrier quarantine lacks original source evidence')
            value.update(reason=r['reason'],carrier_evidence=copy.deepcopy(r['carrier_evidence']),candidate_T_to_T_projection_mm=length)
            quarantined.append(value)
        else:records.append(value)
    all_rows=records+quarantined
    if len({v['axis_edge_id']for v in all_rows})!=len(all_rows):raise ValueError('bounded extent writer repeats')
    return dict(mode=MODE,records=records,axis_edges=len(records),quarantined_records=quarantined,quarantined_axis_edges=len(quarantined),source_bindings=bindings,
        existing_correspondences_unchanged=True,DN_observations_preserved=True,old_bounded_records_preserved=True,
        local_graphs_mutated=False,installed_lengths_assigned=0,net_pipe_cut_lengths_assigned=0,human_accepted=False)


def from_artifact(raw_path,rendered_path,proof_path,prior):
    proof=verify_once(Path(proof_path).parent,verify_output)
    if proof['inputs']['raw_axis_graph']['sha256']!=sha(raw_path):raise ValueError('bounded extent raw graph differs')
    return collect(load(raw_path),load(rendered_path),proof,
        dict(axis_graph=sha(raw_path),rendered_graph=sha(rendered_path),native_proof=sha(proof_path),
             bounded_parent_proof=proof['inputs']['bounded_proof']['sha256'],
             plan_graph=proof['inputs']['plan_graph']['sha256'],axis_local_graph=proof['inputs']['axis_graph']['sha256']),prior)
