"""Reapply complete member external scopes with explicit plan-view contacts.

This source-stage entry does not publish a graph, update values or certify a
cached parent. Complete current-provider/alias replay and viewer adoption are
separate mandatory stages, recorded explicitly in the proof.
"""
import argparse,copy,hashlib,importlib,json,csv,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from current_two_arm_circle_routes import discover_external
from plan_member_contact_context import prove_member_routes,MODE

def require(value,message):
    if not value:raise ValueError(message)
def rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))

def validate_manifest(manifest):
    require(manifest.get('schema')==MODE and manifest.get('view_role')=='floor_plan_orthographic_XY','explicit qualified floor-plan source role required')
    inputs=manifest['inputs'];required={'provider','member_bridges','member_interfaces','plan_source','plan_graph','plan_inventory','axis_source','axis_graph','axis_inventory','current_T_source_config','junction_transition','template_origin','orientation_policy'}
    require(set(inputs)==required and isinstance(manifest.get('floor'),int),'complete fixed source-stage input roles required')
    require('t3'not in Path(inputs['plan_source']['path']).stem.lower()and't3'not in Path(inputs['axis_source']['path']).stem.lower(),'primary source must be non-T3')
    require(all(sha(v['path'])==v['sha256']for v in inputs.values()),'fixed source-stage input changed')
    return inputs

def compute(manifest):
    inputs=validate_manifest(manifest);provider=load(inputs['provider']['path']);parent=load(inputs['member_bridges']['path']);interfaces=load(inputs['member_interfaces']['path'])
    for k in ('plan_source','plan_graph','axis_source','axis_graph'):
        require(parent['inputs'][k]==inputs[k]and interfaces['inputs'][k]==inputs[k],'member source/graph namespace differs')
    require(provider['inputs']['axis_graph']==inputs['axis_graph']and provider['inputs']['axis_source']==inputs['axis_source'],'current axis provider differs')
    f=str(manifest['floor']);require(provider['inputs']['plan_graph_'+f]==inputs['plan_graph']and provider['inputs']['plan_source_'+f]==inputs['plan_source'],'current floor provider differs')
    docs={};preflight={};graphs={}
    for view in ('plan','axis'):
        docs[view],preflight[view]=read_source(inputs[view+'_source']['path']);graphs[view]=load(inputs[view+'_graph']['path']);require(graphs[view]['metadata']['source_sha256']==inputs[view+'_source']['sha256'],'graph/native source binding differs')
    before=encode(graphs),encode(provider),encode(parent),encode(interfaces)
    candidates,held,cohort=discover_external(graphs['plan'],graphs['axis'],parent,interfaces,provider,manifest['floor'])
    components={v:rows(inputs[v+'_inventory']['path'])for v in ('plan','axis')};component_before=encode(components)
    angles=load(inputs['orientation_policy']['path'])['isometric_horizontal_directions_degrees'];template=load(inputs['template_origin']['path']);config=load(inputs['current_T_source_config']['path'])
    records=[];profiles={}
    if candidates:
        records,profiles=prove_member_routes(candidates,graphs,docs,provider,inputs,config,components,angles,template,junction_transition_spec=inputs['junction_transition'])
    require(before==(encode(graphs),encode(provider),encode(parent),encode(interfaces))and component_before==encode(components),'source graph, component inventory or old provider mutated')
    for record in records:
        edge=next(e for e in graphs['axis']['edges']if e['edge_id']==record['axis_edge_id']);record['axis_nodes']=[edge[k]for k in ('start_node_id','end_node_id')];record['axis_attribute_paths']=copy.deepcopy(edge['attribute_paths'])
    validate_manifest(manifest)
    return dict(mode=MODE,inputs=copy.deepcopy(inputs),floor=manifest['floor'],view_role=manifest['view_role'],records=records,held=held,cohort=cohort,source_preflight=preflight,native_component_profiles=profiles,
        original_native_readers_reused=True,source_stable_junction_owner_replayed=True,all_remaining_member_ports_screened=True,
        complete_provider_and_alias_parent_replay_gate='required_separately_before_publication_not_claimed_by_this_source_context',
        original_source_graphs_mutated=False,original_component_owners_mutated=False,axis_3D_reader_unchanged=True,
        DN_values_assigned=0,physical_lengths_assigned=0,current_mapping_publication_performed=False,human_accepted=False,whole_goal_complete=False)

def implementations():
    names=('plan_member_contact_context','current_two_arm_circle_routes','member_external_anchored_routes','third_arm_crossview_paths','source_stable_junction_reapplication','native_current_junction_reader','native_ball_contact_reapplication','native_flange_contact_ownership','native_inline_joint_path_coverage','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest_path,output):
    output=Path(output);require(not output.exists(),'fresh source context output required');before=implementations();proof=compute(load(manifest_path));require(before==implementations(),'source context implementation changed')
    output.mkdir(parents=True);p=output/'plan-member-contact-context.json';p.write_bytes(encode(proof));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=before,output_sha256=sha(p))));return proof

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');p=output/'plan-member-contact-context.json';require(receipt['mode']==MODE and receipt['implementation_sha256']==implementations()and sha(receipt['manifest']['path'])==receipt['manifest']['sha256']and sha(p)==receipt['output_sha256'],'source context receipt or implementation changed')
    proof=compute(load(receipt['manifest']['path']));require(encode(proof)==p.read_bytes(),'independent native source context replay differs');return proof

def main():
    p=argparse.ArgumentParser()
    for key in ('manifest','output','verify-output'):p.add_argument('--'+key,type=Path)
    a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
            r=produce(a.manifest,a.output)
    print(json.dumps(dict(mode=MODE,source_qualified_routes=len(r['records']),held=len(r['held']),current_mapping_publication_performed=False,human_accepted=False),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
