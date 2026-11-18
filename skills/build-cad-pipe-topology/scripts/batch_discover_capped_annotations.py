"""Fixed-input, independently replayable annotation discovery for whole views."""
import argparse,importlib,json
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from discover_native_capped_annotations import discover

MODE='whole_view_native_capped_annotation_discovery_v1'

def checked(item):
    path=Path(item['path']).resolve()
    if sha(path)!=item['sha256']:raise ValueError('native discovery input changed: '+str(path))
    return path

def implementation_hashes():
    names=('discover_native_capped_annotations','native_capped_branch_annotations','native_line_path_evidence','source_readability')
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))

def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':')).encode('utf8')

def compute(manifest,announce=lambda s:None):
    rows=manifest['views'];ids=[r['id']for r in rows]
    if not rows or len(ids)!=len(set(ids))or any(not isinstance(i,str)or not i for i in ids):raise ValueError('unique complete source view IDs required')
    for item in rows:
        if set(item['inputs'])!={'source','graph'}:raise ValueError('annotation discovery owns only explicit source and current local graph')
        for spec in item['inputs'].values():checked(spec)
    views={}
    for item in rows:
        paths={k:checked(v)for k,v in item['inputs'].items()};doc,preflight=read_source(paths['source']);graph=load(paths['graph'])
        result=discover(doc,graph,sha(paths['source']),sha(paths['graph']));result['source_preflight']=preflight
        for spec in item['inputs'].values():checked(spec)
        views[item['id']]=result;announce(item['id']+': '+str(len(result['selections']))+' direct native annotations; '+str(len(result['pending']))+' unproved or unsupported captions')
    return dict(mode=MODE,views=views,inputs=rows,counts=dict(views=len(rows),captions=sum(len(r['captions'])for r in views.values()),
        native_direct_annotations=sum(len(r['selections'])for r in views.values()),pending_captions=sum(len(r['pending'])for r in views.values())),
        topology_changed=False,mappings_created=0,physical_values_assigned=0,human_accepted=False,hil_ready=False)

def verify_output(directory):
    directory=Path(directory);audit=load(directory/'native-capped-discovery-audit.json')
    if audit['mode']!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('batch annotation discovery implementation changed')
    manifest=load(checked(audit['manifest']));target=directory/'discovery.json'
    if sha(target)!=audit['output_sha256']:raise ValueError('batch annotation discovery recorded bytes changed')
    result=compute(manifest)
    if canonical(result)!=canonical(load(target)):raise ValueError('native whole-view annotation independent replay differs')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('manifest','output','verify_output'):p.add_argument('--'+key.replace('_','-'),type=Path)
    args=p.parse_args()
    if args.verify_output:
        if args.manifest or args.output:p.error('verification cannot override recorded inputs')
        print(verify_output(args.verify_output)['counts']);return
    if not args.manifest or not args.output:p.error('fixed manifest and new output required')
    if args.output.exists():raise FileExistsError(args.output)
    result=compute(load(args.manifest),lambda s:print(s,flush=True));args.output.mkdir(parents=True)
    target=args.output/'discovery.json';target.write_bytes(encode(result))
    audit=dict(mode=MODE,manifest=dict(path=str(args.manifest.resolve()),sha256=sha(args.manifest)),implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)
    (args.output/'native-capped-discovery-audit.json').write_bytes(encode(audit));print(result['counts'],flush=True)

if __name__=='__main__':main()
