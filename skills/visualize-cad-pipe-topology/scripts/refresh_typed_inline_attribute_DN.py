"""Extend the existing axis-rule context; retain every prior CSV field and value."""
import copy,hashlib,json,shutil
from pathlib import Path
import refresh_plan_crossover_centrelines as prior
from reapply_typed_inline_attribute_DN import verify_output,MODE as NATIVE_MODE
sha,load,encode,effective=prior.sha,prior.load,prior.encode,prior.effective
MODE='inherited_typed_inline_axis_DN_viewer_v1'
AUDIT='typed-inline-DN-refresh.json';EVIDENCE='typed-inline-DN-refresh'
TEMPLATE='public/axis-rule-vertical-DN.js'
FIELDS={'axis_rule_vertical_DN_segment_count','axis_rule_vertical_DN_segments_json','axis_rule_vertical_DN_source_sha256'}
key=lambda r:(r['edge_id'],r['path_index'],r['segment_index'])


def context_from(parent,proof,path):
    parent=Path(parent);m=load(parent/'public/data/manifest.json');c=copy.deepcopy(m['attributeValueContext']);root=c['axis_rule_vertical_DN'];graph=load(parent/'public/data/graph.json');edges={e['edge_id']:e for e in graph['edges']}
    if proof['mode']!=NATIVE_MODE or proof['graph_mutated']is not False or proof['physical_lengths_assigned']!=0 or proof['horizontal_values_assigned']!=0 or proof['physical_ports_inferred']is not False or proof['human_accepted']is not False:raise ValueError('typed source contract differs')
    if any(sha(v['path'])!=v['sha256']for v in proof['inputs'].values())or sha(parent/'public/data/manifest.json')!=proof['inputs']['parent_viewer_manifest']['sha256']:raise ValueError('source or current parent changed')
    source=proof['inputs']['axis_source']['sha256']
    if root['all_current_vertical_domains']!=proof['counts']['previous_known']or root['source_bindings']['native_source']!=source or root['source_bindings']['native_graph']!=proof['inputs']['axis_graph']['sha256']or c['current_rendered_graph_sha256']!=sha(parent/'public/data/graph.json'):raise ValueError('current source domain differs')
    bodies=proof['direct_qualification']['typed_inline_body_evidence'];oldkeys={key(r)for r in root['records']};new=[]
    for r in proof['records']:
        e=edges[r['edge_id']];k=key(r);seed=r.get('seed_record',r);observations=seed['observations'];chains=[o['native_evidence']['source_chain']for o in observations]
        if k in oldkeys or r['system']!=e['system']or e['attribute_paths'][k[1]][k[2]:k[2]+2]!=r['scope_points']or r['physical_length_mm']is not None or r['whole_edge_DN_assigned']is not False:raise ValueError('source target overwrites old scope')
        selected=[b for b in bodies['qualified_typed_instances']if any(p[0]==b['root_handle']for p in chains)]
        if not selected or any(not any(x['typed_instance']['source_chain']==b['source_chain']for x in bodies['excluded_known_body_primitives'])for b in selected):raise ValueError('complete typed body exclusion evidence missing')
        bend='seed_record'in r
        if bend and not any(n['source_item']['root_handle']in {p[0]for p in chains}for n in proof['private_elbow_attribute_items']['records']):raise ValueError('inherited elbow source replay missing')
        if r['connection_rule']!=('original_nested_direct_DN_and_two_arm_bends'if bend else'original_direct_reader_complete_nested_WCS_projection'):raise ValueError('unsupported inherited connection rule')
        new.append(dict(edge_id=k[0],path_index=k[1],segment_index=k[2],system=r['system'],nominal_mm=r['nominal_mm'],scope_points=r['scope_points'],axis_source_sha256=source,seed_text_handles=sorted({o['source_text']['handle']for o in observations}),seed_domains=[{f:seed[f]for f in('edge_id','path_index','segment_index','system','nominal_mm')}],source_chains=chains,source_rules=['original_direct_DN_and_inherited_normalized_two_arm_bends'if bend else'original_direct_reader_with_typed_inline_body_evidence'],typed_component_body_instances=[dict(source_chain=b['source_chain'],type_code=b['type_code'],device_name=b['device_name'],block_signature_sha256=b['block_signature_sha256'],physical_ports_verified=False,primitive_count=len(b['primitives']))for b in selected],original_direct_reader_and_margin_unchanged=True,unknown_neutral_geometry_excluded=False,physical_ports_inferred=False,inherited_elbow_normalization_replayed=bend,physical_length_mm=None,whole_edge_DN_assigned=False,related_HIL_confirmation_inherited=False,human_accepted=False))
    if len(new)!=proof['counts']['new_known']or len({key(r)for r in new})!=len(new):raise ValueError('new exact vertical population differs')
    root['history_before_typed_inline_attribute_DN']={k:copy.deepcopy(root[k])for k in root if k!='records'}
    root['records'].extend(new);root.update(count=len(root['records']),all_current_vertical_domains=proof['counts']['current_known'],remaining_unknown=proof['counts']['remaining_unknown']);root['source_bindings']['native_proof']=sha(path)
    return json.loads(encode(c))


def delta(before,after,context,new_rows):
    old={r['edge_id']:r['values']for r in before};new={r['edge_id']:r['values']for r in after};targets={r['edge_id']for r in new_rows};changed=[]
    if old.keys()!=new.keys():raise ValueError('edge population changed')
    for eid,values in old.items():
        actual=new[eid]
        if eid not in targets:
            if actual!=values:raise ValueError('historical effective value changed '+eid)
            continue
        if any(k in values for k in FIELDS)or {k:v for k,v in actual.items()if k not in FIELDS}!=values:raise ValueError('old known attribute overwritten '+eid)
        rows=[r for r in context['axis_rule_vertical_DN']['records']if r['edge_id']==eid]
        if actual.get('axis_rule_vertical_DN_segment_count')!=len(rows)or json.loads(actual.get('axis_rule_vertical_DN_segments_json','null'))!=rows or actual.get('axis_rule_vertical_DN_source_sha256')!=context['axis_rule_vertical_DN']['source_bindings']['native_source']:raise ValueError('typed DN context not effectively adopted')
        changed.append(eid)
    return dict(changed_edges=sorted(changed),new_vertical_domains=len(new_rows),all_old_known_values_exact=True,old_csv_column_order_preserved=True,new_columns=0,new_lengths=0)


def provider_from(proof,path):
    p=copy.deepcopy(load(proof['inputs']['parent_provider']['path']))
    if p['counts']['all_current_vertical_DN_domains']!=proof['counts']['previous_known']:raise ValueError('provider parent differs')
    p['history_before_typed_inline_attribute_DN']=dict(counts=copy.deepcopy(p['counts']),legacy_top_level_vertical_domains=p.get('all_current_vertical_DN_domains'))
    p['counts']['all_current_vertical_DN_domains']=proof['counts']['current_known'];p['all_current_vertical_DN_domains']=proof['counts']['current_known'];p['typed_inline_attribute_DN']=dict(native_proof_sha256=sha(path),new_domains=len(proof['records']),human_accepted=False)
    return p


def refresh(parent,output,proof_path,templates,port):
    parent,output,proof_path,templates=map(lambda p:Path(p).resolve(),(parent,output,proof_path,templates))
    if output.exists()or parent in output.parents or output==parent:raise ValueError('fresh external output required')
    proof=verify_output(proof_path.parent);inventory=prior.prior.base.artifact_inventory(parent);c=context_from(parent,proof,proof_path);old=effective(parent);m=load(parent/'public/data/manifest.json');previous=len(m['attributeValueContext']['axis_rule_vertical_DN']['records']);new_rows=c['axis_rule_vertical_DN']['records'][previous:]
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.copy2(templates/TEMPLATE,output/TEMPLATE)
    revised=copy.deepcopy(m);revised['attributeValueContext']=c;(output/'public/data/manifest.json').write_bytes(encode(revised));actual=effective(output);change=delta(old,actual,c,new_rows);digest=hashlib.sha256(encode(actual)).hexdigest()
    revised['preferredPort']=port;revised['templateHashes'][TEMPLATE]=sha(templates/TEMPLATE);revised['sourceHashes']['inherited_typed_inline_attribute_DN']=sha(proof_path);revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(c)).hexdigest());revised['inheritedTypedInlineDNRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(proof_path),implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(proof_path),effective=digest,template=sha(templates/TEMPLATE),implementation=sha(__file__),port=port))).hexdigest()[:20];(output/'public/data/manifest.json').write_bytes(encode(revised));index=output/'public/index.html';index.write_text(index.read_text(encoding='utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    folder=output/EVIDENCE;folder.mkdir();(folder/'provider-inventory.json').write_bytes(encode(provider_from(proof,proof_path)));(folder/'current-effective.json').write_bytes(encode(actual));shutil.copy2(proof_path,folder/'native-proof.json')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('native source/schema gate failed')
    for name,h in inventory.items():
        if name.startswith(('public/data/','annotations/'))and name!='public/data/manifest.json'and sha(output/name)!=h:raise ValueError('source payload or annotations changed')
    if prior.prior.base.artifact_inventory(parent)!=inventory:raise ValueError('parent changed')
    audit=dict(mode=MODE,status='source_and_complete_reader_passed_browser_pending',parent=str(parent),parent_file_hashes=inventory,proof_path=str(proof_path),proof_sha256=sha(proof_path),bundle_id=revised['bundleId'],template_sha256=sha(templates/TEMPLATE),delta=change,new_rows=new_rows,source_preflight=preflight,old_annotations_preserved=True,human_accepted=False);audit['output_hashes']=prior.prior.base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit));return audit


def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);path=Path(a['proof_path']);proof=verify_output(path.parent);m=load(output/'public/data/manifest.json')
    if a['mode']!=MODE or m['bundleId']!=a['bundle_id']or sha(path)!=a['proof_sha256']or sha(output/TEMPLATE)!=a['template_sha256']or sha(__file__)!=m['inheritedTypedInlineDNRefresh']['implementation_sha256']or prior.prior.base.artifact_inventory(parent)!=a['parent_file_hashes']or{n:h for n,h in prior.prior.base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']or context_from(parent,proof,path)!=m['attributeValueContext']:raise ValueError('viewer source/context/artifact changed')
    if delta(effective(parent),effective(output),m['attributeValueContext'],a['new_rows'])!=a['delta']or encode(provider_from(proof,path))!=(output/EVIDENCE/'provider-inventory.json').read_bytes():raise ValueError('actual value or complete provider inheritance differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=a['bundle_id'],delta=a['delta'],human_accepted=False)
