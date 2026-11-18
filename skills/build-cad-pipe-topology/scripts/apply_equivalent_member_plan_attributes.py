"""Replay source correspondence, then retain exact qualified plan DN scopes."""
import argparse,importlib,sys
from pathlib import Path
for n in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=str(Path(__file__).resolve().parents[2]/n/'scripts')
    if p not in sys.path:sys.path.insert(0,p)
from confirm_crossview_paths import load,sha,encode
from rebuild_equivalent_member_bounded_batch import verify_output as batch_owner
from ordered_anchor_branch_paths import qualified_local_DN
from equivalent_member_plan_attributes import apply,MODE
from cohort_plan_DN_reapplication import reapply
from source_readability import read_source
from native_current_junction_reader import make_reader
from rebuild_inherited_full_plan_DN import configuration

def compute(manifest):
    inputs=manifest['inputs'];paths={k:Path(v['path'])for k,v in inputs.items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in inputs.items()):raise ValueError('equivalent member attributes input changed')
    checked();batch=batch_owner(paths['batch_proof'].parent)
    if encode(batch)!=paths['batch_proof'].read_bytes():raise ValueError('independent native member batch differs')
    bi=batch['inputs'];floor=str(batch['floor'])
    if bi['parent_viewer_manifest']!=inputs['parent_viewer_manifest']:raise ValueError('attribute application has another original viewer parent')
    for spec in bi.values():
        if sha(spec['path'])!=spec['sha256']:raise ValueError('native source batch input changed')
    plan,axis,raw=[load(bi[k]['path'])for k in('plan_graph','axis_graph','raw_axis_graph')];rendered=load(paths['rendered_graph']);parent=load(paths['parent_viewer_manifest']);ctx=parent['attributeValueContext']
    if sha(paths['rendered_graph'])!=ctx['rendered_graph_sha256']or bi['raw_axis_graph']['sha256']!=ctx['source_graph_sha256']:raise ValueError('attribute application raw/rendered parent differs')
    DN=qualified_local_DN(raw,load(paths['DN_result']),paths['DN_receipt'],paths['DN_result'],{floor:plan},{floor:bi['plan_source']['sha256']},{floor:bi['plan_graph']['sha256']})[floor]
    specific=load(paths['specific_provider_proof'])
    if sha(paths['specific_provider_proof'])!=ctx['qualified_plan_scope_runs']['source_bindings']['native_proof']or specific['inputs']['attribute_policy']!=inputs['specific_attribute_policy']:raise ValueError('specific native annotation origin is outside the complete current parent')
    families={h for c in batch['native_bounded_batch']['complete_member_cohorts']for h in c['source_family']};specs=[s for s in load(paths['specific_attribute_policy'])['groups']if s.get('scope',{}).get('seeds')and{s['source_line_handle']for s in s['scope']['seeds']}<=families]
    dm=load(load(paths['DN_receipt'])['manifest']['path']);item=next(p for p in dm['plans']if str(p['floor'])==floor);source_hash=bi['plan_source']['sha256'];graph_hash=bi['plan_graph']['sha256'];doc,preflight=read_source(bi['plan_source']['path']);reader=make_reader(load(bi['current_T_source_config']['path']),source_hash,graph_hash)
    native_DN=reapply(doc,plan,batch,load(paths['DN_result'])['floors'][floor],configuration(item),specs,reader,source_hash,graph_hash)
    selected=dict(DN)
    for record in native_DN['records']:selected[record['edge_id']]=record['record']
    rows=apply(batch,selected,plan,axis,raw,rendered,ctx['horizontal_directions_degrees'],native_DN);checked()
    return dict(mode=MODE,inputs=inputs,source_batch_inputs=bi,records=rows,native_plan_DN_reapplication=native_DN,source_preflight=preflight,complete_source_batch_replayed=True,existing_complete_DN_provider_retained=True,specific_calibrated_and_F_readers_reapplied=True,source_graphs_mutated=False,DN_used_for_mapping=False,physical_pipe_count_inferred=False,all_horizontal_values_from_plan=True,vertical_values_assigned=0,installed_lengths_assigned=0,unknown_length_filled_with_zero=False,counts=dict(new_correspondence_intervals=len(rows),qualified_plan_DN=sum(r['nominal_mm']is not None for r in rows),complete_horizontal_lengths=sum(r['complete_horizontal_centerline_mm']is not None for r in rows),DN_and_length_complete=sum(r['nominal_mm']is not None and r['complete_horizontal_centerline_mm']is not None for r in rows),native_DN_conflicts=sum(r['DN_status']=='native_plan_DN_conflict'for r in rows),pending_annotation_scopes=sum(r['DN_status']=='existing_native_annotation_provider_application_pending'for r in rows)),human_accepted=False,viewer_publication_pending=True,whole_goal_complete=False)
def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('equivalent_member_plan_attributes','cohort_plan_DN_reapplication','rebuild_equivalent_member_bounded_batch','ordered_anchor_branch_paths','native_main_endpoint_extent','source_readability','native_current_junction_reader','rebuild_inherited_full_plan_DN','full_plan_DN_inherited_annotations','calibrated_direct_dn_evidence','wave_rebased_plan_attributes','full_plan_DN_inheritance')})
def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();r=compute(load(manifest))
    if code!=implementation_hashes():raise ValueError('equivalent attribute implementation changed')
    output.mkdir(parents=True);p=output/'equivalent-member-plan-attributes.json';p.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))))
    return r
def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'equivalent-member-plan-attributes.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']:raise ValueError('equivalent attribute receipt or code changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes():raise ValueError('equivalent attributes independent replay differs')
    return r
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:r=verify_output(a.verify_output)
    else:
        if not a.manifest or not a.output:p.error('fixed source manifest and fresh output required')
        r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
