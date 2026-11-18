"""Expose source-owned vertical DN by original edge/path/segment identity."""
import copy,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from confirm_crossview_paths import load,sha
from axis_vertical_DN_batch import verify_output,MODE as SOURCE_MODE
MODE='qualified_axis_vertical_segment_DN_context_v1'
def collect(raw,rendered,proof,bindings,prior):
    if proof.get('mode')!=SOURCE_MODE or proof.get('graph_mutated')is not False or proof.get('horizontal_plan_attributes_changed')is not False or proof.get('whole_edge_DN_assigned')!=0 or proof.get('physical_lengths_assigned')!=0 or proof.get('human_accepted')is not False:raise ValueError('unsupported vertical annotation proof')
    if prior.get('source_graph_sha256')!=bindings['raw_axis_graph']or prior.get('rendered_graph_sha256')!=bindings['rendered_graph']:raise ValueError('vertical context belongs to another axis graph')
    if raw.get('metadata',{}).get('source_sha256')!=proof['source_sha256']or proof['graph_sha256']!=bindings['native_axis_graph']:raise ValueError('vertical source identity differs')
    by={e['edge_id']:e for e in raw['edges']};view={e['edge_id']:e for e in rendered['edges']};records=[];seen=set();retained=set()
    for e in raw['edges']:
        for a in e.get('axis_riser_attributes',[]):retained.add((e['edge_id'],a['path_index'],a['segment_index']))
    for r in proof['records']:
        key=(r['edge_id'],r['path_index'],r['segment_index'])
        if key in seen:raise ValueError('duplicate vertical source domain')
        seen.add(key);e=by[r['edge_id']];shown=view[r['edge_id']];pi,si=r['path_index'],r['segment_index']
        if any(e.get(k)!=shown.get(k)for k in('edge_id','system','start_node_id','end_node_id','attribute_paths'))or e['attribute_paths'][pi][si:si+2]!=r['scope_points']or e['system']!=r['system']:raise ValueError('vertical annotation scope differs from original/rendered segment')
        if not math.isfinite(r['nominal_mm'])or r['nominal_mm']<=0 or r['whole_edge_DN_assigned']is not False or r['physical_length_mm']is not None or r['whole_edge_physical_length_mm']is not None:raise ValueError('vertical local annotation promoted to whole-edge or physical length')
        for previous in e.get('axis_riser_attributes',[]):
            if (previous['path_index'],previous['segment_index'])==(pi,si)and previous['nominal_mm']!=r['nominal_mm']:raise ValueError('new vertical DN conflicts with existing source-qualified axis value')
        if any(o['source_text']['source_sha256']!=proof['source_sha256']or o['nominal_mm']!=r['nominal_mm']for o in r['observations']):raise ValueError('vertical annotation source lineage differs')
        records.append(dict(copy.deepcopy(r),axis_source_sha256=proof['source_sha256'],related_HIL_confirmation_inherited=False,old_native_axis_value_retained=key in retained))
    if len(records)!=proof['counts']['qualified_vertical_segments']:raise ValueError('vertical scope inventory differs')
    return dict(mode=MODE,records=records,segments=len(records),affected_axis_edges=len({r['edge_id']for r in records}),source_bindings=bindings,axis_source_sha256=proof['source_sha256'],
        existing_axis_segment_values_preserved=True,horizontal_plan_attributes_preserved=True,raw_axis_graph_unchanged=True,whole_edge_DN_assigned=0,physical_lengths_assigned=0,human_accepted=False,
        previous_axis_riser_domains=len(retained),new_axis_vertical_domains=len(seen-retained),all_current_axis_vertical_domains=len(seen|retained),pending_native_domains=len(proof['pending']))
def from_artifact(raw_path,rendered_path,proof_path,prior):
    before={str(p):sha(p)for p in(raw_path,rendered_path,proof_path)};proof=verify_output(Path(proof_path).parent)
    result=collect(load(raw_path),load(rendered_path),proof,dict(raw_axis_graph=sha(raw_path),rendered_graph=sha(rendered_path),native_axis_graph=proof['graph_sha256'],native_vertical_DN_proof=sha(proof_path)),prior)
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('vertical source inputs changed')
    return result
