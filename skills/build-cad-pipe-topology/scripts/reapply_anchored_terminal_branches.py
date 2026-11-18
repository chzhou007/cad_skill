"""Batch all third arms exposed by the current independently mapped main chains."""
import argparse,hashlib,importlib,subprocess,sys,tempfile
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from legacy_named_provider_inventory import require,current_plan_reader
from source_readability import read_source
from anchored_terminal_branch_reapplication import MODE,discover,qualify

def checked_parent(manifest):
    inputs=manifest['inputs'];root=Path(__file__).resolve().parents[2];snap=inputs['parent_snapshot']
    with tempfile.TemporaryDirectory(prefix='cad-anchored-terminal-parent-')as tmp:
        out=Path(tmp)/'verified';cmd=[sys.executable,'-X','utf8','-B',str(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_complementary_attributes.py'),
            '--skills-root',str(Path(snap['path']).parent/'skills'),'--snapshot',snap['path'],'--native-run',str(Path(inputs['parent_proof']['path']).parent),
            '--viewer',manifest['parent_viewer'],'--output',str(out)]
        run=subprocess.run(cmd,cwd=manifest['parent_replay_cwd'],capture_output=True,text=True,encoding='utf-8')
        require(run.returncode==0,'published source/provider replay failed: '+run.stderr[-4000:])
        require((out/'parent-proof.json').read_bytes()==Path(inputs['parent_proof']['path']).read_bytes()and(out/'provider.json').read_bytes()==Path(inputs['parent_provider']['path']).read_bytes(),'published parent native identity differs')
        execution=load(out/'execution.json');execution.pop('elapsed_seconds');return load(out/'parent-proof.json'),load(out/'provider.json'),execution

def compute(manifest,announce=lambda value:None):
    inputs=manifest['inputs'];checked=lambda:require(all(sha(v['path'])==v['sha256']for v in inputs.values()),'anchored interface pinned input changed')
    checked();announce('Independently replaying complete published parent and its actual viewer adoption');parent,provider,execution=checked_parent(manifest)
    require(parent['counts']['pending']==0,'unresolved parent cannot seed a branch batch')
    graphs={v:load(inputs[k]['path'])for v,k in [('plan','plan_graph'),('iso','axis_graph')]}
    candidates,pending=discover(parent,provider,graphs);docs={};preflight={};hashes={}
    for view,source,graph in [('plan','plan_source','plan_graph'),('iso','axis_source','axis_graph')]:
        docs[view],preflight[view]=read_source(inputs[source]['path']);hashes[view]=dict(source_sha256=inputs[source]['sha256'],graph_sha256=inputs[graph]['sha256'])
    configuration=load(inputs['current_T_source_config']['path']);reader=current_plan_reader(configuration,hashes['plan']['source_sha256'],hashes['plan']['graph_sha256']);records=[];cache={}
    announce('Reapplying original outward, terminal glyph, marker port, T and native path owners to '+str(len(candidates))+' third arms')
    for row in candidates:
        try:
            local=parent['floors'][str(row['floor'])];require(local['current_plan_DN']['graph_sha256']==hashes['plan']['graph_sha256'],'parent local DN belongs to another plan')
            dns={r['edge_id']:r for r in local['current_plan_DN']['records']}
            records.append(qualify(row,graphs,docs,hashes,reader,dns,local['units'],cache))
        except ValueError as exc:pending.append(dict(mapping_id=row['mapping_id'],axis_edge_id=row['axis_edge_id'],plan_edge_id=row['plan_edge_id'],plan_anchor=row['plan_anchor'],axis_anchor=row['axis_anchor'],reason=str(exc)))
    checked()
    return dict(mode=MODE,inputs=inputs,records=records,pending=pending,parent_native_replay=execution,source_preflight=preflight,
        all_current_independent_main_third_arms_screened=True,complete_published_parent_replayed=True,graph_mutated=False,old_providers_replaced=False,
        remote_equipment_identities_assigned=0,physical_ports_created=0,whole_axis_DN_assigned=0,whole_axis_lengths_assigned=0,vertical_values_assigned=0,
        counts=dict(considered_third_arms=len(candidates),source_qualified_branch_contexts=len(records),pending=len(pending)),human_accepted=False,whole_goal_complete=False)

def implementations():
    root=Path(__file__).resolve().parents[2];names=('anchored_terminal_branch_reapplication','current_plan_crossover_path_reapplication','ordered_anchor_branch_paths','cad_ceiling_native_rules','native_drawing_marker_ports','batch_native_path_coverage','source_checked_plan_path_coverage','source_reviewed_circle_branch_evidence','native_plan_projection_lengths','source_readability')
    return dict(entry=sha(__file__),fixed_parent_worker=sha(root/'orchestrate-cad-drawing-pipeline/scripts/replay_fixed_complementary_attributes.py'),**{n:sha(importlib.import_module(n).__file__)for n in names})
def produce(manifest,output):
    output=Path(output);require(not output.exists(),'fresh anchored terminal output required');before=implementations();proof=compute(load(manifest),lambda x:print(x,flush=True));require(implementations()==before,'branch implementation changed')
    output.mkdir(parents=True);p=output/'anchored-terminal-branches.json';p.write_bytes(encode(proof));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=before,output_sha256=sha(p))))
    return proof
def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');require(receipt['mode']==MODE and receipt['implementation_sha256']==implementations()and sha(receipt['manifest']['path'])==receipt['manifest']['sha256']and sha(output/'anchored-terminal-branches.json')==receipt['output_sha256'],'anchored branch receipt changed')
    proof=compute(load(receipt['manifest']['path']));require(encode(proof)==(output/'anchored-terminal-branches.json').read_bytes(),'independent native branch replay differs');return proof
def main():
    p=argparse.ArgumentParser()
    for n in('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:result=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('fixed manifest and fresh output required')
            result=produce(a.manifest,a.output)
    print(result['counts'],flush=True)
if __name__=='__main__':main()
