"""Adopt native omission DN without changing any historical effective value."""
import copy,hashlib,shutil,zipfile
from pathlib import Path
import refresh_anchored_terminal_branches as prior
from axis_omission_vertical_DN import verify_output, MODE as NATIVE_MODE
sha,load,encode=prior.sha,prior.load,prior.encode
MODE='native_omission_vertical_DN_viewer_v1'
AUDIT='native-omission-vertical-DN-refresh.json'
EVIDENCE='omission-vertical-DN-refresh'
FIELDS={'axis_omission_vertical_DN_segment_count','axis_omission_vertical_DN_segments_json','axis_omission_vertical_DN_source_sha256'}
TEMPLATES=('public/edge-attributes.js','public/omission-vertical-DN.js','public/edge-attributes-omission-vertical.js')
key=lambda r:(r['edge_id'],r['path_index'],r['segment_index'])


def context_from(parent,proof,path):
    parent=Path(parent);m=load(parent/'public/data/manifest.json');context=copy.deepcopy(m['attributeValueContext'])
    if (proof['mode']!=NATIVE_MODE or proof['graph_mutated'] is not False or proof['horizontal_attributes_changed'] is not False
        or proof['physical_lengths_assigned']!=0 or proof['human_accepted'] is not False or 'omission_vertical_DN' in context):
        raise ValueError('unsupported omission proof or repeated adoption')
    if any(sha(v['path'])!=v['sha256'] for v in proof['inputs'].values()):raise ValueError('native proof input changed')
    if sha(parent/'public/data/manifest.json')!=proof['inputs']['viewer_manifest']['sha256']:
        raise ValueError('current published viewer differs from native batch parent')
    native=load(proof['inputs']['axis_graph']['path']);rendered=load(parent/'public/data/graph.json')
    by={e['edge_id']:e for e in native['edges']};view={e['edge_id']:e for e in rendered['edges']}
    source=proof['inputs']['axis_source']['sha256'];rh=sha(parent/'public/data/graph.json')
    if source!=m['sourceHashes']['main_dxf'] or rh!=context['current_rendered_graph_sha256'] or set(by)!=set(view):
        raise ValueError('native/current rendered source identity differs')
    seeds={key(r):r for r in context['axis_vertical_segment_DN']['records']}
    occupied=set(seeds)|{key(r) for r in context['graph_first_extensions']['vertical_records']}
    for e in rendered['edges']:
        occupied.update((e['edge_id'],r['path_index'],r['segment_index']) for r in e.get('axis_riser_attributes',[]))
    if len(occupied)!=proof['counts']['previous_known']:raise ValueError('actual previous vertical inventory differs')
    records=[];new=set()
    for r in proof['records']:
        k=key(r);seed=r['seed_record'];old=seeds.get(key(seed));e=by[r['edge_id']];shown=view[r['edge_id']]
        if (k in occupied or k in new or old is None or old['observations']!=seed['observations'] or old['nominal_mm']!=r['nominal_mm']
            or any(e.get(f)!=shown.get(f) for f in ('edge_id','system','start_node_id','end_node_id','attribute_paths'))
            or e['attribute_paths'][r['path_index']][r['segment_index']:r['segment_index']+2]!=r['scope_points']
            or e['system']!=r['system'] or seed['system']!=r['system'] or seed['edge_id']!=r['edge_id']
            or seed['path_index']==r['path_index'] or r['whole_edge_DN_assigned'] is not False or r['physical_length_mm'] is not None):
            raise ValueError('target or original seed differs from current viewer')
        c=r['continuity_evidence'];guard=r['annotation_guard']
        if (c['source']!='original_native_omission_pair_replayed' or c['physical_T_crossed'] is not False
            or c['inline_joint_crossed'] is not False or c['physical_length_mm'] is not None
            or guard['other_in_scope_DN_annotations'] or guard['F_crossings']):raise ValueError('omission inheritance escaped original barriers')
        records.append(dict(edge_id=r['edge_id'],path_index=r['path_index'],segment_index=r['segment_index'],system=r['system'],
            nominal_mm=r['nominal_mm'],scope_points=copy.deepcopy(r['scope_points']),axis_source_sha256=source,
            seed_domain=dict(edge_id=seed['edge_id'],path_index=seed['path_index'],segment_index=seed['segment_index'],nominal_mm=seed['nominal_mm']),
            seed_text_handles=guard['seed_text_handles'],omission=dict(source=c['source'],marker_chains=[x['source_chain'] for x in c['markers']],
                contacts=copy.deepcopy(c['contacts']),physical_T_crossed=False,inline_joint_crossed=False,physical_length_mm=None),
            physical_length_mm=None,whole_edge_DN_assigned=False,related_HIL_confirmation_inherited=False,human_accepted=False))
        new.add(k)
    if len(new)!=proof['counts']['new_known'] or len(occupied|new)!=proof['counts']['current_known']:raise ValueError('new vertical inventory differs')
    context['omission_vertical_DN']=dict(mode='qualified_native_omission_vertical_DN_context_v1',records=records,count=len(records),
        source_bindings=dict(native_source=source,native_graph=proof['inputs']['axis_graph']['sha256'],native_proof=sha(path),rendered_graph=rh),
        old_vertical_domains=len(occupied),all_current_vertical_domains=len(occupied|new),remaining_unknown=proof['counts']['remaining_unknown'],
        raw_graph_changed=False,physical_lengths_assigned=0,whole_edge_DN_assigned=0,human_accepted=False)
    return context


def delta(before,after,context):
    old={r['edge_id']:r['values'] for r in before};new={r['edge_id']:r['values'] for r in after}
    if old.keys()!=new.keys():raise ValueError('effective edge population changed')
    rows=context['omission_vertical_DN']['records'];changed=[]
    for eid,values in old.items():
        actual=new[eid];selected=[r for r in rows if r['edge_id']==eid]
        if {k:v for k,v in actual.items() if k not in FIELDS}!=values:raise ValueError('historical effective value changed '+eid)
        if selected:
            import json
            if (actual.get('axis_omission_vertical_DN_segment_count')!=len(selected)
                or json.loads(actual.get('axis_omission_vertical_DN_segments_json','null'))!=selected
                or actual.get('axis_omission_vertical_DN_source_sha256')!=context['omission_vertical_DN']['source_bindings']['native_source']):
                raise ValueError('actual omission reader did not adopt exact native domains '+eid)
            changed.append(eid)
        elif actual!=values:raise ValueError('unrelated effective value changed '+eid)
    return dict(changed_edges=changed,new_vertical_domains=len(rows),all_old_effective_values_exact=True,new_whole_edge_DN=0,new_physical_lengths=0)


def refresh(parent,output,proof_path,templates,port):
    parent,output,proof_path,templates=map(lambda p:Path(p).resolve(),(parent,output,proof_path,templates))
    if output.exists() or parent in output.parents or output==parent:raise ValueError('fresh external output required')
    proof=verify_output(proof_path.parent);before=prior.base.artifact_inventory(parent);context=context_from(parent,proof,proof_path)
    old=prior.effective(parent);m=load(parent/'public/data/manifest.json')
    # Keep the independently qualified existing graph, providers and annotations.
    # This is native replay of the new family, not a new full-parent replay.
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in TEMPLATES:shutil.copy2(templates/name,output/name)
    app=output/'public/app.js';app_text=app.read_text('utf8')
    old_import="from './edge-attributes-terminal-branches.js';"
    if app_text.count(old_import)!=1:raise ValueError('published application reader entry differs')
    app.write_text(app_text.replace(old_import,"from './edge-attributes-omission-vertical.js';"),encoding='utf8')
    revised=copy.deepcopy(m);revised['attributeValueContext']=context
    (output/'public/data/manifest.json').write_bytes(encode(revised))
    current=prior.effective(output);change=delta(old,current,context);digest=hashlib.sha256(encode(current)).hexdigest()
    revised['preferredPort']=port
    revised['templateHashes'].update({name:sha(templates/name) for name in TEMPLATES})
    revised['templateHashes']['public/app.js']=sha(app)
    revised['sourceHashes']['native_omission_vertical_DN']=sha(proof_path)
    revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(context)).hexdigest())
    revised['nativeOmissionVerticalDNRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(proof_path),implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(proof_path),effective=digest,templates={n:sha(templates/n) for n in TEMPLATES},implementation=sha(__file__),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode(revised))
    index=output/'public/index.html';index.write_text(index.read_text('utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    provider=copy.deepcopy(load(proof['inputs']['provider']['path']))
    if provider['counts']['all_current_vertical_DN_domains']!=proof['counts']['previous_known']:raise ValueError('provider vertical parent differs')
    provider['counts']['all_current_vertical_DN_domains']=proof['counts']['current_known']
    provider['omission_vertical_DN']=dict(native_proof_sha256=sha(proof_path),new_domains=len(proof['records']),human_accepted=False)
    evidence=output/EVIDENCE;evidence.mkdir();(evidence/'provider-inventory.json').write_bytes(encode(provider));(evidence/'current-effective.json').write_bytes(encode(current));shutil.copy2(proof_path,evidence/'native-proof.json')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,preflight=read_source(source)
    schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed' or quality['machine_status']!='PASS':raise ValueError('source/schema gate failed')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/')) and n!='public/data/manifest.json' and sha(output/n)!=h:raise ValueError('source payload or annotation changed')
    if prior.base.artifact_inventory(parent)!=before:raise ValueError('parent artifact changed')
    audit=dict(mode=MODE,status='source_and_actual_reader_adoption_passed_browser_pending',parent=str(parent),parent_file_hashes=before,
        proof_path=str(proof_path),proof_sha256=sha(proof_path),bundle_id=revised['bundleId'],templates={n:sha(templates/n) for n in TEMPLATES},delta=change,
        source_preflight=preflight,parent_native_replay_performed=False,new_omission_native_replay_performed=True,old_annotations_preserved=True,human_accepted=False)
    audit['output_hashes']=prior.base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit));return audit


def verify(output):
    output=Path(output);audit=load(output/AUDIT);parent=Path(audit['parent']);path=Path(audit['proof_path']);proof=verify_output(path.parent)
    m=load(output/'public/data/manifest.json')
    if (audit['mode']!=MODE or audit['bundle_id']!=m['bundleId'] or sha(path)!=audit['proof_sha256']
        or m['nativeOmissionVerticalDNRefresh']['implementation_sha256']!=sha(__file__)
        or prior.base.artifact_inventory(parent)!=audit['parent_file_hashes']
        or {n:h for n,h in prior.base.artifact_inventory(output).items() if n!=AUDIT}!=audit['output_hashes']
        or context_from(parent,proof,path)!=m['attributeValueContext']):raise ValueError('viewer source or artifact binding changed')
    actual=prior.effective(output)
    if delta(prior.effective(parent),actual,m['attributeValueContext'])!=audit['delta']:raise ValueError('actual effective delta differs')
    expected=copy.deepcopy(load(proof['inputs']['provider']['path']));expected['counts']['all_current_vertical_DN_domains']=proof['counts']['current_known']
    expected['omission_vertical_DN']=dict(native_proof_sha256=sha(path),new_domains=len(proof['records']),human_accepted=False)
    if encode(expected)!=(output/EVIDENCE/'provider-inventory.json').read_bytes():raise ValueError('provider inheritance differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=audit['delta'],human_accepted=False)
