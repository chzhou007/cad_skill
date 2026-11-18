"""Publish conserved native owner changes and independently proved plan attributes."""
import copy,hashlib,json,shutil,sys,zipfile
from pathlib import Path
for name in ('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    path=str(Path(__file__).resolve().parents[2]/name/'scripts')
    if path not in sys.path:sys.path.insert(0,path)
import refresh_attribute_templates as base
from rebuild_native_contact_application import verify_output as native_owner,MODE as NATIVE_MODE
from native_contact_rendered_graph import restore
sha,load,encoded=base.sha,base.load,base.encoded
MODE='qualified_native_contact_owner_viewer_application_v1'
ALLOWED={'public/edge-attributes.js','public/contact-owner-plan-attributes.js'}

def context_from(proof,path,parent_manifest):
    original=load(parent_manifest);context=copy.deepcopy(original['attributeValueContext']);inputs=proof['inputs'];bi=proof['source_batch_inputs'];prior=context.get('component_inventory_bridge')
    if proof['mode']!=NATIVE_MODE or any(proof.get(key)is not True for key in ('complete_current_parent_replayed','native_owner_inventory_replayed','all_affected_old_scopes_requalified','pipe_graph_restoration_exact'))or inputs['parent_viewer_manifest']['sha256']!=sha(parent_manifest)or inputs['parent_rendered_graph']['sha256']!=context.get('current_rendered_graph_sha256')or prior is None:raise ValueError('native contact application is outside its qualified current parent')
    if 'contact_owner_application'in context:raise ValueError('contact application already adopted')
    context['contact_owner_prior_component_bridge']=copy.deepcopy(prior)
    context['current_rendered_graph_sha256']=proof['rendered_graph_sha256']
    context['component_inventory_bridge']=dict(prior,current_rendered_graph_sha256=proof['rendered_graph_sha256'],native_proof_sha256=sha(path),complete_parent_replayed=True,native_source_replayed=True,pipe_graph_restoration_exact=True)
    fields=('complete_current_parent_replayed','native_owner_inventory_replayed','all_affected_old_scopes_requalified','pipe_graph_restoration_exact','source_graphs_mutated','physical_pipe_count_inferred','DN_used_for_mapping','unknown_physical_parameters_filled','human_accepted')
    root={key:copy.deepcopy(proof[key])for key in fields};root.update(mode='qualified_native_contact_owner_path_attributes_v1',native_mode=NATIVE_MODE,source_proof_sha256=sha(path),records=copy.deepcopy(proof['attribute_records']),counts=copy.deepcopy(proof['counts']),source_bindings=dict(raw_axis_graph=bi['raw_axis_graph']['sha256'],native_axis_graph=bi['axis_graph']['sha256'],plan_source=bi['plan_source']['sha256'],plan_graph=bi['plan_graph']['sha256'],parent_rendered_graph=inputs['parent_rendered_graph']['sha256'],current_rendered_graph=proof['rendered_graph_sha256']))
    context['contact_owner_application']=root
    return json.loads(encoded(context))

def delta(prior,current,records):
    old={row['edge_id']:row['values']for row in prior};new={row['edge_id']:row['values']for row in current};targets={row['axis_edge_id']:row for row in records};generic={'diameter_nominal_mm','diameter_text','diameter_status'}
    if old.keys()!=new.keys()or len(targets)!=len(records):raise ValueError('contact pipe attribute population differs')
    for eid,before in old.items():
        after=new[eid];row=targets.get(eid);known=row is not None and row['nominal_mm']is not None
        for key,value in before.items():
            if known and key in generic:
                if key=='diameter_nominal_mm'and isinstance(value,(int,float))and value>0 and value!=row['nominal_mm']:raise ValueError('contact DN overwrites an old known value')
                continue
            if after.get(key)!=value or key not in after:raise ValueError('contact application changed an old pipe value '+eid+'/'+key)
        added={key for key in after if key not in before}
        if row is None:
            if added:raise ValueError('unrelated edge acquired contact attribute fields')
            continue
        if any(not key.startswith('contact_owner_')and not(known and key in generic)for key in added):raise ValueError('contact application introduced an undeclared attribute')
        if after.get('contact_owner_mapping_id')!=row['mapping_id']or after.get('contact_owner_plan_DN_mm')!=(row['nominal_mm']if known else'')or after.get('contact_owner_complete_centerline_mm')!=(row['complete_horizontal_centerline_mm']if row['complete_horizontal_centerline_mm']is not None else'')or json.loads(after.get('contact_owner_evidence_json','{}'))!=row:raise ValueError('contact effective attributes differ from native source proof')
        if known and (after.get('diameter_nominal_mm')!=row['nominal_mm']or after.get('diameter_text')!='DN'+format(row['nominal_mm'],'g')):raise ValueError('contact generic DN missing')
    return dict(new_correspondences=len(records),new_plan_DN_values=sum(row['nominal_mm']is not None for row in records),new_complete_horizontal_lengths=sum(row['complete_horizontal_centerline_mm']is not None for row in records),all_other_effective_pipe_values_exact=True,old_known_DN_preserved=True,vertical_values_assigned=0,unknown_installed_lengths_filled=0)

def refresh(parent,output,templates,native_path,port=10367):
    parent,output,templates,native_path=map(lambda p:Path(p).resolve(),(parent,output,templates,native_path));archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh external contact viewer required')
    before=base.artifact_inventory(parent);original=load(parent/'public/data/manifest.json');proof=native_owner(native_path.parent);native_graph=native_path.parent/'graph.json';graph=load(native_graph)
    if sha(native_graph)!=proof['rendered_graph_sha256']or restore(graph,proof['graph_audit'])!=load(parent/'public/data/graph.json'):raise ValueError('native contact graph cannot restore original current viewer')
    context=context_from(proof,native_path,parent/'public/data/manifest.json');old=base.effective_attributes(parent);changes={name:sha(templates/name)for name in ALLOWED}
    if any((parent/name).exists()and sha(parent/name)==value for name,value in changes.items()):raise ValueError('both declared contact readers required')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in changes:shutil.copy2(templates/name,output/name)
    shutil.copy2(native_graph,output/'public/data/graph.json');manifest=copy.deepcopy(original);manifest['attributeValueContext']=context;manifest['instances']=len(graph['instances']);(output/'public/data/manifest.json').write_bytes(encoded(manifest))
    current=base.effective_attributes(output);difference=delta(old,current,proof['attribute_records']);digest=hashlib.sha256(encoded(current)).hexdigest()
    manifest['templateHashes'].update(changes);manifest['preferredPort']=port;manifest['reviewContentHashes'].update(viewer_graph=sha(native_graph),effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encoded(context)).hexdigest());manifest['sourceHashes']['native_contact_application']=sha(native_path);manifest['sourceHashes']['native_contact_rendered_graph']=sha(native_graph)
    manifest['nativeContactRefresh']=dict(mode=MODE,parent_bundle_id=original['bundleId'],implementation_sha256=sha(__file__),native_proof_sha256=sha(native_path),pipe_graph_restoration_exact=True,human_confirmation_inherited=False)
    manifest['bundleId']=hashlib.sha256(encoded(dict(parent=original['bundleId'],native=sha(native_path),graph=sha(native_graph),templates=changes,implementation=sha(__file__),port=port))).hexdigest()[:20];(output/'public/data/manifest.json').write_bytes(encoded(manifest));index=output/'public/index.html';index.write_text(index.read_text(encoding='utf8').replace(original['bundleId'],manifest['bundleId']),encoding='utf8')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['source_batch_inputs']['axis_source']['path'];doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encoded(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('native contact rendering/schema failed')
    for name,value in before.items():
        if name.startswith(('public/data/','annotations/'))and name not in ('public/data/manifest.json','public/data/graph.json')and sha(output/name)!=value:raise ValueError('contact viewer changed historical data or annotations')
    if base.artifact_inventory(parent)!=before:raise ValueError('contact viewer mutated original parent')
    evidence=output/'native-contact-application';evidence.mkdir();shutil.copy2(native_path,evidence/'native-proof.json');(evidence/'parent-effective.json').write_bytes(encoded(old));(evidence/'current-effective.json').write_bytes(encoded(current))
    audit=dict(mode=MODE,status='native_contacts_and_path_attributes_passed_actual_browser_pending',parent=str(parent),parent_file_hashes=before,parent_bundle_id=original['bundleId'],bundle_id=manifest['bundleId'],native_proof_path=str(native_path),native_proof_sha256=sha(native_path),changes=changes,delta=difference,counts=proof['counts'],effective_attribute_sha256=digest,source_preflight=preflight,old_annotations_preserved=True,related_confirmation_invalidated=True,human_accepted=False)
    audit['output_hashes']={name:value for name,value in base.artifact_inventory(output).items()if name!='native-contact-application.json'};(output/'native-contact-application.json').write_bytes(encoded(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for name in sorted(base.inventory(output)):z.write(output/name,output.name+'/'+name)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('native contact viewer archive failed')
    return audit

def verify(output):
    output=Path(output);audit=load(output/'native-contact-application.json');manifest=load(output/'public/data/manifest.json');parent=Path(audit['parent']);path=Path(audit['native_proof_path'])
    if audit['mode']!=MODE or audit['bundle_id']!=manifest['bundleId']or manifest['nativeContactRefresh']['implementation_sha256']!=sha(__file__)or base.artifact_inventory(parent)!=audit['parent_file_hashes']:raise ValueError('contact viewer identity changed')
    proof=native_owner(path.parent)
    if sha(path)!=audit['native_proof_sha256']or context_from(proof,path,parent/'public/data/manifest.json')!=manifest['attributeValueContext']or sha(output/'public/data/graph.json')!=proof['rendered_graph_sha256']or restore(load(output/'public/data/graph.json'),proof['graph_audit'])!=load(parent/'public/data/graph.json'):raise ValueError('contact viewer graph or attribute bridge changed')
    if {name:value for name,value in base.artifact_inventory(output).items()if name!='native-contact-application.json'}!=audit['output_hashes']:raise ValueError('contact viewer payload changed')
    actual=base.effective_attributes(output);difference=delta(base.effective_attributes(parent),actual,proof['attribute_records'])
    if difference!=audit['delta']or hashlib.sha256(encoded(actual)).hexdigest()!=audit['effective_attribute_sha256']:raise ValueError('contact pipe values differ')
    return dict(status='pending',artifact_replay='passed',bundle_id=manifest['bundleId'],counts=audit['counts'],delta=difference,human_accepted=False)
