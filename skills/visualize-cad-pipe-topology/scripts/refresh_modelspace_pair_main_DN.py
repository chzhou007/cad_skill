"""Publish inherited direct/paired native source-LINE DN without old-value loss."""
import copy,hashlib,json,shutil,types
from pathlib import Path
import refresh_multiline_main_T_DN as base
import refresh_plan_crossover_centrelines as prior
from refresh_typed_inline_attribute_DN import delta
from reapply_modelspace_pair_main_DN import verify_output,MODE as NATIVE_MODE
sha,load,encode,effective=prior.sha,prior.load,prior.encode,prior.effective
MODE='inherited_modelspace_pair_main_DN_viewer_v1'
AUDIT='modelspace-pair-main-DN-refresh.json';EVIDENCE='modelspace-pair-main-DN-refresh'
TEMPLATE='public/axis-rule-vertical-DN.js'
key=lambda r:(r['edge_id'],r['path_index'],r['segment_index'])

def context_from(parent,proof,path):
    old=load(Path(parent)/'public/data/manifest.json')['attributeValueContext']['axis_rule_vertical_DN'];requalification=proof['existing_main_T_requalification']
    if requalification['status']!='passed'or requalification['old_values_changed']is not False or not requalification['count']or proof['source_local_seed_priority_applied']is not True or proof['seeds']['direct_and_paired_LINE_priority_equal']is not True:raise ValueError('old native main-T and equal LINE-priority replay required')
    builder=types.FunctionType(base.context_from.__code__,dict(base.context_from.__globals__,NATIVE_MODE=NATIVE_MODE),base.context_from.__name__,base.context_from.__defaults__,base.context_from.__closure__);c=builder(parent,proof,path);root=c['axis_rule_vertical_DN'];oldkeys={key(r)for r in old['records']};by={key(r):r for r in proof['records']};declared=[]
    for row in root['records']:
        k=key(row)
        if k in oldkeys:continue
        records=[]
        for choice in by[k]['candidate_evidence']:
            seed=choice['seed']
            for observation in seed['observations']:
                native=observation['native_evidence'];family='native_pair'if native.get('original_pair_geometry_replayed')is True else'native_direct'
                if family=='native_pair'and(native['pair']['DN_or_level_used_to_choose_pipe']is not False or native['pair']['physical_level_or_units_inferred']is not False):raise ValueError('paired source owner cannot use DN or level values')
                records.append(dict(text_handle=observation['source_text']['handle'],source_LINE=seed['source_line_handle'],geometry_family=family,source_LINE_scope_native_replayed=True))
        row.update(seed_annotation_owners=records,same_LINE_seed_priority_checked=True,original_caption_owner_rules_replayed=True);declared.append(':'.join(map(str,k)))
    previous=root.get('modelspace_pair_seed_ownership',{}).get('keys',[]);keys=previous+declared
    if len(set(keys))!=len(keys):raise ValueError('new source owner scope keys overlap prior writer')
    root['modelspace_pair_seed_ownership']=dict(mode='original_native_pair_and_direct_source_LINE_scope_v1',keys=keys,count=len(keys),existing_main_T_requalified=requalification['count'],old_values_changed=False)
    return c

def provider_from(proof,path):
    p=copy.deepcopy(load(proof['inputs']['parent_provider']['path']))
    if p['counts']['all_current_vertical_DN_domains']!=proof['counts']['previous_known']:raise ValueError('provider parent differs')
    p['history_before_modelspace_pair_main_DN']=dict(counts=copy.deepcopy(p['counts']),legacy_top_level_vertical_domains=p.get('all_current_vertical_DN_domains'));p['counts']['all_current_vertical_DN_domains']=proof['counts']['current_known'];p['all_current_vertical_DN_domains']=proof['counts']['current_known'];p['modelspace_pair_main_DN']=dict(native_proof_sha256=sha(path),new_domains=len(proof['records']),old_main_T_requalified=proof['existing_main_T_requalification']['count'],human_accepted=False);return p


def refresh(parent,output,proof_path,templates,port):
    parent,output,proof_path,templates=map(lambda p:Path(p).resolve(),(parent,output,proof_path,templates))
    if output.exists()or parent in output.parents or output==parent:raise ValueError('fresh external output required')
    proof=verify_output(proof_path.parent);inventory=prior.prior.base.artifact_inventory(parent);c=context_from(parent,proof,proof_path);old=effective(parent);m=load(parent/'public/data/manifest.json');previous=len(m['attributeValueContext']['axis_rule_vertical_DN']['records']);new_rows=c['axis_rule_vertical_DN']['records'][previous:]
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.copy2(templates/TEMPLATE,output/TEMPLATE)
    revised=copy.deepcopy(m);revised['attributeValueContext']=c;(output/'public/data/manifest.json').write_bytes(encode(revised));actual=effective(output);change=delta(old,actual,c,new_rows);digest=hashlib.sha256(encode(actual)).hexdigest()
    revised['preferredPort']=port;revised['templateHashes'][TEMPLATE]=sha(templates/TEMPLATE);revised['sourceHashes']['inherited_modelspace_pair_main_DN']=sha(proof_path);revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(c)).hexdigest());revised['nativeModelspacePairMainDNRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(proof_path),implementation_sha256=sha(__file__),human_confirmation_inherited=False)
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
    if a['mode']!=MODE or m['bundleId']!=a['bundle_id']or sha(path)!=a['proof_sha256']or sha(output/TEMPLATE)!=a['template_sha256']or sha(__file__)!=m['nativeModelspacePairMainDNRefresh']['implementation_sha256']or prior.prior.base.artifact_inventory(parent)!=a['parent_file_hashes']or{n:h for n,h in prior.prior.base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']or context_from(parent,proof,path)!=m['attributeValueContext']:raise ValueError('viewer source/context/artifact changed')
    if delta(effective(parent),effective(output),m['attributeValueContext'],a['new_rows'])!=a['delta']or encode(provider_from(proof,path))!=(output/EVIDENCE/'provider-inventory.json').read_bytes():raise ValueError('actual value or complete provider inheritance differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=a['bundle_id'],delta=a['delta'],human_accepted=False)
