"""Apply current native T/DN and original metric rules after full parent replay."""
import argparse,importlib,json,subprocess,sys,tempfile
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from legacy_named_provider_inventory import require,current_plan_reader
from source_readability import read_source
from native_plan_projection_lengths import unit_evidence
from current_junction_plan_DN import collect as current_plan_DN
from complementary_plan_attribute_application import MODE,qualify_row

def checked_parent(manifest):
    inputs=manifest['inputs'];snap=inputs['parent_snapshot'];root=Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='cad-complementary-attribute-parent-')as temporary:
        out=Path(temporary)/'checked'
        cmd=[sys.executable,'-X','utf8','-B',str(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_complementary_provider.py'),
             '--skills-root',str(Path(snap['path']).parent/'skills'),'--snapshot',snap['path'],
             '--native-run',str(Path(inputs['parent_proof']['path']).parent),'--output',str(out)]
        run=subprocess.run(cmd,cwd=manifest['parent_replay_cwd'],capture_output=True,text=True,encoding='utf-8')
        require(run.returncode==0,'corrected complete parent failed: '+run.stderr[-4000:])
        for name,key in [('complementary-chains.json','parent_proof'),('provider-inventory.json','parent_provider')]:
            require((out/name).read_bytes()==Path(inputs[key]['path']).read_bytes(),'corrected native parent identity differs')
        execution=load(out/'execution.json');execution.pop('elapsed_seconds')
        return load(out/'complementary-chains.json'),load(out/'provider-inventory.json'),execution

def compute_from_verified_parent(manifest,parent_result,original_DN,announce=lambda value:None):
    inputs=manifest['inputs'];parent,provider,execution=parent_result
    require(parent.get('all_current_plans_known_exploded_ball_population_screened')is True and parent.get('complete_original_provider_replayed')is True,'corrected full source inventory and parent required')
    axis=load(inputs['axis_graph']['path']);configuration=load(inputs['current_T_source_config']['path']);old_manifest=load(inputs['original_DN_manifest']['path']);records=[];pending=[];floors={}
    observed={r['edge_id']:r for r in provider['remaining_horizontal_attributes']}
    for floor in sorted({r['floor']for r in parent['records']}):
        f=str(floor);announce('Reapplying complete local plan DN and native metric owners on floor '+f)
        for key in('plan_graph_'+f,'plan_source_'+f,'axis_graph','axis_source'):
            require(inputs[key]==parent['inputs'][key],'attribute stage changed the qualified graph or source')
        plan=load(inputs['plan_graph_'+f]['path']);doc,preflight=read_source(inputs['plan_source_'+f]['path'])
        item=next(p for p in old_manifest['plans']if p['floor']==floor)
        from rebuild_inherited_full_plan_DN import configuration as original_annotation_configuration
        native=current_plan_DN(doc,plan,original_DN['floors'][f],inputs['plan_source_'+f]['sha256'],inputs['plan_graph_'+f]['sha256'],
            current_plan_reader(configuration,inputs['plan_source_'+f]['sha256'],inputs['plan_graph_'+f]['sha256']),original_annotation_configuration(item))
        units=unit_evidence(doc,load(inputs['unit_policy_'+f]['path']));profile=parent['floors'][f]['native_component_profiles'];profiles=dict(plan=profile['plan'],axis=profile['iso'])
        bindings=dict(plan_source=inputs['plan_source_'+f]['sha256'],plan_graph=inputs['plan_graph_'+f]['sha256'],axis_source=inputs['axis_source']['sha256'],
                      axis_graph=inputs['axis_graph']['sha256'],parent_proof=inputs['parent_proof']['sha256'],current_plan_DN=__import__('hashlib').sha256(encode(native)).hexdigest())
        for group in parent['groups']:
            if group['source_region']['floor']!=floor:continue
            for row in group['records']:
                try:
                    frontier=observed[row['axis_edge_id']]
                    require(frontier['known_whole_DN']is None and frontier['complete_centerline']is False,'old known attribute cannot be replaced by new correspondence')
                    records.append(qualify_row(row,group,dict(plan=plan,iso=axis),native,profiles,units,manifest['horizontal_directions_degrees'],bindings))
                except ValueError as exc:pending.append(dict(axis_edge_id=row['axis_edge_id'],mapping_id=row['mapping_id'],reason=str(exc)))
        floors[f]=dict(current_plan_DN=native,source_preflight=preflight,units=units)
    proof=dict(mode=MODE,inputs=inputs,records=records,pending=pending,floors=floors,parent_native_replay=execution,
        complete_corrected_parent_replayed=True,original_complete_DN_parent_replayed=True,current_T_and_original_metric_owners_reused=True,
        all_current_complementary_intervals_screened=True,all_original_known_plan_DN_preserved=True,
        all_historical_main_roles_reapplied=all(x['current_plan_DN']['all_current_native_main_roles_reapplied']for x in floors.values()),source_graphs_mutated=False,
        source_components_reassigned=False,axis_values_used_for_horizontal_DN=False,vertical_values_assigned=0,installed_lengths_assigned=0,
        human_accepted=False,whole_goal_complete=False,counts=dict(source_intervals=len(parent['records']),complete_centerlines=len(records),known_DN=sum(r['nominal_mm']is not None for r in records),
            DN_conflicts=sum(r['DN_status']=='conflict'for r in records),new_local_plan_DN=sum(x['current_plan_DN']['counts']['new_known_DN']for x in floors.values()),ordered_native_component_pairs=sum(len(r['ordered_native_component_pairs'])for r in records),pending=len(pending)))
    return proof,provider

def compute(manifest,announce=lambda value:None):
    inputs=manifest['inputs']
    def checked():require(all(sha(v['path'])==v['sha256']for v in inputs.values()),'complementary attribute pinned input changed')
    checked();announce('Independently replaying corrected complete source parent');parent=checked_parent(manifest)
    from native_original_plan_DN_replay import replay
    original,original_replay=replay(Path(inputs['original_DN_proof']['path']).parent,manifest.get('original_DN_diagnostic_directory'),announce)
    require(sha(inputs['original_DN_proof']['path'])==original_replay['original_proof_sha256'],'original complete DN source identity differs')
    proof,provider=compute_from_verified_parent(manifest,parent,original,announce);proof['original_DN_native_replay']=original_replay;checked();return proof,provider

def implementations():
    root=Path(__file__).resolve().parents[2]
    names=('current_junction_plan_DN','complementary_plan_attribute_application','native_original_plan_DN_replay','rebuild_inherited_full_plan_DN','full_plan_DN_inherited_annotations','full_plan_DN_inheritance','projected_circle_plan_DN','source_main_DN_continuity','native_projected_circle_main_role','cycle_gate_plan_lengths','member_external_anchored_routes','source_readability')
    return dict(entry=sha(__file__),fixed_parent_worker=sha(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_complementary_provider.py'),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output);require(not output.exists(),'fresh complementary attribute output required');before=implementations();proof,provider=compute(load(manifest),lambda value:print(value,flush=True));require(before==implementations(),'attribute implementation changed')
    output.mkdir(parents=True);values={'complementary-plan-attributes.json':proof,'parent-provider-inventory.json':provider}
    for name,value in values.items():(output/name).write_bytes(encode(value))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256={n:sha(output/n)for n in values})))
    return proof,provider

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');require(receipt['mode']==MODE and receipt['implementation_sha256']==implementations()and sha(receipt['manifest']['path'])==receipt['manifest']['sha256']and all(sha(output/n)==h for n,h in receipt['output_sha256'].items()),'complementary attribute receipt changed')
    proof,provider=compute(load(receipt['manifest']['path']))
    for name,value in [('complementary-plan-attributes.json',proof),('parent-provider-inventory.json',provider)]:require(encode(value)==(output/name).read_bytes(),'independent native complementary attribute replay differs')
    return proof,provider

def main():
    p=argparse.ArgumentParser()
    for key in('manifest','output','verify-output'):p.add_argument('--'+key,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:result=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
            result=produce(a.manifest,a.output)
    print(result[0]['counts'],flush=True)

if __name__=='__main__':main()
