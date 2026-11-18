"""Publish native member paths; keep metrics and review history separately owned."""
import argparse, copy, hashlib, json, os, re, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
for name in ('build-cad-pipe-topology', 'orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]/name/'scripts'))
from confirm_crossview_paths import load, sha, encode
from reconstruct_plan_member_contact_context import verify_output as native_verify, MODE as NATIVE_MODE
from rebuild_member_external_routes import inherit
from refresh_reviewed_ring_partition_DN import effective
from refresh_candidate_ring_DN import encode_manifest
import refresh_attribute_templates as base

MODE='qualified_plan_member_contact_viewer_v1'
CONTEXT='plan_member_contact_routes'
FOLDER='plan-member-contact-refresh'
AUDIT=FOLDER+'.json'
FIELDS=['plan_member_contact_mapping_id','plan_member_contact_plan_path','plan_member_contact_evidence_json']

def require(value,message):
    if not value: raise ValueError(message)

def canonical(value):
    # Native readers retain tuples; JSON/Node represents those exact paths as
    # arrays. Normalize the transport boundary, retaining every evidence field.
    return json.loads(encode(value))

def replay_owners(spec, folder):
    """Run the complete original owners in their own immutable compatible roles."""
    roles=spec['parent_owners']
    require(set(roles)=={'current_provider','alias_bridges'},'both complete native parent roles required')
    def run(item):
        name,role=item; stage=Path(role['snapshot']['path']).parent; snap=load(role['snapshot']['path']); root=stage/'skills'
        expected={'current_provider':'visualize-cad-pipe-topology/scripts/refresh_inherited_branch_attribute_entries.py','alias_bridges':'build-cad-pipe-topology/scripts/rebuild_alias_member_inline_bridges.py'}
        require(role['entry']==expected[name],'complete original parent owner required')
        require(sha(role['snapshot']['path'])==role['snapshot']['sha256'],'parent snapshot changed')
        require(all(sha(root/n)==h for n,h in snap['files'].items()),'original parent runtime changed')
        entry=root/role['entry']; require(sha(entry)==role['entry_sha256'],'parent entry changed')
        command=[sys.executable,'-X','utf8','-B',str(entry),'--verify-output',role['output']]
        dest=folder/name;dest.mkdir(parents=True); (dest/'binding.json').write_bytes(encode(role))
        started=time.monotonic()
        with (dest/'stdout.log').open('w',encoding='utf8')as so,(dest/'stderr.log').open('w',encoding='utf8')as se:
            p=subprocess.Popen(command,stdout=so,stderr=se,cwd=spec['cwd'],env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',CAD_NATIVE_WORKERS='8'),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (dest/'process.json').write_bytes(encode(dict(pid=p.pid,launch_ns=time.time_ns(),command=command)))
            code=p.wait()
        result=dict(exit_code=code,elapsed_seconds=time.monotonic()-started,binding_sha256=sha(dest/'binding.json'),
            snapshot_after_exact=all(sha(root/n)==h for n,h in snap['files'].items()),stdout_sha256=sha(dest/'stdout.log'),stderr_sha256=sha(dest/'stderr.log'))
        (dest/'result.json').write_bytes(encode(result));require(code==0 and result['snapshot_after_exact'],'complete original parent replay failed: '+name)
        return name,result
    with ThreadPoolExecutor(max_workers=2)as pool:return dict(pool.map(run,roles.items()))

def context_from(parent,proof,path,provider):
    m=load(Path(parent)/'public/data/manifest.json');prior=m['attributeValueContext'];g=load(Path(parent)/'public/data/graph.json');edges={e['edge_id']:e for e in g['edges']}
    require(proof['mode']==NATIVE_MODE and proof['view_role']=='floor_plan_orthographic_XY' and proof['axis_3D_reader_unchanged']is True
        and proof['original_source_graphs_mutated']is False and proof['original_component_owners_mutated']is False
        and proof['DN_values_assigned']==proof['physical_lengths_assigned']==0 and proof['current_mapping_publication_performed']is False,'unsupported source context')
    require(CONTEXT not in prior and proof['inputs']['provider']['sha256']==sha(provider),'actual current provider differs')
    require(prior['source_graph_sha256']==m['sourceHashes']['graph'] and proof['inputs']['axis_source']['sha256']==m['sourceHashes']['main_dxf'],'rendered/native source differs')
    for r in proof['records']:
        e=edges[r['axis_edge_id']]
        require(r['kind']=='member_to_ordinary_external_route' and e['system']==r['system'] and [e['start_node_id'],e['end_node_id']]==r['axis_nodes']
            and e['attribute_paths']==r['axis_attribute_paths'] and e['floor_start']==e['floor_end']==r['floor']
            and r['whole_edge_DN_mm']is None and r['whole_edge_physical_length_mm']is None
            and r['physical_values_assigned']==0 and r['attribute_adoption_allowed']is False and r['human_accepted']is False
            and r['original_source_Z_preserved']is True and r['axis_component_reader_3D_unchanged']is True,'native/rendered route differs')
    require(len({r['axis_edge_id']for r in proof['records']})==len(proof['records']),'competing member writer')
    out=copy.deepcopy(prior);out[CONTEXT]=dict(mode=MODE,records=copy.deepcopy(proof['records']),count=len(proof['records']),
        source_bindings=dict(native_proof=sha(path),parent_provider=sha(provider),axis_source=proof['inputs']['axis_source']['sha256'],
            plan_source=proof['inputs']['plan_source']['sha256'],native_axis_graph=proof['inputs']['axis_graph']['sha256'],plan_graph=proof['inputs']['plan_graph']['sha256'],rendered_graph=sha(Path(parent)/'public/data/graph.json')),
        physical_values_assigned=0,axis_3D_reader_unchanged=True,human_accepted=False)
    return json.loads(encode(out))

def delta(before,after,records):
    old={r['edge_id']:r['values']for r in before};new={r['edge_id']:r['values']for r in after};target={r['axis_edge_id']:canonical(r)for r in records}
    require(old.keys()==new.keys(),'edge census changed')
    for eid,v in old.items():
        require(all(new[eid].get(k)==value for k,value in v.items()),'old attribute value changed '+eid)
        extra={k:x for k,x in new[eid].items()if k not in v}
        if eid in target:
            require(set(extra)==set(FIELDS)and extra[FIELDS[0]]==target[eid]['mapping_id']and json.loads(extra[FIELDS[2]])==target[eid],'actual mapping reader rejected native proof')
        else:require(not extra,'mapping escaped qualified scope')
    return dict(new_correspondences=sorted(target),old_attribute_values_exact=True,new_DN_values=0,new_length_values=0)

def migrate_review(parent,output,old_manifest,new_manifest,affected):
    """Carry exact stable-edge manual values; semantic confirmations become history."""
    sys.path.insert(0,str(Path(output)))
    from hil_server import identity, now
    old_id,new_id=identity(old_manifest),identity(new_manifest);old=Path(parent)/'annotations'/old_id/'review.json'
    if not old.exists():return dict(old_dataset=old_id,new_dataset=new_id,migrated=False)
    source=load(old);out=copy.deepcopy(source);out['datasetId']=new_id;out['revision']+=1
    if out.get('confirmation'):
        out.setdefault('historicalConfirmations',[]).append(dict(out['confirmation'],invalidatedAt=now(),reason='native_member_correspondence_changed'))
    out['confirmation']=None
    for eid in affected:
        edit=out.get('edgeEdits',{}).get(eid,{})
        if edit.get('reviewed'):
            prior=copy.deepcopy(edit);edit.pop('reviewed')
            out.setdefault('edgeEditHistory',[]).append(dict(edgeId=eid,action='source_mapping_changed',before=prior,after=copy.deepcopy(edit),at=now()))
    out['migration']=dict(fromDatasetId=old_id,sourceReviewSha256=sha(old),reason='same_native_edge_identity_new_correspondence',manual_lengths_preserved=True,human_confirmation_inherited=False)
    out['updatedAt']=now();dest=Path(output)/'annotations'/new_id;dest.mkdir(parents=True,exist_ok=True);(dest/'review.json').write_bytes(encode(out))
    return dict(old_dataset=old_id,new_dataset=new_id,migrated=True,manual_lengths_preserved=True,source_review_sha256=sha(old))

def refresh(spec_path,output):
    spec_path=Path(spec_path).resolve();spec=load(spec_path);parent=Path(spec['parent']).resolve();output=Path(output).resolve();require(not output.exists(),'fresh member viewer required')
    provider=Path(spec['provider']);path=Path(spec['native_proof']);proof=canonical(native_verify(path.parent))
    m=load(parent/'public/data/manifest.json');prior=effective(parent);context=context_from(parent,proof,path,provider)
    original_parent=Path(spec['parent_owners']['current_provider']['output'])
    require(sha(original_parent/'inherited-branch-entries-refresh/provider-inventory.json')==sha(provider)
        and load(original_parent/'public/data/manifest.json')['attributeValueContext']==m['attributeValueContext'],'current UI is not the replayed provider context')
    require(Path(spec['parent_owners']['alias_bridges']['output']).resolve()==path_from(proof,'member_bridges').parent,'alias owner belongs to another source')
    execution=output.parent/(output.name+'-parent-execution');require(not execution.exists(),'fresh parent execution required');execution.mkdir(parents=True)
    parent_results=replay_owners(spec,execution)
    # Recheck all source input hashes after the complete parent executions.
    require(all(sha(v['path'])==v['sha256']for v in proof['inputs'].values()),'source input changed during parent replay')
    before=base.artifact_inventory(parent);original=load(provider)
    revised_provider,local=inherit(original,proof['records'],load(path_from(proof,'member_bridges')),load(path_from(proof,'plan_graph')))
    require(len(local['edges'])==len(load(path_from(proof,'member_bridges'))['member_local_graph']['edges'])+len(proof['records']),'member edges were not rebuilt')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    templates=Path(__file__).resolve().parents[1]/'assets/viewer/public'
    for n in ('plan-member-contact-routes.js','edge-attributes-plan-member-contact.js'):shutil.copy2(templates/n,output/'public'/n)
    app=output/'public/app.js';s=app.read_text('utf8');imports=re.findall(r"from\s*['\"]\./(edge-attributes[A-Za-z0-9_.-]*\.js)['\"]",s);require(len(imports)==1,'one current facade required')
    facade=output/'public/edge-attributes-plan-member-contact.js';facade.write_text(facade.read_text('utf8').replace('./edge-attributes-inherited-entries.js','./'+imports[0]),encoding='utf8')
    s=s.replace('./'+imports[0],'./edge-attributes-plan-member-contact.js')
    # Manual review fields form part of the historical CSV prefix.
    needle='...edgeAttributeCsvFields,...reviewCsvFields]';require(s.count(needle)==1,'current review CSV prefix required')
    s="import {planMemberContactCsvFields} from './plan-member-contact-routes.js';\n"+s.replace(needle,'...edgeAttributeCsvFields,...reviewCsvFields,...planMemberContactCsvFields]')
    app.write_text(s,encoding='utf8');revised=copy.deepcopy(m);revised['attributeValueContext']=context;revised['preferredPort']=spec['port']
    (output/'public/data/manifest.json').write_bytes(encode_manifest(revised));actual=effective(output);change=delta(prior,actual,proof['records'])
    modules=['public/app.js','public/plan-member-contact-routes.js','public/edge-attributes-plan-member-contact.js'];hashes={n:sha(output/n)for n in modules}
    revised['templateHashes'].update(hashes);revised['sourceHashes'][CONTEXT]=sha(path)
    revised['reviewContentHashes'].update(effective_edge_attributes=hashlib.sha256(encode(actual)).hexdigest(),attribute_value_context=hashlib.sha256(encode(context)).hexdigest())
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(path),implementation=sha(__file__),templates=hashes,port=spec['port']))).hexdigest()[:20]
    revised['planMemberContactRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],human_confirmation_inherited=False)
    (output/'public/data/manifest.json').write_bytes(encode_manifest(revised));index=output/'public/index.html';index.write_text(index.read_text('utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    migration=migrate_review(parent,output,m,revised,{r['axis_edge_id']for r in proof['records']})
    from hil_server import identity
    q=load(output/'public/data/edge-review-queue.json');removed={r['axis_edge_id']for r in proof['records']};q['datasetId']=identity(revised)
    # Still unknown whole-edge lengths remain available in the review editor.
    for item in q['items']:
        if item['edgeId']in removed:item.update(label='长度/属性',reasons=['路径已对应，混合边的实际接管长度仍未知'],sourceScope='known_member_external_correspondence_unknown_length')
    (output/'public/data/edge-review-queue.json').write_bytes(encode(q))
    folder=output/FOLDER;folder.mkdir();shutil.copy2(path,folder/'native-proof.json');(folder/'provider-inventory.json').write_bytes(encode(revised_provider));(folder/'member-local-graph.json').write_bytes(encode(local));(folder/'current-effective.json').write_bytes(encode(actual));(folder/'parent-gates.json').write_bytes(encode(parent_results))
    require(base.artifact_inventory(parent)==before,'parent changed during adoption; retry from current review snapshot')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n not in ('public/data/manifest.json','public/data/edge-review-queue.json'):require(sha(output/n)==h,'old data or review history changed')
    audit=dict(mode=MODE,parent=str(parent),parent_files=before,native_proof=str(path),native_proof_sha256=sha(path),spec=dict(path=str(spec_path),sha256=sha(spec_path)),
        delta=change,bundle_id=revised['bundleId'],parent_execution=str(execution),review_migration=migration,all_old_graph_and_components_exact=True,
        source_context_independently_replayed=True,manual_lengths_not_source_attributes=True,human_accepted=False,whole_goal_complete=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit));return audit

def path_from(proof,key):return Path(proof['inputs'][key]['path'])

def verify(output):
    output=Path(output).resolve();audit=load(output/AUDIT);spec=load(audit['spec']['path']);parent=Path(audit['parent']);path=Path(audit['native_proof'])
    require(audit['mode']==MODE and sha(audit['spec']['path'])==audit['spec']['sha256']and sha(path)==audit['native_proof_sha256'],'publication spec or native proof changed')
    proof=canonical(native_verify(path.parent));m=load(output/'public/data/manifest.json');context=context_from(parent,proof,path,spec['provider'])
    require(context==m['attributeValueContext'],'published member source context differs')
    def immutable(items):return {n:h for n,h in items.items()if not n.startswith(('annotations/','startup-logs/'))}
    require(immutable(base.artifact_inventory(parent))==immutable(audit['parent_files']),'original immutable viewer changed')
    require({n:h for n,h in immutable(base.artifact_inventory(output)).items()if n!=AUDIT}==immutable(audit['output_hashes']),'published immutable viewer changed')
    check=output.parent/(output.name+'-independent-parent-execution');require(not check.exists(),'fresh independent parent execution required');check.mkdir()
    replay_owners(spec,check)
    expected,local=inherit(load(spec['provider']),proof['records'],load(path_from(proof,'member_bridges')),load(path_from(proof,'plan_graph')))
    require(load(output/FOLDER/'provider-inventory.json')==expected and load(output/FOLDER/'member-local-graph.json')==local,'published native member graph or provider differs')
    require(delta(effective(parent),effective(output),proof['records'])==audit['delta'],'actual published mapping delta differs')
    return dict(status='independent_native_parents_source_and_actual_reader_passed',bundle_id=m['bundleId'],delta=audit['delta'],human_accepted=False,whole_goal_complete=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest');p.add_argument('--output');p.add_argument('--verify-output');a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:result=verify(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('manifest and fresh output required')
            result=refresh(a.manifest,a.output)
    print(json.dumps(dict(status=result.get('status','native_member_routes_published_browser_pending'),bundle_id=result['bundle_id'],delta=result['delta']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
