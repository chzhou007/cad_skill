"""Retract only unproved cycle physical claims; retain source readings/history."""
import argparse,copy,hashlib,json,shutil,sys,zipfile
from pathlib import Path
for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
import refresh_attribute_templates as base
from cycle_carrier_guards import verify_output as verify_guards,MODE as SOURCE_MODE,encode as native_encoded
from native_replay_session import verify_once
MODE='qualified_viewer_cycle_carrier_guard_correction_v1'
ALLOWED={'public/edge-attributes.js','public/graph-first-attribute-extensions.js','public/cycle-carrier-guard-attributes.js'}
sha,load,encoded=base.sha,base.load,base.encoded

def delta(prior,current,guard):
    old={r['edge_id']:r['values']for r in prior};new={r['edge_id']:r['values']for r in current};held={r['axis_edge_id']:r for r in guard['records']}
    if old.keys()!=new.keys()or len(old)!=len(prior)or len(new)!=len(current):raise ValueError('correction changed edge inventory')
    for eid,before in old.items():
        after=new[eid]
        for k,v in before.items():
            if eid in held and k.startswith('cycle_gate_'):
                if k in after:raise ValueError('held physical cycle field remains active')
            elif k not in after or after[k]!=v:raise ValueError('unrelated historical value changed '+eid+'/'+k)
        extra={k:v for k,v in after.items()if k not in before}
        if eid not in held:
            if extra:raise ValueError('unrelated edge acquired correction values')
        else:
            if any(not k.startswith('cycle_carrier_')for k in extra):raise ValueError('correction promoted other fields')
            r=held[eid]
            if after.get('cycle_carrier_drawing_projection_mm')!=r['drawing_carrier_projection_mm']or json.loads(after.get('cycle_carrier_evidence_json','{}'))!=r:raise ValueError('drawing-only value differs from native guard')
    return dict(held_physical_cycle_lengths=len(held),source_drawing_readings_retained=len(held),other_old_values_exact=True,new_physical_values=0)

def checked_guard(path,parent_manifest):
    r=verify_once(Path(path).parent,verify_guards)
    if r['mode']!=SOURCE_MODE or native_encoded(r)!=Path(path).read_bytes():raise ValueError('native carrier guard differs')
    manifest=load(parent_manifest);expected=manifest['attributeValueContext']
    if r['source_graph_sha256']!=expected['source_graph_sha256']or r['rendered_graph_sha256']!=expected['rendered_graph_sha256']or r['current_cycle_context_source_bindings']!=expected['graph_first_extensions']['source_bindings']:raise ValueError('carrier guard belongs to another viewer context')
    # Serialize to the same contract as the persisted native artifact.
    return dict(load(path),source_proof_sha256=sha(path),related_HIL_confirmation_inherited=False)

def refresh(parent,output,templates,guard_path,port=10362):
    from refresh_graph_first_attributes import verify as verify_parent
    parent,output,templates=map(lambda p:Path(p).resolve(),(parent,output,templates));archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh external correction output required')
    replay=verify_parent(parent);m=load(parent/'public/data/manifest.json')
    if replay.get('artifact_replay')!='passed'or 'cycle_carrier_guards'in m['attributeValueContext']:raise ValueError('original graph-first viewer not qualified')
    before=base.artifact_inventory(parent);input_hash=sha(guard_path);guard=checked_guard(guard_path,parent/'public/data/manifest.json');context=copy.deepcopy(m['attributeValueContext']);context['cycle_carrier_guards']=guard
    old=base.effective_attributes(parent);changes={n:sha(templates/n)for n in ALLOWED if not(parent/n).exists()or sha(templates/n)!=m['templateHashes'].get(n)}
    if changes.keys()!=ALLOWED:raise ValueError('all declared correction readers required')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in changes:shutil.copy2(templates/n,output/n)
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encoded(revised));current=base.effective_attributes(output);change=delta(old,current,guard);effective_hash=hashlib.sha256(encoded(current)).hexdigest()
    revised['templateHashes'].update(changes);revised['preferredPort']=port;revised['reviewContentHashes'].update(effective_edge_attributes=effective_hash,attribute_value_context=hashlib.sha256(encoded(context)).hexdigest());revised['sourceHashes']['cycle_carrier_guard']=input_hash
    revised['attributeTemplateRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],changed_templates=changes,implementation_sha256=sha(__file__),human_confirmation_inherited=False,declared_semantic_correction=change)
    revised['bundleId']=hashlib.sha256(encoded(dict(parent=m['bundleId'],templates=changes,effective=effective_hash,implementation=sha(__file__),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encoded(revised));p=output/'public/index.html';p.write_text(p.read_text(encoding='utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    source=load(parent/'graph-first-refresh.json')['source_paths']['source'];from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encoded(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('correction native source rendering failed')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('correction mutated graph/components/source/annotations')
    if base.artifact_inventory(parent)!=before or sha(guard_path)!=input_hash:raise ValueError('correction parent/input changed')
    evidence=output/'cycle-carrier-correction';evidence.mkdir();(evidence/'parent-effective.json').write_bytes(encoded(old));(evidence/'current-effective.json').write_bytes(encoded(current));shutil.copy2(guard_path,evidence/'native-guards.json')
    audit=dict(mode=MODE,status='native_correction_and_source_fidelity_passed_actual_browser_pending',parent=str(parent),parent_bundle_id=m['bundleId'],bundle_id=revised['bundleId'],guard_path=str(Path(guard_path).resolve()),guard_sha256=input_hash,parent_file_hashes=before,changes=changes,effective_attribute_hash=effective_hash,delta=change,source_preflight=preflight,historical_metric_evidence_retained=True,old_annotations_preserved=True,related_confirmation_invalidated=True,human_accepted=False)
    audit['output_hashes']={n:h for n,h in base.artifact_inventory(output).items()if n!='cycle-carrier-correction.json'};(output/'cycle-carrier-correction.json').write_bytes(encoded(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('correction viewer archive failed')
    return audit

def verify(output):
    from refresh_graph_first_attributes import verify as verify_parent
    output=Path(output);a=load(output/'cycle-carrier-correction.json');m=load(output/'public/data/manifest.json');parent=Path(a['parent'])
    if a['mode']!=MODE or a['bundle_id']!=m['bundleId']or m['attributeTemplateRefresh']['implementation_sha256']!=sha(__file__)or base.artifact_inventory(parent)!=a['parent_file_hashes']:raise ValueError('correction viewer identity changed')
    verify_parent(parent);prior=load(parent/'public/data/manifest.json')['attributeValueContext'];expected=copy.deepcopy(prior);expected['cycle_carrier_guards']=checked_guard(a['guard_path'],parent/'public/data/manifest.json')
    if sha(a['guard_path'])!=a['guard_sha256']or {n:h for n,h in base.artifact_inventory(output).items()if n!='cycle-carrier-correction.json'}!=a['output_hashes']or expected!=m['attributeValueContext']:raise ValueError('correction source/evidence changed')
    actual=base.effective_attributes(output)
    if hashlib.sha256(encoded(actual)).hexdigest()!=a['effective_attribute_hash']or delta(base.effective_attributes(parent),actual,expected['cycle_carrier_guards'])!=a['delta']:raise ValueError('correction effective values changed')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],counts=a['delta'],human_accepted=False)
