"""Versioned full-plan DN entry; preserve original local owners and DN kernels."""
import argparse, copy, importlib, json, types
from pathlib import Path
from confirm_crossview_paths import load, sha, encode
from rebuild_full_plan_DN import compute as original_compute, checked
from rebuild_inherited_full_plan_DN import configuration, implementation_hashes as previous_hashes
from current_circle_plan_DN import collect

MODE = 'complete_local_plan_native_DN_current_circle_main_lineage_v3'


def compute(manifest, announce=lambda x: None):
    configs = {item['inputs']['graph']['sha256']: configuration(item) for item in manifest['plans']}
    parents = {}
    for item in manifest['plans']:
        items = item.get('circle_main_lineage_parents', [])
        if len({p['sha256'] for p in items}) != len(items):
            raise ValueError('duplicate current circle lineage parent')
        for parent in items:
            checked(parent)
        parents[item['inputs']['graph']['sha256']] = items
    namespace = dict(original_compute.__globals__)
    namespace['collect'] = lambda d, g, sh, gh, seeds, log, circle: collect(d, g, sh, gh, seeds, log, circle, configs[gh], parents[gh])
    reader = types.FunctionType(original_compute.__code__, namespace, original_compute.__name__)
    result = reader(manifest, announce)
    result['previous_mode'] = result['mode']
    result['mode'] = MODE
    result['inherited_annotation_origins'] = {str(i['floor']): copy.deepcopy(i.get('inherited_annotation_inputs', {})) for i in manifest['plans']}
    result['historical_native_implementations_or_globals_changed'] = False
    for item in manifest['plans']:
        configuration(item)
        for parent in item.get('circle_main_lineage_parents', []):
            checked(parent)
    return result


def implementation_hashes():
    result = previous_hashes()
    from current_circle_main_lineage import implementation_hashes as lineage_hashes
    result.update({'circle_lineage:' + name: digest for name, digest in lineage_hashes().items()})
    for name in ('current_circle_main_lineage', 'current_circle_plan_DN'):
        result[name] = sha(importlib.import_module(name).__file__)
    result['current_circle_entry'] = sha(__file__)
    return result


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':'))


def verify_output(directory):
    directory = Path(directory)
    receipt = load(directory / 'current-circle-plan-DN-receipt.json')
    if receipt['mode'] != MODE or receipt['implementation_sha256'] != implementation_hashes():
        raise ValueError('current-circle full-plan DN implementation changed')
    target = directory / 'current-circle-plan-DN-results.json'
    if sha(target) != receipt['output_sha256']:
        raise ValueError('current-circle full-plan DN saved result changed')
    result = compute(load(checked(receipt['manifest'])))
    if canonical(result) != canonical(load(target)):
        raise ValueError('current-circle full-plan DN native independent replay differs')
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--verify-output', type=Path)
    args = p.parse_args()
    if args.verify_output:
        if args.manifest or args.output:
            p.error('verification cannot replace inputs')
        print(verify_output(args.verify_output)['counts'])
        return
    if not args.manifest or not args.output:
        p.error('fixed manifest and new output required')
    if args.output.exists():
        raise FileExistsError(args.output)
    result = compute(load(args.manifest), lambda s: print(s, flush=True))
    args.output.mkdir(parents=True)
    target = args.output / 'current-circle-plan-DN-results.json'
    target.write_bytes(encode(result))
    (args.output / 'current-circle-plan-DN-receipt.json').write_bytes(encode(dict(mode=MODE,
        manifest=dict(path=str(args.manifest.resolve()), sha256=sha(args.manifest)),
        implementation_sha256=implementation_hashes(), output_sha256=sha(target), human_accepted=False)))
    print(result['counts'], flush=True)


if __name__ == '__main__':
    main()
