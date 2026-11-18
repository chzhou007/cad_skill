"""Portable producer for the mandatory native caption/body batch stage."""
import argparse
import csv
from pathlib import Path

from confirm_crossview_paths import load,sha,encode
from native_exploded_caption_identity import compute,migrate_components,implementation_hashes,MODE


def build(paths,policy_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    for key in ('source','graph','devices'):
        if key not in paths:raise ValueError('complete source/graph/component inputs required')
    policy=load(policy_path)
    for key,path in paths.items():
        item=policy.get('inputs',{}).get(key,{})
        if item.get('sha256')!=sha(path) or Path(item.get('path','')).resolve()!=Path(path).resolve():
            raise ValueError('fixed native identity input differs '+key)
    canonical=Path(paths['graph']).with_name('edge_device_instances.csv')
    if sha(canonical)!=sha(paths['devices']):raise ValueError('canonical native component inventory required')
    graph,proof=compute(paths,policy)
    with Path(paths['devices']).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    rows,changes=migrate_components(rows,proof['aliases'])
    output.mkdir(parents=True)
    (output/'graph_with_edges.json').write_bytes(encode(graph))
    with (output/'edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    (output/'component-identity-migration.json').write_bytes(encode(dict(records=changes,instance_count=len(rows),source_handles_and_edge_owners_preserved=True)))
    (output/'identity-receipt.json').write_bytes(encode(dict(mode=MODE,proof=proof,
        implementation_sha256=implementation_hashes(),inputs={**policy['inputs'],
            'policy':dict(path=str(Path(policy_path).resolve()),sha256=sha(policy_path))})))
    return proof


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','devices','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();paths={k:getattr(args,k) for k in ('source','graph','devices')}
    result=build(paths,args.policy,args.output)
    print(dict(checked=result['equipment_bodies_checked'],identity_changes=len(result['aliases']),unresolved=len(result['pending']),human_accepted=False))


if __name__=='__main__':main()
