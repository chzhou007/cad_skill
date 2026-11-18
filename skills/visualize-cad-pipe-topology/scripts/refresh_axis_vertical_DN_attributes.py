"""Append native vertical segment DN while retaining every existing axis/plan value.

The parent artifact's original independent qualification, exact input bytes and
existing effective attributes are retained. New family geometry is independently
reconstructed; parent artifact reuse is never reported as a new parent replay.
"""
import argparse,copy,hashlib,json,shutil,sys,zipfile
from pathlib import Path
import refresh_noncompound_main_attributes as base
from axis_vertical_DN_context import from_artifact,MODE as CONTEXT_MODE
MODE='qualified_viewer_axis_vertical_segment_DN_refresh_v1'
ALLOWED={'public/edge-attributes.js','public/full-batch-plan-attributes.js'}
FIELDS={'axis_vertical_DN_segment_count','axis_vertical_DN_segments_json','axis_vertical_DN_source_sha256'}

def sha(p):return base.sha(p)
def load(p):return base.load(p)
def encoded(v):return base.encoded(v)

def qualified_parent(parent,graph,devices,source,legend,comparison,qualification,qualification_sha):
    if sha(qualification)!=qualification_sha:raise ValueError('original independent parent qualification changed')
    saved=load(qualification);manifest,inputs=base.parent_check(parent,graph,devices,source,legend,comparison)
    if saved.get('formal_artifact_replay',{}).get('artifact_replay')!='passed' or saved['formal_artifact_replay']['bundle_id']!=manifest['bundleId'] or saved['result']!=load(Path(parent)/'compound-interface-refresh.json'):raise ValueError('parent is not its originally qualified interface artifact')
    if any(sha(p)!=h for p,h in saved['result']['original_input_hashes'].items()):raise ValueError('original parent native inputs changed')
    prior=manifest.get('attributeValueContext')
    if not prior or prior.get('source_graph_sha256')!=sha(graph)or prior.get('rendered_graph_sha256')!=sha(Path(parent)/'public/data/graph.json'):raise ValueError('parent source context differs')
    if hashlib.sha256(encoded(prior)).hexdigest()!=manifest['reviewContentHashes'].get('attribute_value_context')or hashlib.sha256(encoded(base.effective_attributes(parent))).hexdigest()!=saved['result']['effective_attribute_hash']:raise ValueError('qualified parent effective attributes changed')
    return manifest,inputs

def delta(prior,current,context):
    old={r['edge_id']:r['values']for r in prior};new={r['edge_id']:r['values']for r in current};target={r['edge_id']for r in context['records']}
    if set(old)!=set(new)or len(old)!=len(prior)or len(new)!=len(current):raise ValueError('axis edge inventory changed')
    changed=[]
    for eid,before in old.items():
        after=new[eid]
        if {k:v for k,v in after.items()if k not in FIELDS}!=before:raise ValueError('inherited effective attribute changed '+eid)
        rows=[r for r in context['records']if r['edge_id']==eid]
        if eid not in target:
            if before!=after:raise ValueError('unrelated effective attribute changed '+eid)
            continue
        if after.get('axis_vertical_DN_segment_count')!=len(rows)or json.loads(after.get('axis_vertical_DN_segments_json','[]'))!=rows or after.get('axis_vertical_DN_source_sha256')!=context['axis_source_sha256']:raise ValueError('actual vertical segment CSV differs '+eid)
        changed.append(eid)
    return dict(new_vertical_segment_annotations=len(context['records']),affected_axis_edges=sorted(changed),previous_axis_riser_domains=context['previous_axis_riser_domains'],new_axis_vertical_domains=context['new_axis_vertical_domains'],all_current_axis_vertical_domains=context['all_current_axis_vertical_domains'],old_effective_attributes_exact=True,new_whole_edge_DN=0,new_physical_lengths=0)

def refresh(parent,output,templates,graph,devices,source,legend,comparison,proof,qualification,qualification_sha,port=10354):
    parent,output,templates=map(lambda p:Path(p).resolve(),(parent,output,templates));archive=output.with_suffix('.zip')
    if output.exists() or archive.exists() or parent==output or parent in output.parents:raise ValueError('fresh external viewer output required')
    manifest,inputs=qualified_parent(parent,graph,devices,source,legend,comparison,qualification,qualification_sha);before=base.artifact_inventory(parent)
    context=copy.deepcopy(manifest['attributeValueContext'])
    if 'axis_vertical_segment_DN' in context:raise ValueError('member interfaces already composed')
    context['axis_vertical_segment_DN']=from_artifact(graph,parent/'public/data/graph.json',proof,context)
    paths=[Path(p) for p in (graph,devices,source,legend,comparison,proof,qualification)];input_hashes={str(p.resolve()):sha(p) for p in paths}
    changes={name:sha(templates/name) for name in ALLOWED if manifest['templateHashes'].get(name)!=sha(templates/name)}
    if not changes:raise ValueError('no new interface attribute templates')
    prior=base.effective_attributes(parent);shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in changes:shutil.copy2(templates/name,output/name)
    provisional=copy.deepcopy(manifest);provisional['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encoded(provisional))
    current=base.effective_attributes(output);change=delta(prior,current,context['axis_vertical_segment_DN']);effective_hash=hashlib.sha256(encoded(current)).hexdigest()
    revised=base.revised_manifest(manifest,changes,effective_hash,sha(__file__),port,context);revised['attributeTemplateRefresh']['mode']=MODE
    revised['sourceHashes']['axis_vertical_DN_proof']=sha(proof)
    (output/'public/data/manifest.json').write_bytes(encoded(revised));p=output/'public/index.html';p.write_text(p.read_text(encoding='utf8').replace(manifest['bundleId'],revised['bundleId']),encoding='utf8')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    doc,readable=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encoded(schema));quality=check(output,source)
    if schema['status']!='passed' or quality['machine_status']!='PASS':raise ValueError('new viewer native/schema check failed')
    for name,digest in before.items():
        if name.startswith(('public/data/','annotations/')) and name!='public/data/manifest.json' and sha(output/name)!=digest:raise ValueError('original source payload or annotation changed '+name)
    if base.artifact_inventory(parent)!=before or any(sha(p)!=h for p,h in input_hashes.items()):raise ValueError('parent or native inputs changed during composition')
    evidence=output/'axis-vertical-DN-refresh';evidence.mkdir();(evidence/'parent-effective.json').write_bytes(encoded(prior));(evidence/'current-effective.json').write_bytes(encoded(current))
    shutil.copy2(proof,evidence/'native-vertical-DN.json')
    audit=dict(mode=MODE,status='native_schema_source_fidelity_and_effective_delta_passed_actual_browser_pending',parent=str(parent),template_root=str(templates),
        source_paths={k:str(Path(v).resolve()) for k,v in dict(graph=graph,devices=devices,source=source,legend=legend,comparison=comparison,proof=proof,qualification=qualification).items()},
        qualification_sha256=qualification_sha,original_input_hashes=input_hashes,parent_file_hashes=before,parent_bundle_id=manifest['bundleId'],bundle_id=revised['bundleId'],changes=changes,
        effective_attribute_hash=effective_hash,delta=change,vertical_DN_counts={k:context['axis_vertical_segment_DN'][k]for k in('segments','affected_axis_edges','previous_axis_riser_domains','new_axis_vertical_domains','all_current_axis_vertical_domains')},
        source_preflight=readable,native_schema_status=schema['status'],native_drawing_status=quality['machine_status'],
        parent_original_qualified_artifact_reused=True,parent_native_replay_performed=False,new_vertical_native_attribution_checked=True,
        canonical_axis_graph_mutated=False,rendered_axis_graph_mutated=False,component_assignments_mutated=False,old_annotations_preserved=True,human_confirmation_inherited=False,human_accepted=False)
    audit['output_hashes']={k:v for k,v in base.artifact_inventory(output).items() if k!='axis-vertical-DN-refresh.json'}
    (output/'axis-vertical-DN-refresh.json').write_bytes(encoded(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for name in sorted(base.inventory(output)):z.write(output/name,output.name+'/'+name)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('new member viewer ZIP failed')
    return audit

def verify(output):
    output=Path(output);audit=load(output/'axis-vertical-DN-refresh.json');manifest=load(output/'public/data/manifest.json');parent=Path(audit['parent']);p=audit['source_paths']
    if audit['mode']!=MODE or audit['bundle_id']!=manifest['bundleId'] or base.artifact_inventory(parent)!=audit['parent_file_hashes']:raise ValueError('viewer parent/identity changed')
    qualified_parent(parent,p['graph'],p['devices'],p['source'],p['legend'],p['comparison'],p['qualification'],audit['qualification_sha256'])
    for path,digest in audit['original_input_hashes'].items():
        if sha(path)!=digest:raise ValueError('viewer native input changed')
    if {k:v for k,v in base.artifact_inventory(output).items() if k!='axis-vertical-DN-refresh.json'}!=audit['output_hashes']:raise ValueError('viewer output bytes changed')
    prior=load(parent/'public/data/manifest.json')['attributeValueContext'];expected=copy.deepcopy(prior);expected['axis_vertical_segment_DN']=from_artifact(p['graph'],output/'public/data/graph.json',p['proof'],prior)
    if manifest['attributeValueContext']!=expected:raise ValueError('actual member interface context differs from independent native replay')
    actual=base.effective_attributes(output)
    if hashlib.sha256(encoded(actual)).hexdigest()!=audit['effective_attribute_hash'] or delta(base.effective_attributes(parent),actual,expected['axis_vertical_segment_DN'])!=audit['delta']:raise ValueError('actual member effective values differ')
    return dict(status='pending',artifact_replay='passed',bundle_id=manifest['bundleId'],parent_qualified_artifact_reused=True,new_vertical_native_attribution_checked=True,canonical_axis_graph_mutated=False,human_accepted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--verify',type=Path)
    for name in ('parent','output','templates','graph','devices','source','legend','comparison','proof','qualification'):p.add_argument('--'+name,type=Path)
    p.add_argument('--qualification-sha256');p.add_argument('--port',type=int,default=10354);a=p.parse_args()
    if a.verify:result=verify(a.verify)
    else:
        names=('parent','output','templates','graph','devices','source','legend','comparison','proof','qualification')
        if any(getattr(a,n) is None for n in names) or not a.qualification_sha256:p.error('all pinned native/parent/template inputs required')
        result=refresh(**{n:getattr(a,n) for n in names},qualification_sha=a.qualification_sha256,port=a.port)
    print(json.dumps(dict(status=result['status'],bundle_id=result['bundle_id']),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
