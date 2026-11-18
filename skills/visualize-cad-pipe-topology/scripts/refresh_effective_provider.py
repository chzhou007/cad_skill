"""Publish complete member DN in primary CSV fields and rebuild the live frontier."""
import argparse,copy,hashlib,shutil,sys,zipfile
from pathlib import Path
for n in ['build-cad-pipe-topology','orchestrate-cad-drawing-pipeline']:sys.path.insert(0,str(Path(__file__).resolve().parents[2]/n/'scripts'))
from confirm_crossview_paths import load,sha,encode
from refresh_uniform_subroute_DN import verify as verify_parent
from riser_header_interval_application import verify_output as verify_intervals
from refresh_reviewed_ring_partition_DN import effective
from current_effective_provider import reconcile
import refresh_attribute_templates as base
MODE='actual_effective_member_DN_and_provider_refresh_v1';AUDIT='effective-provider-refresh.json';FOLDER='effective-provider-refresh';MODULE='public/edge-attributes-effective-provider.js';SCALARS={'diameter_nominal_mm','diameter_text','diameter_status'}

def delta(before,after,proof):
    targets={r['axis_edge_id']:r for r in proof['member_records']if r['member_kind']=='approach'and isinstance(r['nominal_mm'],(int,float))and r['nominal_mm']>0 and r['complete_horizontal_centerline_mm']is not None};old={r['edge_id']:r['values']for r in before};new={r['edge_id']:r['values']for r in after};filled=[]
    if old.keys()!=new.keys():raise ValueError('effective edge population changed')
    for eid,v in old.items():
        w=new[eid]
        if eid not in targets:
            if w!=v:raise ValueError('unrelated or partial member values changed '+eid)
            continue
        if {k:x for k,x in v.items()if k not in SCALARS}!={k:x for k,x in w.items()if k not in SCALARS}:raise ValueError('old lengths or source metadata changed '+eid)
        nominal=targets[eid]['nominal_mm']
        if v.get('diameter_nominal_mm')not in (None,'',nominal)or w.get('diameter_nominal_mm')!=nominal:raise ValueError('complete member primary DN conflicts')
        if v.get('diameter_nominal_mm')in(None,''):filled.append(eid)
    return dict(primary_complete_member_DN_fills=sorted(filled),new_lengths=0,new_vertical_values=0,new_columns=0,all_old_length_and_partial_member_fields_exact=True)

def refresh(parent,output,intervals,templates,port):
    parent,output,intervals,templates=[Path(p).resolve()for p in [parent,output,intervals,templates]]
    if output.exists()or output.with_suffix('.zip').exists():raise FileExistsError(output)
    verify_parent(parent);proof=verify_intervals(intervals);m=load(parent/'public/data/manifest.json');context=m['attributeValueContext']
    if context['riser_header_application']['source_proof_sha256']!=sha(intervals/'riser-header-intervals.json'):raise ValueError('complete native interval source differs from viewer')
    before=base.artifact_inventory(parent);old=effective(parent);shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.copy2(templates/MODULE,output/MODULE)
    app=output/'public/app.js';s=app.read_text(encoding='utf8');assert s.count("from './edge-attributes-uniform-subroute.js'")==1;app.write_text(s.replace("from './edge-attributes-uniform-subroute.js'","from './edge-attributes-effective-provider.js'"),encoding='utf8')
    current=effective(output);change=delta(old,current,proof);provider=reconcile(load(parent/'uniform-subroute-DN-refresh/provider-inventory.json'),current,context);folder=output/FOLDER;folder.mkdir();(folder/'current-effective.json').write_bytes(encode(current));(folder/'provider-inventory.json').write_bytes(encode(provider))
    revised=copy.deepcopy(m);revised['preferredPort']=port;revised['sourceHashes']['complete_member_primary_DN']=sha(intervals/'riser-header-intervals.json');revised['templateHashes'].update({n:sha(output/n)for n in [MODULE,'public/app.js']});revised['reviewContentHashes']['effective_edge_attributes']=hashlib.sha256(encode(current)).hexdigest();revised['effectiveProviderRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],implementation_sha256=sha(__file__),provider_implementation_sha256=sha(Path(__file__).with_name('current_effective_provider.py')),human_confirmation_inherited=False);revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],templates={n:sha(output/n)for n in [MODULE,'public/app.js']},port=port,provider=sha(folder/'provider-inventory.json')))).hexdigest()[:20];(output/'public/data/manifest.json').write_bytes(encode(revised));p=output/'public/index.html';p.write_text(p.read_text(encoding='utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('native drawing gate failed')
    if base.artifact_inventory(parent)!=before:raise ValueError('parent mutated')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('old graph/data/annotations changed')
    a=dict(mode=MODE,parent=str(parent),parent_files=before,intervals=str(intervals),interval_proof_sha256=sha(intervals/'riser-header-intervals.json'),bundle_id=revised['bundleId'],delta=change,source_preflight=preflight,human_accepted=False,output_hashes=base.artifact_inventory(output));(output/AUDIT).write_bytes(encode(a))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    return a

def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);intervals=Path(a['intervals']);verify_parent(parent);proof=verify_intervals(intervals);m=load(output/'public/data/manifest.json');oldm=load(parent/'public/data/manifest.json');v=effective(output)
    if a['mode']!=MODE or m['effectiveProviderRefresh']['implementation_sha256']!=sha(__file__)or m['effectiveProviderRefresh']['provider_implementation_sha256']!=sha(Path(__file__).with_name('current_effective_provider.py'))or sha(intervals/'riser-header-intervals.json')!=a['interval_proof_sha256']or m['attributeValueContext']!=oldm['attributeValueContext']or base.artifact_inventory(parent)!=a['parent_files']or {n:h for n,h in base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']or delta(effective(parent),v,proof)!=a['delta']or reconcile(load(parent/'uniform-subroute-DN-refresh/provider-inventory.json'),v,m['attributeValueContext'])!=load(output/FOLDER/'provider-inventory.json'):raise ValueError('current effective provider replay differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=a['delta'],counts=load(output/FOLDER/'provider-inventory.json')['counts'],human_accepted=False)

def main():
    p=argparse.ArgumentParser()
    for n in ['parent','output','intervals','templates','verify-output']:p.add_argument('--'+n,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify(a.verify_output)if a.verify_output else refresh(a.parent,a.output,a.intervals,a.templates,a.port)
    print({k:v for k,v in r.items()if k in ['mode','status','artifact_replay','bundle_id','delta']},flush=True)
if __name__=='__main__':main()
