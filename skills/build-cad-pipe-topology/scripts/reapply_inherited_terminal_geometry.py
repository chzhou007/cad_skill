"""Batch inherited marker geometry and native crossovers after branch publication."""
import argparse,copy,hashlib,importlib,subprocess,sys,tempfile
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from legacy_named_provider_inventory import require,current_plan_reader
from source_readability import read_source
from anchored_terminal_branch_reapplication import discover,source_terminal_outward,outward,branch_snapshot
from confirmed_circle_crossover_path_reapplication import audit as plan_coverage
from crossview_equipment_branch_inventory import index_graph,native_tee
from native_plan_projection_lengths import lengths
from inherited_marker_and_crossover_evidence import population,collect,path_coverage,BRIDGE

MODE='native_inherited_terminal_geometry_reapplication_v1'

def checked_parent(manifest):
    inputs=manifest['inputs'];snap=inputs['parent_snapshot'];root=Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='cad-inherited-terminal-parent-')as tmp:
        out=Path(tmp)/'checked';cmd=[sys.executable,'-X','utf8','-B',str(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_terminal_branch_provider.py'),
            '--skills-root',str(Path(snap['path']).parent/'skills'),'--snapshot',snap['path'],'--native-run',str(Path(inputs['parent_proof']['path']).parent),'--viewer',manifest['parent_viewer'],'--output',str(out)]
        run=subprocess.run(cmd,cwd=manifest['parent_replay_cwd'],capture_output=True,text=True,encoding='utf-8')
        require(run.returncode==0,'complete original branch provider failed: '+run.stderr[-4000:])
        require((out/'parent-proof.json').read_bytes()==Path(inputs['parent_proof']['path']).read_bytes()and(out/'provider.json').read_bytes()==Path(inputs['parent_provider']['path']).read_bytes(),'current branch provider identity changed')
        execution=load(out/'execution.json');execution.pop('elapsed_seconds');return load(out/'parent-proof.json'),load(out/'provider.json'),execution

def qualify(row,graphs,docs,hashes,reader,dns,units,markers,pop):
    plan,geometry,projection=source_terminal_outward(docs['plan'],graphs['plan'],row['plan_anchor'],set(row['blocked']['plan']),row['system'],row['floor'])
    axis=outward(graphs['iso'],row['axis_anchor'],set(row['blocked']['iso']),row['system'],row['floor'])
    require(axis['terminal_kind']=='drawing_marker_interface','axis third arm requires another boundary owner')
    item=markers[axis['terminal_id']];require(item['status']=='passed','native marker population held: '+item.get('reason',''))
    ports=[p for p in item['proof']['records']if p['edge_id']==row['axis_edge_id']and p['system']==row['system']];require(len(ports)==1,'typed native branch port is not unique')
    ph,ah=hashes['plan'],hashes['iso'];pc=plan_coverage(docs['plan'],graphs['plan'],row['plan_edge_id'],row['plan_anchor'],ph['source_sha256'],ph['graph_sha256'],reader)
    ac=path_coverage(docs['iso'],graphs['iso'],row['axis_edge_id'],ah['source_sha256'],ah['graph_sha256'],pop)
    for part in pc['edges']:
        require(all(s['status']=='single_source_line_covers'for s in part['segments']),'plan branch has another unverified source fragment')
    for part in ac['edges']:
        for s in part['segments']:
            if s['index']==ports[0]['display_segment_index']:continue
            require(s['status']in('single_source_line_covers',BRIDGE),'axis branch has another unsupported primitive')
            if s['status']==BRIDGE:require(s['source_crossover_evidence']['crossed_pipe_connected']is False and s['physical_gap_length_mm']is None,'crossover became a new junction or measured length')
    pt=reader(docs['plan'],graphs['plan'],row['plan_anchor'],ph['source_sha256'],ph['graph_sha256']);at=native_tee(docs['iso'],graphs['iso'],row['axis_anchor'],ah['source_sha256'],ah['graph_sha256'])
    edge=index_graph(graphs['plan'])[1][row['plan_edge_id']];dn=copy.deepcopy(dns[row['plan_edge_id']]);require(dn['system']==row['system']and dn['scope_paths']==edge['attribute_paths'],'inherited plan DN has another scope')
    metric=lengths(graphs['plan'],pc,dict(plan_edges=[row['plan_edge_id']],system=row['system']),units)
    return dict(row,routes=dict(plan=plan,iso=axis),native_checks=dict(plan=dict(native_T=pt,native_path=pc,snapshot=branch_snapshot(graphs['plan'],plan['edges'])),iso=dict(native_T=at,native_path=ac,snapshot=branch_snapshot(graphs['iso'],axis['edges']))),
        plan_terminal_glyph=geometry,temporary_reader_projection=projection,axis_drawing_port=copy.deepcopy(ports[0]),plan_DN_record=dn,plan_horizontal_projection=metric,
        source_scope='source_checked_third_arm_drawing_context_not_remote_identity',physical_port_verified=False,remote_equipment_identity_inferred=False,whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,
        vertical_values_assigned=0,source_graphs_mutated=False,human_accepted=False,inherited_marker_and_crossover_readers_reapplied=True)

def compute(manifest,announce=lambda x:None):
    inputs=manifest['inputs'];checked=lambda:require(all(sha(v['path'])==v['sha256']for v in inputs.values()),'inherited geometry pinned input changed')
    checked();announce('Independently replaying the complete published branch source and actual provider');parent,provider,execution=checked_parent(manifest)
    require(parent['inputs']['parent_proof']==inputs['main_proof'],'main-chain proof differs from independently replayed source parent');main=load(inputs['main_proof']['path'])
    graphs={v:load(inputs[g]['path'])for v,g in [('plan','plan_graph'),('iso','axis_graph')]};docs={};preflight={};hashes={}
    for view,s,g in [('plan','plan_source','plan_graph'),('iso','axis_source','axis_graph')]:docs[view],preflight[view]=read_source(inputs[s]['path']);hashes[view]=dict(source_sha256=inputs[s]['sha256'],graph_sha256=inputs[g]['sha256'])
    announce('Replaying original complete native marker population and five crossover rules');pop=population(docs['iso'],hashes['iso']['source_sha256']);markers={}
    for node in graphs['iso']['nodes']:
        if node.get('subtype')!='external_system_interface':continue
        try:markers[node['node_id']]=dict(status='passed',proof=collect(docs['iso'],graphs['iso'],node['node_id'],hashes['iso']['source_sha256'],hashes['iso']['graph_sha256'],pop))
        except ValueError as exc:markers[node['node_id']]=dict(status='held',reason=str(exc))
    candidates,discovery_held=discover(main,provider,graphs);existing=[h for h in discovery_held if h['reason']=='old axis branch provider must be preserved'];pending=[h for h in discovery_held if h not in existing]
    require(len(existing)==len(parent['records']),'existing published third-arm population changed')
    configuration=load(inputs['current_T_source_config']['path']);reader=current_plan_reader(configuration,hashes['plan']['source_sha256'],hashes['plan']['graph_sha256']);records=[]
    for row in candidates:
        try:
            local=main['floors'][str(row['floor'])];require(local['current_plan_DN']['graph_sha256']==hashes['plan']['graph_sha256'],'inherited full-plan DN graph changed')
            records.append(qualify(row,graphs,docs,hashes,reader,{r['edge_id']:r for r in local['current_plan_DN']['records']},local['units'],markers,pop))
        except ValueError as exc:pending.append(dict(mapping_id=row['mapping_id'],axis_edge_id=row['axis_edge_id'],plan_edge_id=row['plan_edge_id'],reason=str(exc)))
    checked();return dict(mode=MODE,inputs=inputs,records=records,pending=pending,original_published_records=copy.deepcopy(parent['records']),parent_native_replay=execution,source_preflight=preflight,native_population=pop['proof'],marker_population=markers,
        complete_published_parent_replayed=True,all_current_marker_interfaces_screened=True,all_current_main_third_arms_screened=True,old_published_records_unchanged=True,source_graphs_mutated=False,new_physical_nodes_created=0,
        crossed_pipes_connected=False,whole_axis_DN_assigned=0,whole_axis_lengths_assigned=0,vertical_values_assigned=0,human_accepted=False,whole_goal_complete=False,
        counts=dict(marker_interfaces=len(markers),marker_source_pass=sum(x['status']=='passed'for x in markers.values()),marker_source_held=sum(x['status']=='held'for x in markers.values()),original_published_branches=len(existing),new_branch_contexts=len(records),pending_branches=len(pending)))

def implementations():
    names=('inherited_marker_and_crossover_evidence','confirmed_circle_crossover_path_reapplication','anchored_terminal_branch_reapplication','current_plan_crossover_path_reapplication','native_drawing_marker_ports','native_plan_projection_lengths','source_readability');root=Path(__file__).resolve().parents[2]
    from inherited_exploded_ball_profiles import owner
    old=owner()
    return dict(entry=sha(__file__),fixed_parent_worker=sha(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_terminal_branch_provider.py'),original_edges=sha(old.__file__),original_geometry=sha(old.graph.__file__),original_equipment_network=sha(old.equipment_graph.__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})
def produce(manifest,output):
    output=Path(output);require(not output.exists(),'fresh inherited geometry output required');before=implementations();proof=compute(load(manifest),lambda x:print(x,flush=True));require(before==implementations(),'native geometry implementation changed')
    output.mkdir(parents=True);p=output/'inherited-terminal-geometry.json';p.write_bytes(encode(proof));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256=sha(p))));return proof
def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');require(r['mode']==MODE and r['implementation_sha256']==implementations()and sha(r['manifest']['path'])==r['manifest']['sha256']and sha(output/'inherited-terminal-geometry.json')==r['output_sha256'],'inherited geometry receipt changed')
    proof=compute(load(r['manifest']['path']));require(encode(proof)==(output/'inherited-terminal-geometry.json').read_bytes(),'independent inherited geometry replay differs');return proof
def main():
    p=argparse.ArgumentParser()
    for k in('manifest','output','verify-output'):p.add_argument('--'+k,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:proof=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
            proof=produce(a.manifest,a.output)
    print(proof['counts'],flush=True)
if __name__=='__main__':main()
