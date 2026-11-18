"""Manifest-driven full-axis application of inherited CAD correspondence rules."""
import argparse
import csv
from pathlib import Path

from confirm_crossview_paths import load, sha, encode
from fresh_reviewed_plan_inventory import verify_output as verify_inventory
from native_exploded_caption_identity import verify_output as verify_identity,migrate_components
from reviewed_main_DN_boundaries import verify_output as verify_DN
from batch_apply_crossview_rules import MODE,rebase_axis_inventory,discover_floor,evaluate_all_axis_edges
from batch_rule_contract import check
from source_readability import read_source
from batch_native_path_coverage import collect as coverage
from native_plan_projection_lengths import unit_evidence,lengths


def checked(spec):
    if not isinstance(spec,dict) or set(spec)!={'path','sha256'} or sha(spec['path'])!=spec['sha256']:
        raise ValueError('batch dependency changed or lacks an exact file pin')
    return Path(spec['path'])


def compute(manifest,announce=lambda message:None):
    items=manifest['inputs'];paths={k:checked(v) for k,v in items.items()}
    metric_paths={f:checked(v) for f,v in manifest['metric_policies'].items()}
    if paths['inventory_receipt'].name!='inventory-receipt.json' or paths['identity_receipt'].name!='identity-receipt.json':
        raise ValueError('canonical independent stage receipts required')
    identity_dir=paths['identity_receipt'].parent
    announce('Replaying native body identity and preserved pipe/component ownership')
    identity=verify_identity(identity_dir)['proof']
    axis=load(identity_dir/'graph_with_edges.json')
    origin=load(paths['identity_receipt'])['inputs']['graph']['path'];old_axis=load(origin)
    with Path(origin).with_name('edge_device_instances.csv').open(encoding='utf-8-sig',newline='') as stream:
        old_components=list(csv.DictReader(stream))
    expected,component_aliases=migrate_components(old_components,identity['aliases'])
    with (identity_dir/'edge_device_instances.csv').open(encoding='utf-8-sig',newline='') as stream:
        if list(csv.DictReader(stream))!=expected:raise ValueError('identity stage lost or reassigned native components')
    announce('Replaying all floor/equipment/service native inventories before batch matching')
    batch=verify_inventory(paths['inventory_receipt'].parent)
    if set(batch['floors'])!=set(metric_paths):raise ValueError('all current inventory floors require metric policies')
    floors={};inventories={};native={};metrics={}
    for f,inventory in batch['floors'].items():
        inventory=rebase_axis_inventory(inventory,old_axis,axis,identity);inventories[f]=inventory
        local=batch['local_inputs'][f]
        graphs=dict(plan=load(local['plan_graph']['path']),iso=axis)
        floors[f]=discover_floor(graphs,inventory,int(f));native[f]={};docs={}
        announce(f'{f}F whole-floor rule application: {len(floors[f]["records"])} path candidates')
        for view in ('plan','iso'):
            doc,_=read_source(local[view+'_source']['path']);docs[view]=doc
            ids=sorted({eid for row in floors[f]['records'] for eid in row[view+'_edges']})
            sh=local[view+'_source']['sha256'];gh=local['plan_graph']['sha256'] if view=='plan' else sha(identity_dir/'graph_with_edges.json')
            native[f][view]=coverage(doc,graphs[view],ids,sh,gh)
        units=unit_evidence(docs['plan'],load(metric_paths[f]));metrics[f]=[]
        for row in floors[f]['records']:
            value=dict(mapping_id=row['mapping_id'],plan_edges=row['plan_edges'],iso_edges=row['iso_edges'])
            try:value['projection']=lengths(graphs['plan'],native[f]['plan'],row,units)
            except ValueError as exc:value.update(projection=None,reason=str(exc))
            metrics[f].append(value)
    DN=verify_DN(paths['DN_receipt'].parent);matched={r['plan_edges'][0]:r for r in floors[str(manifest['reviewed_DN_floor'])]['records']}
    resolutions=[]
    for row in DN['records']:
        if row['edge_id'] not in matched:raise ValueError('reviewed DN scope has no current batch mapping')
        current=matched[row['edge_id']]
        resolutions.append(dict(plan_edge=row['edge_id'],iso_edges=current['iso_edges'],nominal_mm=row['nominal_mm'],
            current_mapping=current['mapping_id'],DN_source=row))
    outcomes=evaluate_all_axis_edges(axis,floors,load(paths['prior_attributes']))
    summary=check(outcomes,axis)
    for key,spec in items.items():checked(spec)
    for spec in manifest['metric_policies'].values():checked(spec)
    return dict(mode=MODE,floors=floors,inventories=inventories,native=native,metrics=metrics,
        all_axis_edges=outcomes,summary=summary,reviewed_DN_mappings=resolutions,component_identity_aliases=component_aliases,
        identity_graph_sha256=sha(identity_dir/'graph_with_edges.json'),
        attributes_fused=False,human_accepted=False,hil_ready=False)


def implementation_hashes():
    import batch_apply_crossview_rules,native_exploded_caption_identity,fresh_reviewed_plan_inventory
    return dict(entry=sha(__file__),batch=sha(batch_apply_crossview_rules.__file__),
        identity=sha(native_exploded_caption_identity.__file__),inventory=sha(fresh_reviewed_plan_inventory.__file__))


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'batch-rule-receipt.json')
    if receipt['implementation_sha256']!=implementation_hashes():raise ValueError('batch implementation changed')
    manifest=checked(receipt['manifest']);result=compute(load(manifest))
    if encode(result)!=(directory/'batch-rule-results.json').read_bytes():raise ValueError('full batch independent native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=Path);parser.add_argument('--output',type=Path);parser.add_argument('--verify-output',type=Path)
    args=parser.parse_args()
    if args.verify_output:
        if args.manifest or args.output:parser.error('verification cannot override fixed inputs')
        result=verify_output(args.verify_output);print(result['summary'],flush=True);return
    if not args.manifest or not args.output:parser.error('fixed manifest and fresh output required')
    if args.output.exists():raise FileExistsError(args.output)
    result=compute(load(args.manifest),lambda message:print(message,flush=True));args.output.mkdir(parents=True)
    (args.output/'batch-rule-results.json').write_bytes(encode(result))
    (args.output/'batch-rule-receipt.json').write_bytes(encode(dict(mode=MODE,
        manifest=dict(path=str(args.manifest.resolve()),sha256=sha(args.manifest)),implementation_sha256=implementation_hashes(),
        result_sha256=sha(args.output/'batch-rule-results.json'),human_accepted=False)))
    print(result['summary'],flush=True)


if __name__=='__main__':main()
