"""Versioned source-qualified mapping/attribute extension of an unchanged viewer."""
import argparse,copy,hashlib,json,shutil,sys,zipfile
from pathlib import Path
import refresh_attribute_templates as base
from bounded_main_complete_extent_context import from_artifact
MODE='qualified_native_bounded_main_complete_extent_refresh_v1'
ALLOWED={'public/anchor-bounded-main-attributes.js','public/edge-attributes.js'}
sha,load,encoded=base.sha,base.load,base.encoded

def qualified_parent(parent,graph,devices,source,legend,comparison,qualification,qualification_sha):
    if sha(qualification)!=qualification_sha:raise ValueError('qualified parent report changed')
    saved=load(qualification);manifest,inputs=base.parent_check(parent,graph,devices,source,legend,comparison);audit=load(Path(parent)/'qualified-plan-scope-refresh.json')
    if saved['formal_artifact_replay'].get('artifact_replay')!='passed' or saved['formal_artifact_replay']['bundle_id']!=manifest['bundleId'] or saved['result']!=audit:raise ValueError('specific-provider parent artifact not qualified')
    if any(sha(p)!=h for p,h in audit['original_input_hashes'].items()):raise ValueError('parent source dependency changed')
    context=manifest['attributeValueContext']
    if context['source_graph_sha256']!=sha(graph) or context['rendered_graph_sha256']!=sha(Path(parent)/'public/data/graph.json') or hashlib.sha256(encoded(context)).hexdigest()!=manifest['reviewContentHashes']['attribute_value_context']:raise ValueError('parent attribute identity changed')
    if hashlib.sha256(encoded(base.effective_attributes(parent))).hexdigest()!=audit['effective_attribute_hash']:raise ValueError('parent effective CSV changed')
    return manifest,inputs


def delta(prior,current,context):
    old={r['edge_id']:r['values']for r in prior};new={r['edge_id']:r['values']for r in current};complete={r['axis_edge_id']:r for r in context['records']};blocked={r['axis_edge_id']:r for r in context.get('quarantined_records',[])};targets={**complete,**blocked}
    if old.keys()!=new.keys() or len(targets)!=len(complete)+len(blocked):raise ValueError('bounded extent inventory changed')
    allowed={'batch_complete_horizontal_centerline_mm','bounded_main_complete_centerline_mm','bounded_main_complete_extent_evidence_json','bounded_main_complete_extent_proof_sha256'}
    guard_fields={'diameter_nominal_mm','diameter_text','diameter_status','crossview_plan_drawn_nominal_mm','crossview_plan_horizontal_projection_mm','crossview_projection_allocation','crossview_metric_status','bounded_main_plan_DN_mm','bounded_main_carrier_guard_status','bounded_main_prior_scalar_DN_mm','bounded_main_carrier_guard_evidence_json','bounded_main_complete_extent_proof_sha256'}
    for eid,before in old.items():
        after=new[eid]
        if eid not in targets:
            if before!=after:raise ValueError('unrelated effective attributes changed '+eid)
            continue
        r=targets[eid]
        if eid in blocked:
            if before.get('diameter_nominal_mm')!=r['nominal_mm'] or after.get('diameter_nominal_mm')!='' or after.get('bounded_main_prior_scalar_DN_mm')!=r['nominal_mm'] or after.get('diameter_status')!='compound_carrier_member_identity_pending':raise ValueError('carrier scalar was not superseded with retained source observation')
            if json.loads(after.get('bounded_main_carrier_guard_evidence_json','{}'))!=r:raise ValueError('carrier guard source evidence absent')
            fields=guard_fields
        else:
            value=r['complete_horizontal_centerline_route_mm']
            if before.get('diameter_nominal_mm')!=r['nominal_mm'] or after.get('diameter_nominal_mm')!=r['nominal_mm']:raise ValueError('existing noncompound DN changed')
            if before.get('batch_complete_horizontal_centerline_mm')not in(None,'') or after.get('batch_complete_horizontal_centerline_mm')!=value or after.get('bounded_main_complete_centerline_mm')!=value:raise ValueError('new complete centreline absent or previously known')
            if json.loads(after.get('bounded_main_complete_extent_evidence_json','{}'))!=r:raise ValueError('effective export lacks complete extent proof')
            fields=allowed
        if any(before.get(k)!=after.get(k)and k not in fields for k in before.keys()|after.keys()):raise ValueError('undeclared target attribute changed')
        if after.get('bounded_main_complete_extent_proof_sha256')!=context['source_bindings']['native_proof']:raise ValueError('effective proof binding absent')
    return dict(new_complete_horizontal_centerlines=len(complete),quarantined_prior_scalar_DN=len(blocked),new_known_DN=0,all_non_target_effective_values_exact=True,all_source_observations_preserved=True,new_installed_lengths=0,new_net_cut_lengths=0)


def refresh(parent,output,templates,graph,devices,source,legend,comparison,proof,qualification,qualification_sha,port=10358):
    parent,output,templates=map(lambda p:Path(p).resolve(),(parent,output,templates));archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh external viewer required')
    manifest,inputs=qualified_parent(parent,graph,devices,source,legend,comparison,qualification,qualification_sha);before=base.artifact_inventory(parent);context=copy.deepcopy(manifest['attributeValueContext'])
    if 'complete_main_extents'in context['anchor_bounded_mains']:raise ValueError('new owner mapping already composed')
    context['anchor_bounded_mains']['complete_main_extents']=from_artifact(graph,parent/'public/data/graph.json',proof,context)
    paths=[Path(p)for p in(graph,devices,source,legend,comparison,proof,qualification)];input_hashes={str(p.resolve()):sha(p)for p in paths};changes={n:sha(templates/n)for n in ALLOWED if sha(templates/n)!=manifest['templateHashes'].get(n)}
    if changes.keys()!=ALLOWED:raise ValueError('the declared specific-provider reader must be packaged')
    prior=base.effective_attributes(parent);shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in changes:shutil.copy2(templates/n,output/n)
    provisional=copy.deepcopy(manifest);provisional['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encoded(provisional))
    current=base.effective_attributes(output);change=delta(prior,current,context['anchor_bounded_mains']['complete_main_extents']);effective_hash=hashlib.sha256(encoded(current)).hexdigest()
    revised=copy.deepcopy(manifest);revised['templateHashes'].update(changes);revised['preferredPort']=port;revised['attributeValueContext']=context;revised['reviewContentHashes']['effective_edge_attributes']=effective_hash;revised['reviewContentHashes']['attribute_value_context']=hashlib.sha256(encoded(context)).hexdigest();revised['sourceHashes']['bounded_main_extent_proof']=sha(proof)
    revised['attributeTemplateRefresh']=dict(mode=MODE,parent_bundle_id=manifest['bundleId'],changed_templates=changes,implementation_sha256=sha(__file__),source_reconstruction_performed=False,human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encoded(dict(parent=manifest['bundleId'],templates=changes,effective=effective_hash,implementation=sha(__file__),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encoded(revised));p=output/'public/index.html';p.write_text(p.read_text(encoding='utf8').replace(manifest['bundleId'],revised['bundleId']),encoding='utf8')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    doc,readable=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encoded(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('new mapped viewer schema/native rendering failed')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('source payload or historical annotations changed')
    if base.artifact_inventory(parent)!=before or any(sha(p)!=h for p,h in input_hashes.items()):raise ValueError('input or parent changed during composition')
    evidence=output/'bounded-main-extent-refresh';evidence.mkdir();(evidence/'parent-effective.json').write_bytes(encoded(prior));(evidence/'current-effective.json').write_bytes(encoded(current));shutil.copy2(proof,evidence/'native-bounded-main-extents.json')
    audit=dict(mode=MODE,status='native_schema_fidelity_and_new_member_effective_delta_passed_actual_browser_pending',parent=str(parent),template_root=str(templates),source_paths={k:str(Path(v).resolve())for k,v in dict(graph=graph,devices=devices,source=source,legend=legend,comparison=comparison,proof=proof,qualification=qualification).items()},qualification_sha256=qualification_sha,original_input_hashes=input_hashes,parent_file_hashes=before,parent_bundle_id=manifest['bundleId'],bundle_id=revised['bundleId'],changes=changes,effective_attribute_hash=effective_hash,delta=change,source_preflight=readable,native_schema_status=schema['status'],native_drawing_status=quality['machine_status'],parent_original_qualified_artifact_reused=True,parent_native_replay_performed=False,new_crossview_native_reconstruction=True,canonical_axis_graph_mutated=False,rendered_axis_graph_mutated=False,component_assignments_mutated=False,old_annotations_preserved=True,human_confirmation_inherited=False,human_accepted=False)
    audit['output_hashes']={k:v for k,v in base.artifact_inventory(output).items()if k!='bounded-main-extent-refresh.json'};(output/'bounded-main-extent-refresh.json').write_bytes(encoded(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('new viewer ZIP failed')
    return audit

def verify(output):
    output=Path(output);a=load(output/'bounded-main-extent-refresh.json');m=load(output/'public/data/manifest.json');parent=Path(a['parent']);p=a['source_paths']
    if a['mode']!=MODE or a['bundle_id']!=m['bundleId']or m['attributeTemplateRefresh']['implementation_sha256']!=sha(__file__)or base.artifact_inventory(parent)!=a['parent_file_hashes']:raise ValueError('new mapped viewer identity changed')
    qualified_parent(parent,p['graph'],p['devices'],p['source'],p['legend'],p['comparison'],p['qualification'],a['qualification_sha256'])
    if any(sha(p)!=h for p,h in a['original_input_hashes'].items()):raise ValueError('mapped viewer native input changed')
    if {k:v for k,v in base.artifact_inventory(output).items()if k!='bounded-main-extent-refresh.json'}!=a['output_hashes']:raise ValueError('mapped viewer bytes changed')
    prior=load(parent/'public/data/manifest.json')['attributeValueContext'];expected=copy.deepcopy(prior);expected['anchor_bounded_mains']['complete_main_extents']=from_artifact(p['graph'],output/'public/data/graph.json',p['proof'],prior)
    if m['attributeValueContext']!=expected:raise ValueError('new mapping context differs from independent native replay')
    actual=base.effective_attributes(output)
    if hashlib.sha256(encoded(actual)).hexdigest()!=a['effective_attribute_hash']or delta(base.effective_attributes(parent),actual,expected['anchor_bounded_mains']['complete_main_extents'])!=a['delta']:raise ValueError('new mapped effective attributes differ')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],new_crossview_native_reconstruction=True,human_accepted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--verify',type=Path)
    for n in('parent','output','templates','graph','devices','source','legend','comparison','proof','qualification'):p.add_argument('--'+n,type=Path)
    p.add_argument('--qualification-sha256');p.add_argument('--port',type=int,default=10358);a=p.parse_args()
    if a.verify:r=verify(a.verify)
    else:
        keys=('parent','output','templates','graph','devices','source','legend','comparison','proof','qualification')
        if any(getattr(a,n)is None for n in keys)or not a.qualification_sha256:p.error('all pinned native inputs required')
        r=refresh(**{n:getattr(a,n)for n in keys},qualification_sha=a.qualification_sha256,port=a.port)
    print(json.dumps(dict(status=r['status'],bundle_id=r['bundle_id']),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
