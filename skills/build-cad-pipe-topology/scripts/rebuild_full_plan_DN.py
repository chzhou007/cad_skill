"""Replay each local plan owner and read DN over every current plan edge."""
import argparse,collections,importlib,sys
from pathlib import Path
_PIPELINE=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(_PIPELINE)not in sys.path:sys.path.insert(0,str(_PIPELINE))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_replay_session import verify_once
from full_plan_DN_source import collect

MODE='complete_local_plan_native_DN_batch_v1'
PARENTS=dict(reviewed_interface_owners='attach_reviewed_interface_owners',reviewed_drawing_gaps='reconstruct_reviewed_plan_gaps',
    wave_main_cohort='reconstruct_wave_main_cohorts')


def checked(item):
    path=Path(item['path']).resolve()
    if sha(path)!=item['sha256']:raise ValueError('full-plan DN input changed: '+str(path))
    return path


def compute(manifest,announce=lambda x:None):
    plans=manifest['plans'];floors=[p['floor']for p in plans]
    if not plans or len(set(floors))!=len(floors)or any(isinstance(f,bool)or not isinstance(f,int)for f in floors):
        raise ValueError('unique explicit local floors required')
    # Cheap schema/hash/review checks precede every expensive native parent.
    for item in plans:
        for spec in item['inputs'].values():checked(spec)
        if 'reviewed_boundaries'in item:checked(item['reviewed_boundaries'])
        if 'reviewed_horizontal_scope'in item:
            from reviewed_horizontal_DN_scopes import prepare
            review=item['reviewed_horizontal_scope'];rp={k:checked(v)for k,v in review['inputs'].items()}
            prepare(load(checked(item['inputs']['graph'])),rp,review['question_id'],sha(checked(item['inputs']['source'])))
    outputs={};preflights={};parents={};reviewed={}
    for item in sorted(plans,key=lambda x:x['floor']):
        floor=str(item['floor']);paths={k:checked(v)for k,v in item['inputs'].items()}
        graph_path=paths['graph'];graph=load(graph_path);sh,gh=sha(paths['source']),sha(graph_path)
        if graph_path.name!='graph_with_edges.json'or paths['devices']!=graph_path.with_name('assigned_edge_device_instances.csv'):
            raise ValueError('canonical local graph and component inventory required')
        doc,preflights[floor]=read_source(paths['source'])
        if item['parent_mode']not in PARENTS:raise ValueError('unsupported full-plan topology owner')
        announce(f'{floor}F: replaying native local topology owner before full-plan DN')
        verifier=importlib.import_module(PARENTS[item['parent_mode']]).verify_output
        audit=verify_once(graph_path.parent,verifier)
        if audit['output_graph_sha256']!=gh or audit['inputs']['source']['sha256']!=sh:raise ValueError('local native parent differs')
        parents[floor]=dict(mode=item['parent_mode'],graph_sha256=gh,component_sha256=sha(paths['devices']),native_replay_passed=True)
        circle=load(paths['circle_policy'])if 'circle_policy'in paths else None;seeds=[];reviewed[floor]=[]
        if 'reviewed_boundaries'in item:
            rp=checked(item['reviewed_boundaries'])
            from reviewed_main_DN_boundaries import verify_output as verify_boundaries
            proof=verify_once(rp.parent,verify_boundaries)
            if proof['source_sha256']!=sh or proof['current_graph_sha256']!=gh:raise ValueError('reviewed main DN scope graph differs')
            for row in proof['records']:
                seeds.append(dict(edge_id=row['edge_id'],nominal_mm=row['nominal_mm'],evidence_id='reviewed:'+proof['question_id']+':'+row['edge_id'],scope_only=True))
            reviewed[floor].append(dict(question_id=proof['question_id'],evidence_file_sha256=sha(rp),whole_axis_values_assigned=0))
        if 'reviewed_horizontal_scope'in item:
            from reviewed_horizontal_DN_scopes import collect as reviewed_collect
            policy=item['reviewed_horizontal_scope'];rp={k:checked(v)for k,v in policy['inputs'].items()}
            if rp['source']!=paths['source']:raise ValueError('reviewed horizontal source differs from current floor')
            proof=reviewed_collect(doc,graph,rp,policy['question_id'],sh,gh,circle)
            seeds.extend(proof['records']);reviewed[floor].append(proof)
        outputs[floor]=collect(doc,graph,sh,gh,seeds,announce,circle)
        if sha(graph_path)!=gh or sha(paths['source'])!=sh or sha(paths['devices'])!=parents[floor]['component_sha256']:
            raise ValueError('local topology or source changed during DN reading')
        if len(outputs[floor]['records'])!=len(graph['edges']):raise ValueError('full local edge coverage incomplete')
        for spec in item['inputs'].values():checked(spec)
        announce(f'{floor}F complete local DN: {outputs[floor]["counts"]}')
    counts=dict(total_plan_edges=sum(x['counts']['graph_edges']for x in outputs.values()),
        known_plan_DN_edges=sum(x['counts']['known_DN_edges']for x in outputs.values()))
    return dict(mode=MODE,floors=outputs,counts=counts,local_parent_replay=parents,source_preflight=preflights,
        reviewed_scopes=reviewed,crossview_mapping_required_to_read_plan=False,axis_values_fused=0,
        local_graphs_mutated=False,physical_lengths_assigned=0,human_accepted=False,hil_ready=False)


def implementation_hashes():
    names=('full_plan_DN_source','full_plan_DN_inheritance','discover_native_component_DN','component_DN_underline_end',
        'reviewed_horizontal_DN_scopes','through_source_DN_inheritance','source_direct_dn_evidence','plan_pipe_diameter_scopes',
        'batch_native_path_coverage','qualified_inline_DN_evidence','native_inherited_duplicate_circle_evidence','source_readability')
    return dict({name:sha(importlib.import_module(name).__file__)for name in names},entry=sha(__file__))


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'full-plan-DN-receipt.json')
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('full-plan DN implementation changed')
    manifest_path=checked(receipt['manifest']);result=compute(load(manifest_path))
    if sha(directory/'full-plan-DN-results.json')!=receipt['output_sha256']or encode(result)!=(directory/'full-plan-DN-results.json').read_bytes():
        raise ValueError('whole-plan DN native independent replay differs')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:
        if a.manifest or a.output:p.error('verification cannot override inputs')
        print(verify_output(a.verify_output)['counts']);return
    if not a.manifest or not a.output:p.error('fixed input manifest and new output required')
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(load(a.manifest),lambda x:print(x,flush=True));a.output.mkdir(parents=True)
    target=a.output/'full-plan-DN-results.json';target.write_bytes(encode(result))
    (a.output/'full-plan-DN-receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(a.manifest.resolve()),sha256=sha(a.manifest)),
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(result['counts'],flush=True)


if __name__=='__main__':main()
