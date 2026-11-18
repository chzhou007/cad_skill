"""Replay current local parents; normalize all eligible circles and their routes."""
import argparse,copy,csv,hashlib,importlib,json,subprocess,sys,tempfile
from pathlib import Path
for n in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/n/'scripts'))
from confirm_crossview_paths import load,sha,encode
from legacy_named_provider_inventory import require
from current_two_arm_circle_routes import MODE,rebuild,discover_external,inherit
from member_external_anchored_routes import prove
from native_replay_session import verify_once
from source_readability import read_source

def csvrows(path):
    with Path(path).open(encoding='utf-8-sig',newline='')as h:return list(csv.DictReader(h))

def checked_provider(manifest):
    inputs=manifest['inputs'];proof_spec=inputs['metric_proof'];snap=inputs['provider_snapshot'];root=Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='cad-two-arm-provider-')as name:
        output=Path(name)/'checked'
        cmd=[sys.executable,'-X','utf8','-B',str(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_complete_owner.py'),'--skills-root',str(Path(snap['path']).parent/'skills'),'--snapshot',snap['path'],'--native-run',str(Path(proof_spec['path']).parent),'--owner','reapply_anchored_plan_metrics','--result-files',json.dumps(['anchored-plan-metrics.json']),'--output',str(output)]
        p=subprocess.run(cmd,cwd=manifest['parent_replay_cwd'],capture_output=True,text=True,encoding='utf8')
        require(p.returncode==0,'complete metric provider native replay failed: '+p.stderr[-4000:])
        require((output/'anchored-plan-metrics.json').read_bytes()==Path(proof_spec['path']).read_bytes(),'metric parent proof differs')
    from reapply_anchored_plan_metrics import inventory_from
    from refresh_anchored_native_plan_metrics import effective_attributes
    proof=load(proof_spec['path']);viewer=Path(inputs['viewer_manifest']['path']).parents[2];vm=load(inputs['viewer_manifest']['path'])
    require(vm['sourceHashes']['anchored_native_plan_metrics']==proof_spec['sha256'],'actual viewer has another metric owner')
    provider=inventory_from(load(proof['inputs']['provider']['path']),proof,effective_attributes(viewer))
    actual=load(inputs['provider']['path'])
    require(json.loads(encode(provider))==actual,'complete actual adopted provider differs')
    return actual

def local_parent(floor,graph_spec,source_spec,components_spec):
    owner={1:'attach_reviewed_interface_owners',2:'rebuild_ordered_sideview_owners',3:'reconstruct_wave_main_cohorts'}[floor]
    module=importlib.import_module(owner);result=verify_once(Path(graph_spec['path']).parent,module.verify_output)
    require(result['output_graph_sha256']==graph_spec['sha256'],'current local parent native graph differs')
    audit_inputs=result.get('inputs')
    if audit_inputs is None:audit_inputs=load(result['manifest']['path'])['inputs']
    require(audit_inputs['source']==source_spec,'current local parent source differs')
    require(Path(components_spec['path'])==Path(graph_spec['path']).with_name('assigned_edge_device_instances.csv'),'local parent needs its actual canonical component inventory')
    return dict(owner=owner,output_graph_sha256=graph_spec['sha256'],native_replayed=True)

def compute(manifest,announce=lambda value:None):
    inputs=manifest['inputs']
    def checked():require(all(sha(v['path'])==v['sha256']for v in inputs.values()),'current two-arm input changed')
    checked();announce('Replaying complete current adopted provider');provider=checked_provider(manifest)
    floors={};outputs={};bindings={};changed=[]
    for floor in(1,2,3):
        f=str(floor);parent=local_parent(floor,inputs['plan_graph_'+f],inputs['plan_source_'+f],inputs['plan_components_'+f]);graph=load(inputs['plan_graph_'+f]['path']);doc,preflight=read_source(inputs['plan_source_'+f]['path']);rows=csvrows(inputs['plan_components_'+f]['path'])
        out,assigned,proof=rebuild(doc,graph,rows);gh=hashlib.sha256(encode(out)).hexdigest();outputs[f]=(out,assigned)
        bindings[f]=dict(source=inputs['plan_source_'+f],original_graph=inputs['plan_graph_'+f],reading_graph_sha256=gh,edge_aliases=proof['edge_aliases'],separate_reading_graph=True)
        floors[f]=dict(parent=parent,source_preflight=preflight,proof=proof,reading_graph_sha256=gh)
        if proof['records']:changed.append(floor)
        announce('Floor '+f+': '+str(proof['counts']))
    axis=load(inputs['axis_graph']['path']);interfaces=load(inputs['member_interfaces']['path']);bridges=load(inputs['member_bridges']['path']);local=load(inputs['member_local_graph']['path']);records=[];held=[];cohorts={};profiles={}
    for floor in changed:
        f=str(floor);plan,pi=outputs[f];parent_specs=provider['original_provider_inventory_inputs']
        require(parent_specs['axis_graph']==inputs['axis_graph']and parent_specs['plan_graph_'+f]==inputs['plan_graph_'+f],'local normalization uses another complete provider scope')
        for k,current in [('plan_source','plan_source_'+f),('axis_source','axis_source'),('plan_graph','plan_graph_'+f),('axis_graph','axis_graph')]:
            require(interfaces['source_hashes'][k]==inputs[current]['sha256']and bridges['source_hashes'][k]==inputs[current]['sha256'],'member parent native input differs')
        candidates,unresolved,cohort=discover_external(plan,axis,bridges,interfaces,provider,floor)
        derived_inputs=dict(plan_source=inputs['plan_source_'+f],axis_source=inputs['axis_source'],plan_graph=dict(path='separate_native_reading_graph',sha256=bindings[f]['reading_graph_sha256']),axis_graph=inputs['axis_graph'])
        docs=dict(plan=read_source(inputs['plan_source_'+f]['path'])[0],axis=read_source(inputs['axis_source']['path'])[0]);ai=csvrows(inputs['axis_components']['path'])
        current,profile=prove(candidates,dict(plan=plan,axis=axis),docs,provider,derived_inputs,load(inputs['current_T_source_config']['path']),dict(plan=pi,axis=ai),manifest['horizontal_directions_degrees'])
        for row in current:
            row['source_reading_graph_binding']=copy.deepcopy(bindings[f]);row['axis_nodes']=[next(e for e in axis['edges']if e['edge_id']==row['axis_edge_id'])[k]for k in('start_node_id','end_node_id')];row['axis_attribute_paths']=copy.deepcopy(next(e for e in axis['edges']if e['edge_id']==row['axis_edge_id'])['attribute_paths'])
        provider,local=inherit(provider,current,local,plan,bindings);records.extend(current);held.extend(unresolved);cohorts[f]=cohort;profiles[f]=profile
    checked();proof=dict(mode=MODE,inputs=inputs,floors=floors,records=records,held_external_routes=held,external_cohorts=cohorts,native_component_profiles=profiles,complete_original_adopted_provider_replayed=True,current_local_topology_parents_replayed=True,all_current_pipe_circles_screened=True,original_two_arm_rule_reused=True,old_source_graphs_unchanged=True,all_old_provider_observations_preserved=True,new_pipe_attribute_values=0,physical_Ts_added=0,human_accepted=False,whole_goal_complete=False,counts=dict(pipe_circles=sum(v['proof']['counts']['pipe_circles']for v in floors.values()),normalized_circles=sum(v['proof']['counts']['qualified']for v in floors.values()),retired_nonphysical_endpoints=sum(v['proof']['counts']['retired_nonphysical_endpoints']for v in floors.values()),new_correspondences=len(records),existing_correspondence_edges=provider['counts']['existing_correspondence_edges']))
    return proof,provider,local,outputs

def implementations():
    names=('current_two_arm_circle_routes','normalize_two_arm_circle_continuity','member_external_anchored_routes','rebuild_member_external_routes','reapply_anchored_plan_metrics','source_readability','reconstruct_wave_main_cohorts','rebuild_ordered_sideview_owners','attach_reviewed_interface_owners','third_arm_crossview_paths')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def payloads(proof,provider,local,outputs):
    values={'current-two-arm-routes.json':encode(proof),'provider-inventory.json':encode(provider),'member-local-graph.json':encode(local),'horizontal-frontier.json':encode(provider['current_horizontal_frontier'])}
    for f,(graph,rows)in outputs.items():
        values[f+'/graph_with_edges.json']=encode(graph)
        import io
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows);values[f+'/assigned_edge_device_instances.csv']=stream.getvalue().encode('utf-8-sig')
    return values

def produce(manifest,output):
    output=Path(output);require(not output.exists(),'choose a fresh two-arm route output');before=implementations();proof,provider,local,outputs=compute(load(manifest),lambda v:print(v,flush=True));require(before==implementations(),'two-arm implementations changed');values=payloads(proof,provider,local,outputs);output.mkdir(parents=True)
    for n,b in values.items():p=output/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256={n:sha(output/n)for n in values})))
    return proof,provider,local,outputs

def verify_output(output):
    output=Path(output);a=load(output/'receipt.json');require(a['mode']==MODE and a['implementation_sha256']==implementations()and sha(a['manifest']['path'])==a['manifest']['sha256']and all(sha(output/n)==h for n,h in a['output_sha256'].items()),'two-arm route receipt changed');result=compute(load(a['manifest']['path']))
    require(all((output/n).read_bytes()==b for n,b in payloads(*result).items()),'independent native two-arm route replay differs');return result

def main():
    p=argparse.ArgumentParser()
    for k in('manifest','output','verify-output'):p.add_argument('--'+k,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
            r=produce(a.manifest,a.output)
    print(r[0]['counts'],flush=True)
if __name__=='__main__':main()
