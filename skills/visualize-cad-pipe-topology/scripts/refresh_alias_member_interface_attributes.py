"""Versioned source-qualified mapping/attribute extension of an unchanged viewer."""
import argparse,copy,hashlib,json,shutil,sys,zipfile
from pathlib import Path
import refresh_attribute_templates as base
from alias_member_interface_context import from_artifact
MODE='qualified_viewer_confirmed_alias_member_interfaces_v1'
ALLOWED={'public/edge-attributes.js','public/alias-member-interface-attributes.js'}
sha,load,encoded=base.sha,base.load,base.encoded

def qualified_parent(parent,graph,devices,source,legend,comparison,qualification,qualification_sha):
    if sha(qualification)!=qualification_sha:raise ValueError('original bounded viewer qualification changed')
    saved=load(qualification);manifest,inputs=base.parent_check(parent,graph,devices,source,legend,comparison);audit=load(Path(parent)/'bounded-main-extent-refresh.json')
    if saved['formal_artifact_replay'].get('artifact_replay')!='passed' or saved['formal_artifact_replay']['bundle_id']!=manifest['bundleId'] or saved['result']!=audit:raise ValueError('parent is not the independently qualified bounded viewer')
    if any(sha(p)!=h for p,h in audit['original_input_hashes'].items()):raise ValueError('qualified parent native input changed')
    context=manifest['attributeValueContext']
    if context['source_graph_sha256']!=sha(graph) or context['rendered_graph_sha256']!=sha(Path(parent)/'public/data/graph.json') or hashlib.sha256(encoded(context)).hexdigest()!=manifest['reviewContentHashes']['attribute_value_context']:raise ValueError('qualified parent attribute identity changed')
    if hashlib.sha256(encoded(base.effective_attributes(parent))).hexdigest()!=audit['effective_attribute_hash']:raise ValueError('qualified parent actual effective attributes changed')
    return manifest,inputs


def delta(prior,current,context):
    old={r['edge_id']:r['values']for r in prior};new={r['edge_id']:r['values']for r in current};targets={r['axis_edge_id']:r for r in context['records']}
    if old.keys()!=new.keys() or len(targets)!=len(context['records']):raise ValueError('alias member effective edge inventory changed')
    complete=[];partial=[]
    whole={'diameter_nominal_mm','diameter_text','diameter_status','physical_edge_length_status'}
    for eid,before in old.items():
        after=new[eid]
        if eid not in targets:
            if before!=after:raise ValueError('unrelated effective attributes changed: '+eid)
            continue
        row=targets[eid];main=row['kind']=='primary_member_main'
        for key in before.keys()|after.keys():
            if before.get(key)!=after.get(key) and not(key.startswith('alias_member_')or main and key in whole):raise ValueError('old or vertical attribute changed: '+eid+'/'+key)
        domains=row['attribute_source_domains']
        if after.get('alias_member_horizontal_DN_mm')!=row['nominal_mm']or after.get('alias_member_horizontal_complete_centerline_mm')!=domains['horizontal_complete_centerline_mm']:raise ValueError('alias member effective horizontal value differs')
        if main:
            if before.get('diameter_nominal_mm') not in(None,'',row['nominal_mm']) or after.get('diameter_nominal_mm')!=row['nominal_mm']or after.get('alias_member_complete_centerline_mm')!=domains['horizontal_complete_centerline_mm']:raise ValueError('new primary value conflicts or is incomplete')
            complete.append(eid)
        else:
            if after.get('alias_member_complete_centerline_mm') not in(None,''):raise ValueError('mixed approach gained whole length')
            partial.append(eid)
    return dict(complete_primary_members=sorted(complete),mixed_horizontal_scopes=sorted(partial),unrelated_edges_unchanged=len(old)-len(targets),all_old_vertical_values_unchanged=True,installed_lengths_assigned=0)


def refresh(parent,output,templates,graph,devices,source,legend,comparison,proof,qualification,qualification_sha,port=10359):
    parent,output,templates=map(lambda p:Path(p).resolve(),(parent,output,templates));archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh external viewer required')
    manifest,inputs=qualified_parent(parent,graph,devices,source,legend,comparison,qualification,qualification_sha);before=base.artifact_inventory(parent);context=copy.deepcopy(manifest['attributeValueContext'])
    if 'alias_member_interfaces'in context:raise ValueError('new owner mapping already composed')
    context['alias_member_interfaces']=from_artifact(graph,parent/'public/data/graph.json',proof,context)
    paths=[Path(p)for p in(graph,devices,source,legend,comparison,proof,qualification)];input_hashes={str(p.resolve()):sha(p)for p in paths};changes={n:sha(templates/n)for n in ALLOWED if sha(templates/n)!=manifest['templateHashes'].get(n)}
    if changes.keys()!=ALLOWED:raise ValueError('the declared specific-provider reader must be packaged')
    prior=base.effective_attributes(parent);shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in changes:shutil.copy2(templates/n,output/n)
    provisional=copy.deepcopy(manifest);provisional['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encoded(provisional))
    current=base.effective_attributes(output);change=delta(prior,current,context['alias_member_interfaces']);effective_hash=hashlib.sha256(encoded(current)).hexdigest()
    revised=copy.deepcopy(manifest);revised['templateHashes'].update(changes);revised['preferredPort']=port;revised['attributeValueContext']=context;revised['reviewContentHashes']['effective_edge_attributes']=effective_hash;revised['reviewContentHashes']['attribute_value_context']=hashlib.sha256(encoded(context)).hexdigest();revised['sourceHashes']['alias_member_interface_proof']=sha(proof)
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
    evidence=output/'alias-member-interface-refresh';evidence.mkdir();(evidence/'parent-effective.json').write_bytes(encoded(prior));(evidence/'current-effective.json').write_bytes(encoded(current));shutil.copy2(proof,evidence/'native-alias-member-interfaces.json');shutil.copy2(Path(proof).with_name('member_graph.json'),evidence/'member_graph.json')
    audit=dict(mode=MODE,status='native_schema_fidelity_and_new_member_effective_delta_passed_actual_browser_pending',parent=str(parent),template_root=str(templates),source_paths={k:str(Path(v).resolve())for k,v in dict(graph=graph,devices=devices,source=source,legend=legend,comparison=comparison,proof=proof,qualification=qualification).items()},qualification_sha256=qualification_sha,original_input_hashes=input_hashes,parent_file_hashes=before,parent_bundle_id=manifest['bundleId'],bundle_id=revised['bundleId'],changes=changes,effective_attribute_hash=effective_hash,delta=change,source_preflight=readable,native_schema_status=schema['status'],native_drawing_status=quality['machine_status'],parent_original_qualified_artifact_reused=True,parent_native_replay_performed=False,new_crossview_native_reconstruction=True,canonical_axis_graph_mutated=False,rendered_axis_graph_mutated=False,component_assignments_mutated=False,old_annotations_preserved=True,human_confirmation_inherited=False,human_accepted=False)
    audit['output_hashes']={k:v for k,v in base.artifact_inventory(output).items()if k!='alias-member-interface-refresh.json'};(output/'alias-member-interface-refresh.json').write_bytes(encoded(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('new viewer ZIP failed')
    return audit

def verify(output):
    output=Path(output);a=load(output/'alias-member-interface-refresh.json');m=load(output/'public/data/manifest.json');parent=Path(a['parent']);p=a['source_paths']
    if a['mode']!=MODE or a['bundle_id']!=m['bundleId']or m['attributeTemplateRefresh']['implementation_sha256']!=sha(__file__)or base.artifact_inventory(parent)!=a['parent_file_hashes']:raise ValueError('new mapped viewer identity changed')
    qualified_parent(parent,p['graph'],p['devices'],p['source'],p['legend'],p['comparison'],p['qualification'],a['qualification_sha256'])
    if any(sha(p)!=h for p,h in a['original_input_hashes'].items()):raise ValueError('mapped viewer native input changed')
    if {k:v for k,v in base.artifact_inventory(output).items()if k!='alias-member-interface-refresh.json'}!=a['output_hashes']:raise ValueError('mapped viewer bytes changed')
    prior=load(parent/'public/data/manifest.json')['attributeValueContext'];expected=copy.deepcopy(prior);expected['alias_member_interfaces']=from_artifact(p['graph'],output/'public/data/graph.json',p['proof'],prior)
    if m['attributeValueContext']!=expected:raise ValueError('new mapping context differs from independent native replay')
    actual=base.effective_attributes(output)
    if hashlib.sha256(encoded(actual)).hexdigest()!=a['effective_attribute_hash']or delta(base.effective_attributes(parent),actual,expected['alias_member_interfaces'])!=a['delta']:raise ValueError('new mapped effective attributes differ')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],new_crossview_native_reconstruction=True,human_accepted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--verify',type=Path)
    for n in('parent','output','templates','graph','devices','source','legend','comparison','proof','qualification'):p.add_argument('--'+n,type=Path)
    p.add_argument('--qualification-sha256');p.add_argument('--port',type=int,default=10359);a=p.parse_args()
    if a.verify:r=verify(a.verify)
    else:
        keys=('parent','output','templates','graph','devices','source','legend','comparison','proof','qualification')
        if any(getattr(a,n)is None for n in keys)or not a.qualification_sha256:p.error('all pinned native inputs required')
        r=refresh(**{n:getattr(a,n)for n in keys},qualification_sha=a.qualification_sha256,port=a.port)
    print(json.dumps(dict(status=r['status'],bundle_id=r['bundle_id']),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
