"""Compose native member bridges onto the qualified vertical-aware viewer.

The prior artifact qualification is checked against current source/template and
effective-value bytes. Only new bridge geometry is independently replayed here;
that is not a claim of fresh reconstruction of every parent feature.
"""
import argparse,copy,hashlib,json,shutil,zipfile
from pathlib import Path
import refresh_noncompound_main_attributes as base
from compound_bridge_context import from_artifact
MODE='qualified_viewer_compound_member_bridge_refresh_v1'
ALLOWED={'public/edge-attributes.js','public/full-batch-plan-attributes.js'}
FIELDS={'member_bridge_mapping_id','member_bridge_plan_edge','member_bridge_DN_mm','member_bridge_plan_pipe_projection_mm','member_bridge_component_pairs_json','member_bridge_evidence_json'}
CHANGED=FIELDS|{'diameter_nominal_mm','diameter_text','diameter_status','physical_edge_length_status'}
sha,load,encoded=base.sha,base.load,base.encoded

def qualified_parent(parent,graph,devices,source,legend,comparison,qualification,qualification_sha):
    if sha(qualification)!=qualification_sha:raise ValueError('parent qualification changed')
    saved=load(qualification);manifest,inputs=base.parent_check(parent,graph,devices,source,legend,comparison)
    if saved.get('formal_artifact_replay',{}).get('artifact_replay')!='passed' or saved['formal_artifact_replay']['bundle_id']!=manifest['bundleId'] or saved['result']!=load(Path(parent)/'axis-vertical-DN-refresh.json'):raise ValueError('parent is not its qualified vertical-aware artifact')
    if any(sha(p)!=h for p,h in saved['result']['original_input_hashes'].items()):raise ValueError('parent original native inputs changed')
    context=manifest.get('attributeValueContext',{})
    if context.get('source_graph_sha256')!=sha(graph)or context.get('rendered_graph_sha256')!=sha(Path(parent)/'public/data/graph.json'):raise ValueError('parent graph binding changed')
    if hashlib.sha256(encoded(context)).hexdigest()!=manifest['reviewContentHashes'].get('attribute_value_context')or hashlib.sha256(encoded(base.effective_attributes(parent))).hexdigest()!=saved['result']['effective_attribute_hash']:raise ValueError('parent effective attributes changed')
    return manifest,inputs

def delta(prior,current,context):
    old={r['edge_id']:r['values']for r in prior};new={r['edge_id']:r['values']for r in current};targets={r['axis_edge_id']:r for r in context['records']};added=[]
    if set(old)!=set(new)or len(old)!=len(prior)or len(new)!=len(current)or len(targets)!=len(context['records']):raise ValueError('bridge edge inventory changed')
    for eid,before in old.items():
        after=new[eid]
        if eid not in targets:
            if after!=before:raise ValueError('unrelated effective attribute changed '+eid)
            continue
        r=targets[eid]
        if before.get('diameter_nominal_mm')not in(None,'',r['nominal_mm'])or after.get('diameter_nominal_mm')!=r['nominal_mm']:raise ValueError('known DN changed or bridge DN absent '+eid)
        for k in before.keys()|after.keys():
            if before.get(k)!=after.get(k)and k not in CHANGED:raise ValueError('inherited target value changed '+eid+'/'+k)
        if after.get('member_bridge_mapping_id')!=r['mapping_id']or after.get('member_bridge_plan_edge')!=r['source_parent_plan_edge']or after.get('member_bridge_DN_mm')!=r['nominal_mm']or after.get('member_bridge_plan_pipe_projection_mm')!=r['plan_pipe_projection_mm']or json.loads(after.get('member_bridge_component_pairs_json','[]'))!=r['component_correspondences']or json.loads(after.get('member_bridge_evidence_json','{}'))!=r:raise ValueError('bridge actual CSV does not match native context '+eid)
        if before.get('diameter_nominal_mm')in(None,''):added.append(eid)
    return dict(qualified_bridges=len(targets),new_known_DN=len(added),new_known_DN_edges=sorted(added),new_plan_pipe_projections=len(targets),component_pairs=sum(len(r['component_correspondences'])for r in targets.values()),all_old_known_DN_preserved=True,all_non_target_effective_values_exact=True,old_vertical_and_other_target_fields_exact=True,new_complete_centerlines=0,new_installed_lengths=0,new_net_cut_lengths=0)

def refresh(parent,output,templates,graph,devices,source,legend,comparison,proof,qualification,qualification_sha,port=10355):
    parent,output,templates=map(lambda p:Path(p).resolve(),(parent,output,templates));archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh external viewer output required')
    manifest,inputs=qualified_parent(parent,graph,devices,source,legend,comparison,qualification,qualification_sha);before=base.artifact_inventory(parent);context=copy.deepcopy(manifest['attributeValueContext'])
    if 'compound_member_bridges'in context:raise ValueError('bridge context already composed')
    context['compound_member_bridges']=from_artifact(graph,parent/'public/data/graph.json',proof,context)
    paths=[Path(p)for p in(graph,devices,source,legend,comparison,proof,qualification)];input_hashes={str(p.resolve()):sha(p)for p in paths}
    changes={n:sha(templates/n)for n in ALLOWED if sha(templates/n)!=manifest['templateHashes'].get(n)}
    if not changes:raise ValueError('no new bridge attribute templates')
    prior=base.effective_attributes(parent);shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in changes:shutil.copy2(templates/n,output/n)
    provisional=copy.deepcopy(manifest);provisional['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encoded(provisional))
    current=base.effective_attributes(output);change=delta(prior,current,context['compound_member_bridges']);effective_hash=hashlib.sha256(encoded(current)).hexdigest()
    revised=base.revised_manifest(manifest,changes,effective_hash,sha(__file__),port,context);revised['attributeTemplateRefresh']['mode']=MODE;revised['sourceHashes']['compound_member_bridge_proof']=sha(proof)
    (output/'public/data/manifest.json').write_bytes(encoded(revised));p=output/'public/index.html';p.write_text(p.read_text(encoding='utf8').replace(manifest['bundleId'],revised['bundleId']),encoding='utf8')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    doc,readable=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encoded(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('native viewer/schema checks failed')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('source payload or annotation changed '+n)
    if base.artifact_inventory(parent)!=before or any(sha(p)!=h for p,h in input_hashes.items()):raise ValueError('native input or parent changed during composition')
    evidence=output/'member-bridge-refresh';evidence.mkdir();(evidence/'parent-effective.json').write_bytes(encoded(prior));(evidence/'current-effective.json').write_bytes(encoded(current));shutil.copy2(proof,evidence/'native-member-bridges.json')
    audit=dict(mode=MODE,status='native_schema_source_fidelity_effective_delta_passed_actual_browser_pending',parent=str(parent),template_root=str(templates),source_paths={k:str(Path(v).resolve())for k,v in dict(graph=graph,devices=devices,source=source,legend=legend,comparison=comparison,proof=proof,qualification=qualification).items()},qualification_sha256=qualification_sha,original_input_hashes=input_hashes,parent_file_hashes=before,parent_bundle_id=manifest['bundleId'],bundle_id=revised['bundleId'],changes=changes,effective_attribute_hash=effective_hash,delta=change,source_preflight=readable,native_schema_status=schema['status'],native_drawing_status=quality['machine_status'],parent_original_qualified_artifact_reused=True,parent_native_replay_performed=False,new_member_bridge_native_reconstruction=True,canonical_axis_graph_mutated=False,rendered_axis_graph_mutated=False,component_assignments_mutated=False,old_annotations_preserved=True,human_confirmation_inherited=False,human_accepted=False)
    audit['output_hashes']={k:v for k,v in base.artifact_inventory(output).items()if k!='member-bridge-refresh.json'};(output/'member-bridge-refresh.json').write_bytes(encoded(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('new viewer ZIP failed')
    return audit

def verify(output):
    output=Path(output);a=load(output/'member-bridge-refresh.json');m=load(output/'public/data/manifest.json');parent=Path(a['parent']);p=a['source_paths']
    if a['mode']!=MODE or a['bundle_id']!=m['bundleId']or base.artifact_inventory(parent)!=a['parent_file_hashes']:raise ValueError('bridge viewer parent identity changed')
    qualified_parent(parent,p['graph'],p['devices'],p['source'],p['legend'],p['comparison'],p['qualification'],a['qualification_sha256'])
    if any(sha(p)!=h for p,h in a['original_input_hashes'].items()):raise ValueError('bridge viewer input changed')
    if {k:v for k,v in base.artifact_inventory(output).items()if k!='member-bridge-refresh.json'}!=a['output_hashes']:raise ValueError('bridge viewer bytes changed')
    prior=load(parent/'public/data/manifest.json')['attributeValueContext'];expected=copy.deepcopy(prior);expected['compound_member_bridges']=from_artifact(p['graph'],output/'public/data/graph.json',p['proof'],prior)
    if m['attributeValueContext']!=expected:raise ValueError('viewer bridge context differs from native replay')
    actual=base.effective_attributes(output)
    if hashlib.sha256(encoded(actual)).hexdigest()!=a['effective_attribute_hash']or delta(base.effective_attributes(parent),actual,expected['compound_member_bridges'])!=a['delta']:raise ValueError('viewer effective bridge values differ')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],parent_qualified_artifact_reused=True,new_member_bridge_native_reconstruction=True,human_accepted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--verify',type=Path)
    for n in('parent','output','templates','graph','devices','source','legend','comparison','proof','qualification'):p.add_argument('--'+n,type=Path)
    p.add_argument('--qualification-sha256');p.add_argument('--port',type=int,default=10355);a=p.parse_args()
    if a.verify:r=verify(a.verify)
    else:
        keys=('parent','output','templates','graph','devices','source','legend','comparison','proof','qualification')
        if any(getattr(a,n)is None for n in keys)or not a.qualification_sha256:p.error('all pinned inputs required')
        r=refresh(**{n:getattr(a,n)for n in keys},qualification_sha=a.qualification_sha256,port=a.port)
    print(json.dumps(dict(status=r['status'],bundle_id=r['bundle_id']),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
