"""Adopt multi-LINE native main/T evidence in the existing vertical context."""
import copy,hashlib,json,shutil
from pathlib import Path
import refresh_plan_crossover_centrelines as prior
from refresh_typed_inline_attribute_DN import delta
from reapply_multiline_main_T_DN import verify_output,MODE as NATIVE_MODE
from native_multiline_main_T_DN import RULE
sha,load,encode,effective=prior.sha,prior.load,prior.encode,prior.effective
MODE='native_multiline_main_T_DN_viewer_v1'
AUDIT='multiline-main-T-DN-refresh.json';EVIDENCE='multiline-main-T-DN-refresh'
TEMPLATE='public/axis-rule-vertical-DN.js'
key=lambda r:(r['edge_id'],r['path_index'],r['segment_index'])

def context_from(parent,proof,path):
    parent=Path(parent);m=load(parent/'public/data/manifest.json');c=copy.deepcopy(m['attributeValueContext']);root=c['axis_rule_vertical_DN'];edges={e['edge_id']:e for e in load(parent/'public/data/graph.json')['edges']}
    if proof['mode']!=NATIVE_MODE or any(proof[k]!=0 for k in('physical_lengths_assigned','horizontal_values_assigned'))or any(proof[k]is not False for k in('graph_mutated','components_reassigned','human_accepted'))or any(proof.get(k)is not True for k in('whole_branch_annotation_barriers_checked','source_roots_from_native_witnesses','branch_DN_never_used_as_main_seed','whole_root_main_annotation_extents_checked','conflicting_source_connected_seeds_blocked')):raise ValueError('native main source contract differs')
    if any(sha(v['path'])!=v['sha256']for v in proof['inputs'].values())or sha(parent/'public/data/manifest.json')!=proof['inputs']['parent_viewer_manifest']['sha256']:raise ValueError('current source or parent changed')
    source=proof['inputs']['axis_source']['sha256']
    if root['all_current_vertical_domains']!=proof['counts']['previous_known']or root['source_bindings']['native_source']!=source or root['source_bindings']['native_graph']!=proof['inputs']['axis_graph']['sha256']or c['current_rendered_graph_sha256']!=sha(parent/'public/data/graph.json'):raise ValueError('source domain identity differs')
    oldkeys={key(r)for r in root['records']};new=[]
    for r in proof['records']:
        k=key(r);e=edges[k[0]];choices=r['candidate_evidence']
        if k in oldkeys or r['connection_rule']!=RULE or not choices or r['system']!=e['system']or e['attribute_paths'][k[1]][k[2]:k[2]+2]!=r['scope_points']or r['physical_length_mm']is not None or r['whole_edge_DN_assigned']is not False:raise ValueError('original unknown vertical scope differs')
        observations=[];domains=[];junctions=[];chains=[]
        for choice in choices:
            seed=choice['seed'];guard=choice['annotation_guard']
            if seed['system']!=r['system']or seed['nominal_mm']!=r['nominal_mm']or guard['other_in_scope_DN_annotations']or guard['F_crossings']or not choice.get('root_through_main_full_source_extents'):raise ValueError('source main caption or branch barrier differs')
            observations+=seed['observations'];domains.append({f:seed[f]for f in('edge_id','path_index','segment_index','system','nominal_mm')});junctions += [j['node_id']for p in choice['junctions']for j in p['junctions']]
            for part in choice['main_parts']:
                scopes=part['scopes'];native=part['source_continuity']['native_chain']
                if len(scopes)!=len(native):raise ValueError('native corridor source chain differs')
                chains += [dict(edge_id=s['edge_id'],path_index=s['path_index'],segment_index=s['segment_index'],root_handle=n['root_handle'],child_handle=n['child_handle'])for s,n in zip(scopes,native)]
        if not chains or not junctions:raise ValueError('complete native main and T lineage required')
        new.append(dict(edge_id=k[0],path_index=k[1],segment_index=k[2],scope_points=r['scope_points'],system=r['system'],nominal_mm=r['nominal_mm'],axis_source_sha256=source,seed_text_handles=sorted({o['source_text']['handle']for o in observations}),seed_domains=domains,main_line_handles=sorted({s['child_handle']for s in chains}),root_T_nodes=sorted(set(junctions)),main_source_chains=chains,source_rules=[RULE],whole_branch_annotation_barriers_checked=True,multiline_main_source_chain_replayed=True,source_roots_from_native_witnesses=True,branch_DN_used_as_main_seed=False,physical_length_mm=None,whole_edge_DN_assigned=False,related_HIL_confirmation_inherited=False,human_accepted=False))
    if len(new)!=proof['counts']['new_known']or len({key(r)for r in new})!=len(new):raise ValueError('complete new population differs')
    root['history_before_multiline_main_T_DN']={k:copy.deepcopy(root[k])for k in root if k!='records'};root['records'].extend(new);root.update(count=len(root['records']),all_current_vertical_domains=proof['counts']['current_known'],remaining_unknown=proof['counts']['remaining_unknown']);root['source_bindings']['native_proof']=sha(path)
    for row in new:row.update(root_main_annotation_extents_checked=True,conflicting_source_connected_seeds_blocked=True)
    return json.loads(encode(c))

def provider_from(proof,path):
    p=copy.deepcopy(load(proof['inputs']['parent_provider']['path']))
    if p['counts']['all_current_vertical_DN_domains']!=proof['counts']['previous_known']:raise ValueError('provider parent differs')
    p['history_before_multiline_main_T_DN']=dict(counts=copy.deepcopy(p['counts']),legacy_top_level_vertical_domains=p.get('all_current_vertical_DN_domains'));p['counts']['all_current_vertical_DN_domains']=proof['counts']['current_known'];p['all_current_vertical_DN_domains']=proof['counts']['current_known'];p['multiline_main_T_DN']=dict(native_proof_sha256=sha(path),new_domains=len(proof['records']),human_accepted=False);return p


def refresh(parent,output,proof_path,templates,port):
    parent,output,proof_path,templates=map(lambda p:Path(p).resolve(),(parent,output,proof_path,templates))
    if output.exists()or parent in output.parents or output==parent:raise ValueError('fresh external output required')
    proof=verify_output(proof_path.parent);inventory=prior.prior.base.artifact_inventory(parent);c=context_from(parent,proof,proof_path);old=effective(parent);m=load(parent/'public/data/manifest.json');previous=len(m['attributeValueContext']['axis_rule_vertical_DN']['records']);new_rows=c['axis_rule_vertical_DN']['records'][previous:]
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.copy2(templates/TEMPLATE,output/TEMPLATE)
    revised=copy.deepcopy(m);revised['attributeValueContext']=c;(output/'public/data/manifest.json').write_bytes(encode(revised));actual=effective(output);change=delta(old,actual,c,new_rows);digest=hashlib.sha256(encode(actual)).hexdigest()
    revised['preferredPort']=port;revised['templateHashes'][TEMPLATE]=sha(templates/TEMPLATE);revised['sourceHashes']['native_multiline_main_T_DN']=sha(proof_path);revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(c)).hexdigest());revised['nativeMultilineMainTDNRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(proof_path),implementation_sha256=sha(__file__),human_confirmation_inherited=False)
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
    if a['mode']!=MODE or m['bundleId']!=a['bundle_id']or sha(path)!=a['proof_sha256']or sha(output/TEMPLATE)!=a['template_sha256']or sha(__file__)!=m['nativeMultilineMainTDNRefresh']['implementation_sha256']or prior.prior.base.artifact_inventory(parent)!=a['parent_file_hashes']or{n:h for n,h in prior.prior.base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']or context_from(parent,proof,path)!=m['attributeValueContext']:raise ValueError('viewer source/context/artifact changed')
    if delta(effective(parent),effective(output),m['attributeValueContext'],a['new_rows'])!=a['delta']or encode(provider_from(proof,path))!=(output/EVIDENCE/'provider-inventory.json').read_bytes():raise ValueError('actual value or complete provider inheritance differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=a['bundle_id'],delta=a['delta'],human_accepted=False)
