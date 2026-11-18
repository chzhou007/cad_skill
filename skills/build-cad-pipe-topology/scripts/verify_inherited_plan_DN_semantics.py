"""Fresh native replay of historical DN JSON without relying on dict order.

Keep the original producer, implementation hashes, source receipts and output
bytes intact. Compare the complete JSON value, including every array position,
number representation, field and lineage; object key order is serialization.
"""
import json
from pathlib import Path
from confirm_crossview_paths import load,sha
from rebuild_inherited_full_plan_DN import MODE,compute,implementation_hashes
from rebuild_full_plan_DN import checked


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':')).encode('utf8')


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'inherited-plan-DN-receipt.json')
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes():
        raise ValueError('inherited full-plan DN implementation changed')
    target=directory/'inherited-plan-DN-results.json'
    if sha(target)!=receipt['output_sha256']:raise ValueError('inherited full-plan DN recorded bytes changed')
    manifest=load(checked(receipt['manifest']))
    replay=compute(manifest);saved=load(target)
    if canonical(replay)!=canonical(saved):raise ValueError('complete inherited plan DN native JSON value replay differs')
    return json.loads(canonical(replay))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify-output',type=Path,required=True)
    args=parser.parse_args();print(verify_output(args.verify_output)['counts'])
