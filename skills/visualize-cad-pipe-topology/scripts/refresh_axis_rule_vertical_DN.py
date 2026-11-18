"""Adopt independently checked native DN rules without changing prior values."""
import copy,hashlib,json,shutil,subprocess
from pathlib import Path
import refresh_anchored_terminal_branches as prior
from reapply_axis_main_T_DN import verify_output,MODE as NATIVE_MODE
sha,load,encode=prior.sha,prior.load,prior.encode
MODE='native_axis_rule_vertical_DN_viewer_v1'
AUDIT='native-axis-rule-DN-refresh.json';EVIDENCE='axis-rule-DN-refresh'
FIELDS={'axis_rule_vertical_DN_segment_count','axis_rule_vertical_DN_segments_json','axis_rule_vertical_DN_source_sha256'}
TEMPLATES=('public/axis-rule-vertical-DN.js','public/edge-attributes-axis-rule.js')
key=lambda r:(r['edge_id'],r['path_index'],r['segment_index'])

def effective(bundle):
    bundle=Path(bundle);facade='edge-attributes-axis-rule.js' if (bundle/'public/edge-attributes-axis-rule.js').exists() else 'edge-attributes-nested-direct-axis.js'
    js="import fs from'node:fs';import{pathToFileURL}from'node:url';const p=process.argv[1],m=JSON.parse(fs.readFileSync(p+'/public/data/manifest.json')),g=JSON.parse(fs.readFileSync(p+'/public/data/graph.json')),a=await import(pathToFileURL(p+'/public/"+facade+"'));console.log(JSON.stringify(g.edges.map(e=>({edge_id:e.edge_id,values:a.crossViewAttributeCsvValues(e,m.attributeValueContext)}))))"
    result=subprocess.run(['node','--input-type=module','-e',js,str(bundle)],capture_output=True,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('complete actual attribute reader failed: '+result.stderr)
    return json.loads(result.stdout)

def context_from(parent,proof,path):
    parent=Path(parent);m=load(parent/'public/data/manifest.json');context=copy.deepcopy(m['attributeValueContext'])
    if (proof['mode']!=NATIVE_MODE or proof['graph_mutated'] is not False or proof['physical_lengths_assigned']!=0 or proof['horizontal_values_assigned']!=0
        or proof['whole_branch_annotation_barriers_checked'] is not True or proof['branch_DN_never_used_as_main_seed'] is not True or proof['human_accepted'] is not False or 'axis_rule_vertical_DN' in context):raise ValueError('invalid independently checked rule adoption contract')
    if any(sha(v['path'])!=v['sha256'] for v in proof['inputs'].values()) or sha(parent/'public/data/manifest.json')!=proof['inputs']['parent_viewer_manifest']['sha256']:raise ValueError('native parent changed')
    native=load(proof['inputs']['axis_graph']['path']);rendered=load(parent/'public/data/graph.json');by={e['edge_id']:e for e in native['edges']};view={e['edge_id']:e for e in rendered['edges']};source=proof['inputs']['axis_source']['sha256'];rh=sha(parent/'public/data/graph.json')
    if source!=m['sourceHashes']['main_dxf'] or rh!=context['current_rendered_graph_sha256'] or by.keys()!=view.keys():raise ValueError('native/rendered source identity differs')
    occupied=set()
    for name in ('axis_vertical_segment_DN','omission_vertical_DN','continuous_axis_vertical_DN','nested_pair_axis_vertical_DN','nested_direct_axis_vertical_DN'):occupied.update(key(r) for r in context[name]['records'])
    occupied.update(key(r) for r in context['graph_first_extensions']['vertical_records'])
    for e in rendered['edges']:occupied.update((e['edge_id'],r['path_index'],r['segment_index']) for r in e.get('axis_riser_attributes',[]))
    if len(occupied)!=proof['counts']['previous_known']:raise ValueError('old complete vertical population differs')
    records=[];new=set()
    for r in proof['records']:
        k=key(r);e=by[k[0]];shown=view[k[0]];rule=r['connection_rule'];choices=r['candidate_evidence']
        if (k in occupied or k in new or rule!='original_native_main_T_and_unlabelled_branch_continuity' or not choices
            or any(e.get(f)!=shown.get(f) for f in ('edge_id','system','start_node_id','end_node_id','attribute_paths'))
            or e['attribute_paths'][k[1]][k[2]:k[2]+2]!=r['scope_points'] or e['system']!=r['system'] or r['whole_edge_DN_assigned'] is not False or r['physical_length_mm'] is not None):raise ValueError('rule target no longer original unknown scope')
        observations=[];domains=[];Ts=[];lines=[]
        for choice in choices:
            seed=choice['seed'];guard=choice['annotation_guard']
            if seed['system']!=r['system'] or seed['nominal_mm']!=r['nominal_mm'] or guard['other_in_scope_DN_annotations'] or guard['F_crossings'] or choice['main']['branch_DN_used_as_main_seed'] is not False or choice['main']['physical_length_mm'] is not None:raise ValueError('main caption/whole-branch barrier differs')
            if choice['main_LINE']!=choice['main']['source_line_handle'] or choice['main_LINE']!=seed['source_line_handle']:raise ValueError('source main identity differs')
            observations.extend(seed['observations']);domains.append({f:seed[f] for f in ('edge_id','path_index','segment_index','system','nominal_mm')});lines.append(choice['main_LINE']);Ts.extend(j['node_id'] for j in choice['root_T']['junctions'])
        records.append(dict(edge_id=k[0],path_index=k[1],segment_index=k[2],system=r['system'],nominal_mm=r['nominal_mm'],scope_points=copy.deepcopy(r['scope_points']),axis_source_sha256=source,
            seed_text_handles=sorted({o['source_text']['handle'] for o in observations}),seed_domains=domains,main_line_handles=sorted(set(lines)),root_T_nodes=sorted(set(Ts)),source_rules=[rule],whole_branch_annotation_barriers_checked=True,
            physical_length_mm=None,whole_edge_DN_assigned=False,related_HIL_confirmation_inherited=False,human_accepted=False));new.add(k)
    if len(new)!=proof['counts']['new_known'] or len(occupied|new)!=proof['counts']['current_known']:raise ValueError('new rule domain conservation differs')
    context['axis_rule_vertical_DN']=dict(mode='qualified_axis_rule_vertical_DN_context_v1',records=records,count=len(records),source_bindings=dict(native_source=source,native_graph=proof['inputs']['axis_graph']['sha256'],native_proof=sha(path),rendered_graph=rh),
        old_vertical_domains=len(occupied),all_current_vertical_domains=len(occupied|new),remaining_unknown=proof['counts']['remaining_unknown'],raw_graph_changed=False,physical_lengths_assigned=0,whole_edge_DN_assigned=0,human_accepted=False)
    return context

def delta(before,after,context):
    old={r['edge_id']:r['values'] for r in before};new={r['edge_id']:r['values'] for r in after};rows=context['axis_rule_vertical_DN']['records'];changed=[]
    if old.keys()!=new.keys():raise ValueError('edge population changed')
    for eid,values in old.items():
        actual=new[eid];selected=[r for r in rows if r['edge_id']==eid]
        if {k:v for k,v in actual.items() if k not in FIELDS}!=values:raise ValueError('historical effective value changed '+eid)
        if selected:
            if (actual.get('axis_rule_vertical_DN_segment_count')!=len(selected) or json.loads(actual.get('axis_rule_vertical_DN_segments_json','null'))!=selected
                or actual.get('axis_rule_vertical_DN_source_sha256')!=context['axis_rule_vertical_DN']['source_bindings']['native_source']):raise ValueError('paired context not adopted '+eid)
            changed.append(eid)
        elif actual!=values:raise ValueError('unrelated effective value changed '+eid)
    return dict(changed_edges=changed,new_vertical_domains=len(rows),all_old_effective_values_exact=True,new_whole_edge_DN=0,new_physical_lengths=0)


def provider_from(proof,path):
    provider=copy.deepcopy(load(proof['inputs']['parent_provider']['path']))
    if provider['counts']['all_current_vertical_DN_domains']!=proof['counts']['previous_known']:raise ValueError('complete prior provider count differs')
    provider['history_counts_before_axis_rule_axis_DN']=dict(counts=copy.deepcopy(provider['counts']),legacy_top_level_vertical_domains=provider.get('all_current_vertical_DN_domains'))
    provider['counts']['all_current_vertical_DN_domains']=proof['counts']['current_known']
    provider['all_current_vertical_DN_domains']=proof['counts']['current_known']
    provider['axis_rule_vertical_DN']=dict(native_proof_sha256=sha(path),new_domains=len(proof['records']),human_accepted=False)
    return provider


def refresh(parent,output,proof_path,templates,port):
    parent,output,proof_path,templates=map(lambda p:Path(p).resolve(),(parent,output,proof_path,templates))
    if output.exists() or parent in output.parents or output==parent:raise ValueError('fresh external viewer output required')
    proof=verify_output(proof_path.parent);inventory=prior.base.artifact_inventory(parent);context=context_from(parent,proof,proof_path);old=effective(parent);m=load(parent/'public/data/manifest.json')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in TEMPLATES:shutil.copy2(templates/name,output/name)
    app=output/'public/app.js';s=app.read_text(encoding='utf-8');old_import="from './edge-attributes-nested-direct-axis.js';"
    if s.count(old_import)!=1:raise ValueError('current complete reader entry differs')
    app.write_text(s.replace(old_import,"from './edge-attributes-axis-rule.js';"),encoding='utf-8')
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode(revised));actual=effective(output);change=delta(old,actual,context);digest=hashlib.sha256(encode(actual)).hexdigest()
    revised['preferredPort']=port;revised['templateHashes'].update({n:sha(templates/n) for n in TEMPLATES});revised['templateHashes']['public/app.js']=sha(app);revised['sourceHashes']['native_axis_rule_vertical_DN']=sha(proof_path)
    revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(context)).hexdigest());revised['nativeAxisRuleAxisDNRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(proof_path),implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(proof_path),effective=digest,templates={n:sha(templates/n) for n in TEMPLATES},implementation=sha(__file__),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode(revised));index=output/'public/index.html';index.write_text(index.read_text(encoding='utf-8').replace(m['bundleId'],revised['bundleId']),encoding='utf-8')
    provider=provider_from(proof,proof_path)
    evidence=output/EVIDENCE;evidence.mkdir();(evidence/'provider-inventory.json').write_bytes(encode(provider));(evidence/'current-effective.json').write_bytes(encode(actual));shutil.copy2(proof_path,evidence/'native-proof.json')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed' or quality['machine_status']!='PASS':raise ValueError('native source/schema gate failed')
    for n,h in inventory.items():
        if n.startswith(('public/data/','annotations/')) and n!='public/data/manifest.json' and sha(output/n)!=h:raise ValueError('source payload or annotation changed')
    if prior.base.artifact_inventory(parent)!=inventory:raise ValueError('parent changed')
    audit=dict(mode=MODE,status='independent_native_and_actual_complete_reader_passed_browser_pending',parent=str(parent),parent_file_hashes=inventory,proof_path=str(proof_path),proof_sha256=sha(proof_path),bundle_id=revised['bundleId'],templates={n:sha(templates/n) for n in TEMPLATES},delta=change,source_preflight=preflight,parent_native_replay_performed=False,new_axis_rule_native_replay_performed=True,old_annotations_preserved=True,human_accepted=False)
    audit['output_hashes']=prior.base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit));return audit

def verify(output):
    output=Path(output);audit=load(output/AUDIT);parent=Path(audit['parent']);path=Path(audit['proof_path']);proof=verify_output(path.parent);m=load(output/'public/data/manifest.json')
    if (audit['mode']!=MODE or audit['bundle_id']!=m['bundleId'] or sha(path)!=audit['proof_sha256'] or m['nativeAxisRuleAxisDNRefresh']['implementation_sha256']!=sha(__file__)
        or prior.base.artifact_inventory(parent)!=audit['parent_file_hashes'] or {n:h for n,h in prior.base.artifact_inventory(output).items() if n!=AUDIT}!=audit['output_hashes'] or context_from(parent,proof,path)!=m['attributeValueContext']):raise ValueError('viewer source, context or artifact changed')
    if delta(effective(parent),effective(output),m['attributeValueContext'])!=audit['delta']:raise ValueError('actual paired reader delta differs')
    provider=provider_from(proof,path)
    if encode(provider)!=(output/EVIDENCE/'provider-inventory.json').read_bytes():raise ValueError('provider inheritance changed')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=audit['delta'],human_accepted=False)
