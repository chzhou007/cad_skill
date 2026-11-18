"""Native complete-cohort complementary chain extension with original providers."""
import argparse,csv,importlib,io,json,subprocess,sys,tempfile
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from legacy_named_provider_inventory import require
from complementary_anchor_chains import MODE,discover,prove,inherit
from compound_carrier_atom_origins import refine
from inherited_exploded_ball_profiles import collect as profiles,recover

def checked_parent(manifest):
    inputs=manifest['inputs'];snap=inputs['provider_snapshot'];provider=inputs['provider'];root=Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='cad-complementary-parent-')as temporary:
        out=Path(temporary)/'checked'
        cmd=[sys.executable,'-X','utf8','-B',str(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_two_arm_provider.py'),
             '--skills-root',str(Path(snap['path']).parent/'skills'),'--snapshot',snap['path'],
             '--native-run',str(Path(inputs['two_arm_proof']['path']).parent),'--provider',provider['path'],'--output',str(out)]
        run=subprocess.run(cmd,cwd=manifest['parent_replay_cwd'],capture_output=True,text=True,encoding='utf-8')
        require(run.returncode==0,'complete current two-arm provider replay failed: '+run.stderr[-4500:])
        require((out/'provider-inventory.json').read_bytes()==Path(provider['path']).read_bytes(),'replayed complete provider differs')
        execution=load(out/'execution.json');execution.pop('elapsed_seconds')
        return load(out/'provider-inventory.json'),execution

def compute(manifest,announce=lambda value:None):
    inputs=manifest['inputs']
    def checked():require(all(sha(v['path'])==v['sha256']for v in inputs.values()),'complementary chain pinned input changed')
    checked();announce('Replaying complete current provider in its original frozen runtime');provider,parent=checked_parent(manifest)
    axis=load(inputs['axis_graph']['path']);configuration=load(inputs['current_T_source_config']['path']);groups=[];held=[];floors={};docs_axis=None
    for floor in(1,2,3):
        f=str(floor);plan=load(inputs['plan_graph_'+f]['path']);graphs=dict(plan=plan,iso=axis)
        require(provider['original_provider_inventory_inputs']['plan_graph_'+f]==inputs['plan_graph_'+f]and provider['original_provider_inventory_inputs']['axis_graph']==inputs['axis_graph'],'chain graph differs from current complete parent')
        pd,pp=read_source(inputs['plan_source_'+f]['path'])
        original_components=list(csv.DictReader(Path(inputs['plan_components_'+f]['path']).open(encoding='utf-8-sig',newline='')))
        plan_components,recovery=recover(pd,plan,original_components,'plan')
        rows,pending=discover(graphs,provider,floor);held.extend(pending)
        component_reading=dict(original_inventory=inputs['plan_components_'+f],source_graph=inputs['plan_graph_'+f],
                               source=inputs['plan_source_'+f],rows=plan_components,recovery=recovery,separate_reading_inventory=True)
        if not rows:
            floors[f]=dict(candidates=0,source_checked_groups=0,plan_component_reading=component_reading,source_preflight=dict(plan=pp));continue
        announce('Floor '+f+': '+str(len(rows))+' complete unknown-chain regions; '+str(recovery['recovered_physical_source_instances'])+' recovered original plan ball valves')
        if docs_axis is None:docs_axis,ap=read_source(inputs['axis_source']['path'])
        docs=dict(plan=pd,iso=docs_axis)
        components=dict(plan=plan_components,iso=list(csv.DictReader(Path(inputs['axis_components']['path']).open(encoding='utf-8-sig',newline=''))))
        ids={v:[eid for r in rows for eid in r[v]['edges']]for v in graphs}
        native_profiles={v:profiles(docs[v],graphs[v],components[v],ids[v],v)for v in graphs}
        risks=refine(pd,plan,inputs['plan_source_'+f]['sha256'])
        hashes={v:dict(source_sha256=inputs[s]['sha256'],graph_sha256=inputs[g]['sha256'])for v,s,g in [('plan','plan_source_'+f,'plan_graph_'+f),('iso','axis_source','axis_graph')]}
        current=load(inputs['plan_reading_graph_'+f]['path']);qualified=[]
        for row in rows:
            try:qualified.append(prove(row,graphs,current,docs,provider,hashes,configuration,manifest['horizontal_directions_degrees'],components,native_profiles,risks))
            except ValueError as exc:held.append(dict(source_region=row,reason='native_complementary_chain_check_failed',detail=str(exc)))
        groups.extend(qualified);floors[f]=dict(candidates=len(rows),source_checked_groups=len(qualified),plan_component_reading=component_reading,native_component_profiles=native_profiles,source_preflight=dict(plan=pp,iso=ap),compound_risks=risks)
        announce('Floor '+f+': '+str(sum(len(r['records'])for r in qualified))+' native topology correspondences')
    records=[r for g in groups for r in g['records']];result=inherit(provider,records)
    result['plan_exploded_component_reading_inventories']={f:floors[f]['plan_component_reading']for f in floors}
    proof=dict(mode=MODE,inputs=inputs,groups=groups,records=records,held=held,floors=floors,parent_native_replay=parent,
        complete_original_provider_replayed=True,all_current_floor_regions_screened=True,all_current_plans_known_exploded_ball_population_screened=True,source_graphs_mutated=False,
        physical_values_assigned=0,DN_used_for_matching=False,off_chain_terminal_identities_assigned=False,human_accepted=False,whole_goal_complete=False,
        counts=dict(new_chain_correspondences=len(records),new_ordinary_anchors=len(result['new_complementary_chain_anchors']),
                    source_detail_differences=sum(r['source_detail_difference']for r in records),groups=len(groups),held=len(held),
                    recovered_original_plan_ball_valves=sum(v['plan_component_reading']['recovery']['recovered_physical_source_instances']for v in floors.values())))
    checked();return proof,result

def implementations():
    root=Path(__file__).resolve().parents[2]
    names=('complementary_anchor_chains','inherited_exploded_ball_profiles','third_arm_crossview_paths','compound_carrier_atom_origins','source_stable_junction_reapplication','batch_native_path_coverage','source_readability')
    return dict(entry=sha(__file__),parent_worker=sha(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_two_arm_provider.py'),
                legacy_exploded_owner=sha(Path(__file__).parent/'legacy_v17/build_edges.py'),
                **{n:sha(importlib.import_module(n).__file__)for n in names})

def payloads(proof,provider):
    values={name:encode(value)for name,value in [('complementary-chains.json',proof),('provider-inventory.json',provider),('horizontal-frontier.json',provider['current_horizontal_frontier'])]}
    for f,spec in provider['plan_exploded_component_reading_inventories'].items():
        rows=spec['rows'];fields=list(dict.fromkeys(key for row in rows for key in row))
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
        values['plan-component-reading/'+f+'/assigned_edge_device_instances.csv']=stream.getvalue().encode('utf-8-sig')
    return values

def produce(manifest,output):
    output=Path(output);require(not output.exists(),'choose a fresh complementary chain output');before=implementations()
    proof,provider=compute(load(manifest),lambda value:print(value,flush=True));require(before==implementations(),'complementary implementations changed')
    output.mkdir(parents=True);values=payloads(proof,provider)
    for n,v in values.items():p=output/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v)
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256={n:sha(output/n)for n in values})))
    return proof,provider

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json')
    require(receipt['mode']==MODE and receipt['implementation_sha256']==implementations()and sha(receipt['manifest']['path'])==receipt['manifest']['sha256']and all(sha(output/n)==h for n,h in receipt['output_sha256'].items()),'complementary chain receipt changed')
    proof,provider=compute(load(receipt['manifest']['path']))
    for name,value in payloads(proof,provider).items():
        require(value==(output/name).read_bytes(),'independent native complementary proof, provider or reading inventory differs')
    return proof,provider

def main():
    p=argparse.ArgumentParser()
    for n in('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:proof,provider=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
            proof,provider=produce(a.manifest,a.output)
    print(proof['counts'],flush=True)

if __name__=='__main__':main()
