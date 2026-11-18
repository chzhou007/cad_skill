"""Adopt native member values while retaining all original drawing data."""
import copy,hashlib,json,shutil,sys,zipfile
from pathlib import Path
for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
import refresh_attribute_templates as base
from native_replay_session import verify_once
from riser_header_interval_application import verify_output as native_owner,MODE as NATIVE_MODE,encode as native_encoded
sha,load,encoded=base.sha,base.load,base.encoded
MODE='qualified_viewer_reanchored_riser_header_attributes_v1'
CONTEXT_MODE='qualified_riser_header_interval_application_v1'
ALLOWED={'public/edge-attributes.js','public/cycle-carrier-guard-attributes.js','public/riser-header-member-attributes.js'}

def context_from(path,parent_manifest):
    p=Path(path);r=verify_once(p.parent,native_owner);m=load(parent_manifest);old=m['attributeValueContext']
    if r['mode']!=NATIVE_MODE or native_encoded(r)!=p.read_bytes()or r['inputs']['parent_manifest']['sha256']!=sha(parent_manifest):raise ValueError('riser member source/context differs')
    out=dict(load(p),native_mode=NATIVE_MODE,mode=CONTEXT_MODE,source_proof_sha256=sha(p),source_bindings={k:v['sha256']for k,v in r['inputs'].items()},prior_guard_proof_sha256=old['cycle_carrier_guards']['source_proof_sha256'])
    if out['source_bindings']['raw_axis_graph']!=old['source_graph_sha256']or out['source_bindings']['rendered_graph']!=old['rendered_graph_sha256']:raise ValueError('riser context belongs to other axis graph')
    return out

def delta(prior,current,context):
    old={r['edge_id']:r['values']for r in prior};new={r['edge_id']:r['values']for r in current};members={r['axis_edge_id']:r for r in context['member_records']};cleared={r['axis_edge_id']:r for r in context['cycle_clearances']}
    if old.keys()!=new.keys()or len(old)!=len(prior)or len(new)!=len(current):raise ValueError('riser refresh changed axis edge population')
    for eid,before in old.items():
        after=new[eid]
        for k,v in before.items():
            if eid in cleared and k.startswith('cycle_carrier_'):
                if k in after:raise ValueError('cleared historical hold remains active')
            elif k not in after or after[k]!=v:raise ValueError('unrelated old effective value changed '+eid+'/'+k)
        added={k:v for k,v in after.items()if k not in before}
        if eid in members:
            row=members[eid]
            if any(not k.startswith('riser_header_')for k in added)or after.get('riser_header_mapping_id')!=row['mapping_id']or after.get('riser_header_plan_DN_mm')!=(row['nominal_mm']if row['nominal_mm']is not None else'')or after.get('riser_header_complete_centerline_mm')!=(row['complete_horizontal_centerline_mm']if row['complete_horizontal_centerline_mm']is not None else'')or json.loads(after.get('riser_header_evidence_json','{}'))!=row:raise ValueError('member values differ from native application')
        elif eid in cleared:
            row=cleared[eid]
            if any(not(k.startswith('cycle_gate_')or k.startswith('cycle_carrier_clearance_'))for k in added)or after.get('cycle_gate_complete_centerline_mm')!=row['complete_horizontal_centerline_mm']or json.loads(after.get('cycle_carrier_clearance_evidence_json','{}'))!=row:raise ValueError('cleared metric differs from native source')
        elif added:raise ValueError('unrelated edge acquired riser values')
    return dict(new_member_correspondence_edges=len(members),new_plan_DN_values=sum(r['nominal_mm']is not None for r in members.values()),new_complete_horizontal_lengths=sum(r['complete_horizontal_centerline_mm']is not None for r in members.values()),restored_native_cycle_lengths=len(cleared),other_old_values_exact=True,installed_lengths_assigned=0)

def refresh(parent,output,templates,source_path,port=10363):
    from refresh_cycle_carrier_guards import verify as parent_owner
    parent,output,templates=[Path(p).resolve()for p in(parent,output,templates)];archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh external riser viewer required')
    if parent_owner(parent).get('artifact_replay')!='passed':raise ValueError('riser viewer parent not qualified')
    m=load(parent/'public/data/manifest.json');before=base.artifact_inventory(parent);input_hash=sha(source_path);native=context_from(source_path,parent/'public/data/manifest.json');context=copy.deepcopy(m['attributeValueContext'])
    if 'riser_header_application'in context:raise ValueError('member source already applied')
    context['riser_header_application']=native;old=base.effective_attributes(parent);changes={n:sha(templates/n)for n in ALLOWED if not(parent/n).exists()or sha(templates/n)!=m['templateHashes'].get(n)}
    if set(changes)!=ALLOWED:raise ValueError('all declared riser readers required')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in changes:shutil.copy2(templates/n,output/n)
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encoded(revised));current=base.effective_attributes(output);difference=delta(old,current,native);digest=hashlib.sha256(encoded(current)).hexdigest()
    revised['templateHashes'].update(changes);revised['preferredPort']=port;revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encoded(context)).hexdigest());revised['sourceHashes']['riser_header_application']=input_hash
    revised['attributeTemplateRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],changed_templates=changes,implementation_sha256=sha(__file__),human_confirmation_inherited=False,declared_semantic_change=difference)
    revised['bundleId']=hashlib.sha256(encoded(dict(parent=m['bundleId'],templates=changes,effective=digest,implementation=sha(__file__),port=port))).hexdigest()[:20];(output/'public/data/manifest.json').write_bytes(encoded(revised));p=output/'public/index.html';p.write_text(p.read_text(encoding='utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    source=load(source_path)['inputs']['axis_source']['path'];from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encoded(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('riser viewer native rendering failed')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('riser refresh changed native graph/data or historical annotations')
    if base.artifact_inventory(parent)!=before or sha(source_path)!=input_hash:raise ValueError('riser viewer parent/source changed')
    proof=output/'riser-header-application';proof.mkdir();(proof/'parent-effective.json').write_bytes(encoded(old));(proof/'current-effective.json').write_bytes(encoded(current));shutil.copy2(source_path,proof/'native-application.json')
    audit=dict(mode=MODE,status='native_member_values_and_rendering_passed_actual_browser_pending',parent=str(parent),parent_bundle_id=m['bundleId'],bundle_id=revised['bundleId'],native_source_path=str(Path(source_path).resolve()),native_source_sha256=input_hash,parent_file_hashes=before,changes=changes,delta=difference,effective_attribute_hash=digest,source_preflight=preflight,old_graphs_and_components_unchanged=True,old_annotations_preserved=True,related_confirmation_invalidated=True,human_accepted=False)
    audit['output_hashes']={n:h for n,h in base.artifact_inventory(output).items()if n!='riser-header-application.json'};(output/'riser-header-application.json').write_bytes(encoded(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('riser viewer archive failed')
    return audit

def verify(output):
    from refresh_cycle_carrier_guards import verify as parent_owner
    output=Path(output);a=load(output/'riser-header-application.json');m=load(output/'public/data/manifest.json');parent=Path(a['parent'])
    if a['mode']!=MODE or a['bundle_id']!=m['bundleId']or m['attributeTemplateRefresh']['implementation_sha256']!=sha(__file__)or base.artifact_inventory(parent)!=a['parent_file_hashes']:raise ValueError('riser viewer identity changed')
    parent_owner(parent);expected=copy.deepcopy(load(parent/'public/data/manifest.json')['attributeValueContext']);expected['riser_header_application']=context_from(a['native_source_path'],parent/'public/data/manifest.json')
    if sha(a['native_source_path'])!=a['native_source_sha256']or expected!=m['attributeValueContext']or {n:h for n,h in base.artifact_inventory(output).items()if n!='riser-header-application.json'}!=a['output_hashes']:raise ValueError('riser viewer source/context changed')
    actual=base.effective_attributes(output)
    if hashlib.sha256(encoded(actual)).hexdigest()!=a['effective_attribute_hash']or delta(base.effective_attributes(parent),actual,expected['riser_header_application'])!=a['delta']:raise ValueError('riser viewer effective values changed')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],counts=a['delta'],human_accepted=False)
