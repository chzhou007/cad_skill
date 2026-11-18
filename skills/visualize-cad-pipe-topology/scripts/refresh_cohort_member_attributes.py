"""Publish source-checked cohort intervals without changing local graph bytes."""
import copy,hashlib,json,shutil,sys,zipfile
from pathlib import Path
for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    p=str(Path(__file__).resolve().parents[2]/name/'scripts')
    if p not in sys.path:sys.path.insert(0,p)
import refresh_attribute_templates as base
from apply_equivalent_member_plan_attributes import verify_output as native_owner,MODE as NATIVE_MODE,encode as native_encoded
sha,load,encoded=base.sha,base.load,base.encoded
MODE='qualified_viewer_equivalent_member_plan_attributes_v1'
CONTEXT_MODE='qualified_equivalent_member_plan_attributes_v1'
ALLOWED={'public/edge-attributes.js','public/cohort-member-plan-attributes.js'}

def context_from(path,parent_manifest):
    path=Path(path);native=native_owner(path.parent);parent=load(parent_manifest);old=parent['attributeValueContext'];inputs=native['inputs'];source=native['source_batch_inputs']
    if native['mode']!=NATIVE_MODE or native_encoded(native)!=path.read_bytes()or inputs['parent_viewer_manifest']['sha256']!=sha(parent_manifest):raise ValueError('cohort source application or original viewer differs')
    if source['raw_axis_graph']['sha256']!=old['source_graph_sha256']or inputs['rendered_graph']['sha256']!=old['rendered_graph_sha256']or source['axis_graph']['sha256']!=old['riser_header_application']['source_bindings']['axis_graph']:raise ValueError('cohort source application has another graph ancestry')
    fields=('records','counts','complete_source_batch_replayed','existing_complete_DN_provider_retained','specific_calibrated_and_F_readers_reapplied','source_graphs_mutated','DN_used_for_mapping','physical_pipe_count_inferred','all_horizontal_values_from_plan','vertical_values_assigned','installed_lengths_assigned','unknown_length_filled_with_zero','human_accepted')
    context={k:copy.deepcopy(native[k])for k in fields};context.update(mode=CONTEXT_MODE,native_mode=NATIVE_MODE,source_proof_sha256=sha(path),source_bindings={**{k:v['sha256']for k,v in inputs.items()},'raw_axis_graph':source['raw_axis_graph']['sha256'],'native_axis_graph':source['axis_graph']['sha256'],'plan_source':source['plan_source']['sha256'],'plan_graph':source['plan_graph']['sha256']})
    # Native owners may return tuples for source points. The manifest and the
    # browser both speak JSON; compare the exact serialized representation.
    return json.loads(native_encoded(context))

def delta(prior,current,context):
    old={r['edge_id']:r['values']for r in prior};new={r['edge_id']:r['values']for r in current};targets={r['axis_edge_id']:r for r in context['records']};generic={'diameter_nominal_mm','diameter_text','diameter_status'}
    if old.keys()!=new.keys()or len(old)!=len(prior)or len(new)!=len(current)or len(targets)!=len(context['records']):raise ValueError('cohort viewer edge population differs')
    for eid,before in old.items():
        after=new[eid];row=targets.get(eid);known=row is not None and row['nominal_mm']is not None
        for key,value in before.items():
            if known and key in generic:
                if key=='diameter_nominal_mm'and isinstance(value,(int,float))and value>0 and value!=row['nominal_mm']:raise ValueError('new cohort DN conflicts with an existing known value')
                continue
            if key not in after or after[key]!=value:raise ValueError('old effective value changed outside declared cohort DN '+eid+'/'+key)
        added={k:v for k,v in after.items()if k not in before}
        if row is None:
            if added:raise ValueError('unrelated edge acquired cohort fields')
            continue
        if any(not k.startswith('cohort_member_')and not(known and k in generic)for k in added):raise ValueError('cohort refresh introduced an undeclared field')
        if (after.get('cohort_member_mapping_id')!=row['mapping_id']or after.get('cohort_member_plan_DN_mm')!=(row['nominal_mm']if known else'')or after.get('cohort_member_complete_centerline_mm')!=(row['complete_horizontal_centerline_mm']if row['complete_horizontal_centerline_mm']is not None else'')or after.get('cohort_member_drawn_projection_mm')!=row['drawn_plan_projection_mm']or json.loads(after.get('cohort_member_evidence_json','{}'))!=row):raise ValueError('effective cohort values differ from native source application')
        if known and (after.get('diameter_nominal_mm')!=row['nominal_mm']or after.get('diameter_text')!='DN'+format(row['nominal_mm'],'g')or after.get('diameter_status')!='cohort_member_native_plan_DN'):raise ValueError('generic DN column does not expose the qualified plan value')
    return dict(new_correspondence_intervals=len(targets),new_plan_DN_values=sum(r['nominal_mm']is not None for r in targets.values()),new_complete_horizontal_lengths=sum(r['complete_horizontal_centerline_mm']is not None for r in targets.values()),new_DN_and_length_complete=sum(r['nominal_mm']is not None and r['complete_horizontal_centerline_mm']is not None for r in targets.values()),all_other_effective_values_exact=True,old_known_DN_preserved=True,vertical_values_assigned=0,installed_lengths_assigned=0)

def refresh(parent,output,templates,source_path,port=10364):
    parent,output,templates=map(lambda p:Path(p).resolve(),(parent,output,templates));archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh external cohort viewer required')
    original=load(parent/'public/data/manifest.json');before=base.artifact_inventory(parent);source_hash=sha(source_path);native=context_from(source_path,parent/'public/data/manifest.json');context=copy.deepcopy(original['attributeValueContext'])
    if 'equivalent_member_application'in context:raise ValueError('cohort source application already published')
    context['equivalent_member_application']=native;old=base.effective_attributes(parent);changes={n:sha(templates/n)for n in ALLOWED if not(parent/n).exists()or sha(templates/n)!=original['templateHashes'].get(n)}
    if set(changes)!=ALLOWED:raise ValueError('all declared cohort readers required')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in changes:shutil.copy2(templates/name,output/name)
    revised=copy.deepcopy(original);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encoded(revised));current=base.effective_attributes(output);difference=delta(old,current,native);effective=hashlib.sha256(encoded(current)).hexdigest()
    revised['templateHashes'].update(changes);revised['preferredPort']=port;revised['reviewContentHashes'].update(effective_edge_attributes=effective,attribute_value_context=hashlib.sha256(encoded(context)).hexdigest());revised['sourceHashes']['equivalent_member_application']=source_hash;revised['attributeTemplateRefresh']=dict(mode=MODE,parent_bundle_id=original['bundleId'],changed_templates=changes,implementation_sha256=sha(__file__),human_confirmation_inherited=False,declared_semantic_change=difference)
    revised['bundleId']=hashlib.sha256(encoded(dict(parent=original['bundleId'],templates=changes,effective=effective,implementation=sha(__file__),port=port))).hexdigest()[:20];(output/'public/data/manifest.json').write_bytes(encoded(revised));index=output/'public/index.html';index.write_text(index.read_text(encoding='utf8').replace(original['bundleId'],revised['bundleId']),encoding='utf8')
    source=load(source_path)['source_batch_inputs']['axis_source']['path']
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encoded(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('cohort viewer native rendering failed')
    for name,digest in before.items():
        if name.startswith(('public/data/','annotations/'))and name!='public/data/manifest.json'and sha(output/name)!=digest:raise ValueError('cohort refresh changed graph/data or historical annotations')
    if base.artifact_inventory(parent)!=before or sha(source_path)!=source_hash:raise ValueError('cohort viewer original input changed')
    proof=output/'cohort-member-application';proof.mkdir();(proof/'parent-effective.json').write_bytes(encoded(old));(proof/'current-effective.json').write_bytes(encoded(current));shutil.copy2(source_path,proof/'native-application.json')
    audit=dict(mode=MODE,status='native_cohort_attributes_and_rendering_passed_actual_browser_pending',parent=str(parent),parent_bundle_id=original['bundleId'],bundle_id=revised['bundleId'],native_source_path=str(Path(source_path).resolve()),native_source_sha256=source_hash,parent_file_hashes=before,changes=changes,delta=difference,effective_attribute_hash=effective,source_preflight=preflight,old_graphs_and_components_unchanged=True,old_annotations_preserved=True,related_confirmation_invalidated=True,human_accepted=False)
    audit['output_hashes']={n:h for n,h in base.artifact_inventory(output).items()if n!='cohort-member-application.json'};(output/'cohort-member-application.json').write_bytes(encoded(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for name in sorted(base.inventory(output)):z.write(output/name,output.name+'/'+name)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('cohort viewer archive failed')
    return audit

def verify(output):
    output=Path(output);audit=load(output/'cohort-member-application.json');manifest=load(output/'public/data/manifest.json');parent=Path(audit['parent'])
    if audit['mode']!=MODE or audit['bundle_id']!=manifest['bundleId']or manifest['attributeTemplateRefresh']['implementation_sha256']!=sha(__file__)or base.artifact_inventory(parent)!=audit['parent_file_hashes']:raise ValueError('cohort viewer identity changed')
    native=context_from(audit['native_source_path'],parent/'public/data/manifest.json');expected=copy.deepcopy(load(parent/'public/data/manifest.json')['attributeValueContext']);expected['equivalent_member_application']=native
    if sha(audit['native_source_path'])!=audit['native_source_sha256']or expected!=manifest['attributeValueContext']or {n:h for n,h in base.artifact_inventory(output).items()if n!='cohort-member-application.json'}!=audit['output_hashes']:raise ValueError('cohort viewer source/context changed')
    actual=base.effective_attributes(output)
    if hashlib.sha256(encoded(actual)).hexdigest()!=audit['effective_attribute_hash']or delta(base.effective_attributes(parent),actual,native)!=audit['delta']:raise ValueError('cohort viewer effective values changed')
    return dict(status='pending',artifact_replay='passed',bundle_id=manifest['bundleId'],counts=audit['delta'],human_accepted=False)
