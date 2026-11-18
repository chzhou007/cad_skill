"""Derive a strict producer API policy from completed, hash-bound observations.

This assets the existing project recipe. It does not infer CAD connectivity,
certify unseen processes, qualify unproved owned files, or claim native IO
closure. The original producer must subsequently run under the derived policy.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from producer_process_identity import bind_tree, bind_access_records


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text('utf8'))


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf8')


def pin(path):
    return dict(path=str(Path(path).resolve()), sha256=sha(path))


def require(value, message):
    if not value:
        raise ValueError(message)


def source_in_package(package, relative):
    require(isinstance(relative, str) and relative and '\\' not in relative and ':' not in relative
            and not PurePosixPath(relative).is_absolute()
            and all(p not in ('', '.', '..') for p in relative.split('/')), 'Invalid package-relative source')
    path = (package / relative).resolve()
    require(path.is_relative_to(package), 'Seed source escaped package')
    return path


def compute(result_path, package, seed_manifest_path):
    result_path, package, seed_manifest_path = map(lambda p: Path(p).resolve(), (result_path, package, seed_manifest_path))
    before = [pin(p) for p in (result_path, seed_manifest_path)]
    result = load(result_path)
    require(result.get('status') == 'producer_command_returned' and result.get('exit_code') == 0,
            'Completed successful producer discovery required')
    require(result.get('strict_production_closure_not_inferred_from_exit_code') is True,
            'Producer result must retain its closure scope')
    receipt_root = (result_path.parent / 'work/producer-observation').resolve()
    reports, bound_files = [], []
    for row in result['observations']:
        path = Path(row['path']).resolve()
        require(path.is_relative_to(receipt_root) and sha(path) == row['sha256'], 'Observation receipt moved or changed')
        report = load(path)
        require(report['mode'] in ('producer_API_input_discovery_v1', 'producer_API_input_enforcement_v1'), 'Unknown observation mode')
        require(not report['changed_inputs'], 'Discovery observed input changes; diagnose before deriving policy')
        require(report['pid'] == row['pid'] and report['parent_pid'] == row['parent_pid'], 'Observation identity differs')
        reports.append(report)
        bound_files.append(pin(path))
    require(bool(reports) and len({r['input_index_sha256'] for r in reports}) == 1, 'One actual producer input revision required')
    root = result['actual_root_pid']
    tree=bind_tree(reports,root)
    def access_epoch(row):
        if row.get('producer_observation'):
            binding=row['producer_observation'];require(sha(binding['path'])==binding['sha256'],'Adapter observation binding changed')
            return load(binding['path'])
        if row.get('actual_access_receipt'):
            binding=row['actual_access_receipt'];require(sha(binding['path'])==binding['sha256'],'Actual adapter receipt changed')
            return load(binding['path'])
        return None
    accesses = result['access_receipts']
    bind_access_records(accesses,tree,access_epoch)
    require(not any(r['unrecorded_reads'] for r in accesses), 'Original adapter has unrecorded input attempts')
    index_sha = reports[0]['input_index_sha256']
    index_path = package / 'indexes' / (index_sha + '.json')
    if not index_path.exists():
        index_path = package / 'logical-input-index.json'
    require(sha(index_path) == index_sha, 'Original producer index changed')
    index = load(index_path)
    for report in reports:
        require(report['helper_binding'] == index['producer_observation'], 'Mixed observation helper/policy revision')
    for key, hash_key in [('relative', 'sha256'), ('policy_relative', 'policy_sha256')]:
        binding = index['producer_observation']
        require(sha(source_in_package(package, binding[key])) == binding[hash_key], 'Observation code or policy changed')
    policy = dict(mode='producer_API_input_enforcement_v1', owned_seeds={}, additional_files={}, directories={}, negative=[])
    negative, ownership_holds, unsupported = set(), [], []
    work=Path(result.get('actual_work',result_path.parent/'work')).resolve()
    parents,qualified_parents={},{}
    for row in index.get('generated_local_parents',{}).values():
        target=(work/row['relative']).resolve();receipt=(work/row['producer_receipt_relative']).resolve()
        require(target.is_relative_to(work)and receipt.is_relative_to(work),'Generated parent escaped actual work')
        key=os.path.normcase(str(target))
        require(key not in parents or parents[key]==row,'Conflicting generated parent roles')
        parents[key]=row

    def qualify_parent(path,state,row):
        require(state.get('kind')=='file'and state.get('sha256',row['sha256'])==row['sha256']and sha(path)==row['sha256'],
                'Generated parent content changed')
        receipt=work/row['producer_receipt_relative']
        require(sha(receipt)==row['producer_receipt_sha256'],'Generated parent producer receipt changed')
        proof=load(receipt);pointer=row['producer_field']
        require(proof.get('mode')=='raw_CAD_to_current_local_topology_delivered_API_input_replay_v1'and
            len(pointer)==3 and pointer[0]=='local_topologies'and type(pointer[1])is int and pointer[1]>=0 and
            pointer[2]in('graph','components'),'Generated parent requires original actual output role')
        record=proof['local_topologies'][pointer[1]]
        require(record.get('graph_and_component_bytes_exact')is True and record[pointer[2]]['sha256']==row['sha256'],
                'Generated parent differs from proved producer output')
        qualified_parents[path]=dict(input=pin(path),producer_receipt=pin(receipt),producer_field=pointer)

    def add(path, state):
        require(isinstance(path, str) and os.path.isabs(path), 'Absolute observed input identity required')
        parent=parents.get(os.path.normcase(os.path.abspath(path)))
        if parent is not None:
            qualify_parent(path,state,parent)
            return
        kind = state.get('kind')
        if kind == 'file':
            require(Path(path).resolve().is_relative_to(package), 'Positive producer file is outside the delivered package')
            digest = state.get('sha256')
            require(isinstance(digest, str) and len(digest) == 64 and sha(path) == digest, 'Observed input file changed or lacks content binding')
            prior = policy['additional_files'].get(path)
            require(prior is None or prior == digest, 'Conflicting file observations')
            policy['additional_files'][path] = digest
        elif kind == 'directory':
            require(Path(path).resolve().is_relative_to(package), 'Positive producer directory is outside the delivered package')
            entries = state.get('entries')
            require(isinstance(entries, list) and all(isinstance(x, str) for x in entries), 'Observed directory members required')
            require(os.listdir(path) == entries, 'Observed directory state changed')
            require(path not in policy['directories'] or policy['directories'][path] == entries, 'Conflicting directory observations')
            policy['directories'][path] = entries
        elif kind == 'missing':
            try:
                os.stat(path)
            except FileNotFoundError:
                negative.add(path)
            else:
                raise ValueError('Previously missing input appeared')
        else:
            unsupported.append(dict(path=path, state=state))

    for report in reports:
        for path, state in report['immutable_inputs'].items():
            add(path, state)
        for row in report['unresolved']:
            if row['role'] == 'owned_output':
                ownership_holds.append(row)
                continue
            add(row['path'], report['immutable_inputs'].get(row['path'], row['state']))
    require(not ownership_holds, 'Unproved owned reads cannot be converted to fixed seeds from final outputs')
    require(not unsupported, 'Unsupported resource/error states require explicit diagnosis')
    forbidden = set(index['forbidden_historical_final_graph_hashes'])
    seeds = load(seed_manifest_path)
    require(seeds['schema'] == 'delivered_producer_startup_seed_bindings_v1', 'Explicit startup seed source bindings required')
    seed_sources = []
    for row in seeds['seeds']:
        relative = row['relative']
        source_in_package(package, relative)  # Same relative-path contract; target is later under work.
        require(row['role'] in ('runtime_cache_seed', 'execution_entry', 'execution_config'), 'Unsupported startup seed role')
        source = source_in_package(package, row['source_relative'])
        require(sha(source) == row['sha256'] and row['sha256'] not in forbidden, 'Startup seed changed or is a historical final graph')
        require(relative not in policy['owned_seeds'], 'Duplicate startup seed destination')
        policy['owned_seeds'][relative] = row['sha256']
        seed_sources.append(dict(relative=relative, role=row['role'], source=pin(source)))
    require(len({n.casefold() for n in policy['owned_seeds']}) == len(policy['owned_seeds']), 'Case-insensitive seed collision')
    policy['negative'] = sorted(negative)
    derivation = dict(mode='completed_producer_observations_to_strict_API_policy_v1', inputs=before,
        source_index=pin(index_path), observation_files=bound_files, root_pid=root, observed_processes=len(reports),
        process_identity_mode=tree['identity_mode'],reused_PIDs=tree['reused_PIDs'],
        seed_sources=seed_sources,qualified_generated_parent_inputs=list(qualified_parents.values()),
        input_files=len(policy['additional_files']), input_directories=len(policy['directories']),
        negative_probes=len(policy['negative']), raw_CAD_values_assigned=0,
        discovery_does_not_prove_unseen_process_closure=True, strict_producer_execution_required=True,
        general_native_IO_or_OS_sandbox_claimed=False, human_accepted=False)
    require(all(sha(p['path']) == p['sha256'] for p in before + bound_files), 'Discovery inputs changed during policy derivation')
    return policy, derivation


def produce(result, package, seeds, output):
    output = Path(output).resolve()
    require(not output.exists(), 'Fresh policy output required')
    require(not output.is_relative_to(Path(package).resolve()), 'Policy output must not modify its input package')
    policy, derivation = compute(result, package, seeds)
    output.mkdir(parents=True)
    (output / 'policy.json').write_bytes(encode(policy))
    (output / 'derivation.json').write_bytes(encode(derivation))
    (output / 'receipt.json').write_bytes(encode(dict(mode='producer_API_policy_derivation_receipt_v1',
        producer_result=pin(result), package=str(Path(package).resolve()), seed_manifest=pin(seeds),
        implementation_sha256=sha(__file__), process_identity_implementation_sha256=sha(Path(__file__).with_name('producer_process_identity.py')),
        policy_sha256=sha(output / 'policy.json'), derivation_sha256=sha(output / 'derivation.json'))))
    return derivation


def verify(output):
    output = Path(output).resolve()
    receipt = load(output / 'receipt.json')
    require(receipt['mode']=='producer_API_policy_derivation_receipt_v1','Unsupported policy derivation receipt')
    require(receipt['implementation_sha256'] == sha(__file__), 'Policy builder changed')
    require(receipt['process_identity_implementation_sha256']==sha(Path(__file__).with_name('producer_process_identity.py')),'Process identity owner changed')
    require(all(sha(receipt[k]['path']) == receipt[k]['sha256'] for k in ('producer_result', 'seed_manifest')), 'Policy source bindings changed')
    policy, derivation = compute(receipt['producer_result']['path'], receipt['package'], receipt['seed_manifest']['path'])
    require(encode(policy) == (output / 'policy.json').read_bytes() and sha(output / 'policy.json') == receipt['policy_sha256'], 'Strict policy differs on re-derivation')
    require(encode(derivation) == (output / 'derivation.json').read_bytes() and sha(output / 'derivation.json') == receipt['derivation_sha256'], 'Policy derivation differs')
    return derivation


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--producer-result', type=Path)
    p.add_argument('--package', type=Path)
    p.add_argument('--seed-manifest', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--verify-output', type=Path)
    a = p.parse_args()
    if not a.verify_output and not all((a.producer_result, a.package, a.seed_manifest, a.output)):
        p.error('producer-result, package, seed-manifest and output are required')
    result = verify(a.verify_output) if a.verify_output else produce(a.producer_result, a.package, a.seed_manifest, a.output)
    print(json.dumps({k: result[k] for k in ('mode', 'observed_processes', 'input_files', 'input_directories', 'negative_probes', 'strict_producer_execution_required')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
