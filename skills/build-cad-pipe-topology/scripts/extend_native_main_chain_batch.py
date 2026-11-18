"""Batch inherited main-chain rules over every floor of a replayed axis batch."""
import argparse,copy
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from apply_crossview_rule_batch import checked
from rebuild_wave_cohort_crossview_batch import verify_output as verify_parent
from native_replay_session import verify_once
from batch_native_main_chains import apply,MODE
from batch_apply_crossview_rules import evaluate_all_axis_edges
from batch_rule_contract import check
from native_plan_projection_lengths import unit_evidence,lengths
from source_readability import read_source


def compute(manifest,announce=lambda message:None):
    receipt=checked(manifest['parent_receipt']);announce('Replaying current full576 parent and all native source dependencies')
    parent=verify_once(receipt.parent,verify_parent);wave_manifest=load(checked(load(receipt)['manifest']))
    old_receipt=checked(wave_manifest['inputs']['parent_receipt']);base=load(checked(load(old_receipt)['manifest']))
    local=load(checked(base['inputs']['inventory_receipt']))['local_inputs']
    axis_dir=checked(base['inputs']['identity_receipt']).parent;axis_path=axis_dir/'graph_with_edges.json';axis=load(axis_path)
    if sha(axis_path)!=parent['identity_graph_sha256']:raise ValueError('current axis identity graph changed')
    cohort=checked(wave_manifest['inputs']['cohort_audit']).parent/'graph_with_edges.json'
    changed_floor=str(parent['current_wave_cohort']['floor']);output=copy.deepcopy(parent);extensions={};preflights={}
    ad,preflights['iso']=read_source(local[changed_floor]['iso_source']['path'])
    for floor,previous in sorted(parent['floors'].items()):
        spec=local[floor]
        for item in spec.values():checked(item)
        plan_path=cohort if floor==changed_floor else checked(spec['plan_graph'])
        plan=load(plan_path);pd,preflights['plan'+floor]=read_source(spec['plan_source']['path'])
        hashes=dict(plan=dict(source_sha256=spec['plan_source']['sha256'],graph_sha256=sha(plan_path)),
            iso=dict(source_sha256=spec['iso_source']['sha256'],graph_sha256=sha(axis_path)))
        extension=apply(dict(plan=pd,iso=ad),dict(plan=plan,iso=axis),previous,int(floor),hashes);extensions[floor]=extension
        if extension['records']:
            output['floors'][floor]['records'].extend(extension['records'])
            policy=checked(base['metric_policies'][floor]);units=unit_evidence(pd,load(policy))
            for row in extension['records']:
                item=dict(mapping_id=row['mapping_id'],plan_edges=row['plan_edges'],iso_edges=row['iso_edges'])
                native=extension['native_evidence'][row['mapping_id']]['plan']['path_coverage']
                try:item['projection']=lengths(plan,native,row,units)
                except ValueError as exc:item.update(projection=None,reason=str(exc))
                item['per_axis_edge_allocation_known']=False;output['metrics'][floor].append(item)
        announce(f'{floor}F native main chain batch: {len(extension["records"])} source-checked paths, '+
            f'{sum(len(r["iso_edges"]) for r in extension["records"])} additional axis-edge candidates')
    output['all_axis_edges']=evaluate_all_axis_edges(axis,output['floors'],load(checked(base['inputs']['prior_attributes'])))
    output['summary']=check(output['all_axis_edges'],axis)
    output.update(mode=MODE,parent_mode=parent['mode'],native_main_chain_extension=extensions,
        chain_source_preflight=preflights,parent_batch_receipt_sha256=sha(receipt),
        attributes_fused=False,human_accepted=False,hil_ready=False)
    checked(manifest['parent_receipt']);return output


def implementation_hashes():
    import batch_native_main_chains,native_replay_session,native_python_replay_adapter,match_source_checked_crossview_paths
    return dict(entry=sha(__file__),chain=sha(batch_native_main_chains.__file__),
        cache=sha(native_replay_session.__file__),child_replay=sha(native_python_replay_adapter.__file__),
        native_path_kernel=sha(match_source_checked_crossview_paths.__file__))


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'main-chain-batch-receipt.json')
    if receipt['implementation_sha256']!=implementation_hashes():raise ValueError('native main-chain batch implementation changed')
    result=compute(load(checked(receipt['manifest'])))
    if encode(result)!=(directory/'main-chain-batch-results.json').read_bytes():raise ValueError('complete main-chain native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path);parser.add_argument('--output',type=Path);parser.add_argument('--verify-output',type=Path)
    args=parser.parse_args()
    if args.verify_output:print(verify_output(args.verify_output)['summary'],flush=True);return
    if not args.manifest or not args.output:parser.error('fixed manifest and new output required')
    if args.output.exists():raise FileExistsError(args.output)
    result=compute(load(args.manifest),lambda message:print(message,flush=True));args.output.mkdir(parents=True)
    (args.output/'main-chain-batch-results.json').write_bytes(encode(result))
    (args.output/'main-chain-batch-receipt.json').write_bytes(encode(dict(mode=MODE,
        manifest=dict(path=str(args.manifest.resolve()),sha256=sha(args.manifest)),implementation_sha256=implementation_hashes(),
        output_sha256=sha(args.output/'main-chain-batch-results.json'),human_accepted=False)))
    print(result['summary'],flush=True)

if __name__=='__main__':main()
