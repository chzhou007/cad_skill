"""Adopt native non-node boundary branch contexts without changing any pipe value."""
import argparse,collections,copy,hashlib,json,re,shutil,sys,zipfile
from pathlib import Path
for n in ('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):sys.path.insert(0,str(Path(__file__).resolve().parents[2]/n/'scripts'))
from confirm_crossview_paths import load,sha,encode
from reapply_nonnode_boundary_branches import verify_output,MODE as NATIVE_MODE
from refresh_reviewed_ring_partition_DN import effective
from refresh_candidate_ring_DN import encode_manifest
from refresh_reviewed_fragment_detail import provider_binding
from current_effective_provider import reconcile
import refresh_attribute_templates as base

MODE='native_boundary_branch_current_viewer_v1';AUDIT='nonnode-boundary-branches-refresh.json';FOLDER='nonnode-boundary-branches-refresh'
MODULES=['public/nonnode-boundary-branches.js','public/edge-attributes-nonnode-boundary.js']
FIELDS={'boundary_branch_mapping_id','boundary_branch_plan_edge','boundary_branch_boundary_id','boundary_branch_axis_port','boundary_branch_scope','boundary_branch_evidence_json'}

def context_from(parent,proof,path):
    parent=Path(parent);m=load(parent/'public/data/manifest.json');prior=m['attributeValueContext'];graph=load(parent/'public/data/graph.json')
    if proof['mode']!=NATIVE_MODE or sha(parent/'public/data/manifest.json')!=proof['inputs']['viewer_manifest']['sha256']or 'nonnode_boundary_branches'in prior:raise ValueError('non-node boundary context has another current viewer')
    if any(proof.get(k)is not True for k in ['all_current_plan_boundary_edges_screened','original_boundary_outward_T_path_and_marker_owners_reused']):raise ValueError('native non-node boundary owner replay incomplete')
    if any(proof.get(k)!=0 for k in ['source_boundaries_promoted_to_nodes','other_system_ports_assigned','remote_equipment_identities_assigned','physical_lengths_assigned','whole_axis_DN_assigned','vertical_values_assigned'])or proof['graph_mutated']or proof['old_providers_replaced']or proof['human_accepted']:raise ValueError('unsupported non-node boundary branch physical claim')
    by={e['edge_id']:e for e in graph['edges']}
    for r in proof['records']:
        e=by[r['axis_edge_id']];native=r['native_checks']['iso']['snapshot']['edges'][0]
        if any(e.get(k)!=native.get(k)for k in ['edge_id','system','start_node_id','end_node_id','start_port_id','end_port_id','attribute_paths'])or e.get('floor_start')!=r['floor']or e.get('floor_end')!=r['floor']:raise ValueError('actual rendered non-node boundary branch geometry or ports differ')
    context=copy.deepcopy(prior);context['nonnode_boundary_branches']=dict(mode='qualified_native_boundary_branch_drawing_context_v1',records=copy.deepcopy(proof['records']),count=len(proof['records']),graph_mutated=False,source_boundaries_promoted_to_nodes=0,other_system_ports_assigned=0,remote_equipment_identities_assigned=0,physical_lengths_assigned=0,whole_axis_DN_assigned=0,vertical_values_assigned=0,human_accepted=False,
        source_bindings=dict(raw_axis_graph=prior['source_graph_sha256'],attribute_context_graph=prior['current_rendered_graph_sha256'],rendered_graph=sha(parent/'public/data/graph.json'),native_axis_graph=proof['inputs']['axis_graph']['sha256'],native_proof=sha(path),parent_provider=proof['inputs']['provider']['sha256']))
    return context

def delta(previous,current,proof):
    old={r['edge_id']:r['values']for r in previous};new={r['edge_id']:r['values']for r in current};targets={r['axis_edge_id']:r for r in proof['records']}
    if old.keys()!=new.keys()or len(targets)!=len(proof['records']):raise ValueError('non-node boundary correspondence changed edge population')
    for eid,before in old.items():
        after=new[eid]
        if any(k not in after or after[k]!=v for k,v in before.items()):raise ValueError('an old DN, length, source, vertical or component value changed '+eid)
        extra={k:v for k,v in after.items()if k not in before};r=targets.get(eid)
        if r is None:
            if extra:raise ValueError('non-node boundary context escaped its source scope')
        elif set(extra)!=FIELDS or extra['boundary_branch_mapping_id']!=r['mapping_id']or extra['boundary_branch_plan_edge']!=r['plan_edge_id']or json.loads(extra['boundary_branch_evidence_json'])!=r:raise ValueError('native non-node boundary correspondence not adopted by actual reader')
    return dict(new_drawing_correspondences=len(targets),all_old_pipe_values_exact=True,new_whole_DN_values=0,new_lengths=0,new_vertical_values=0,new_columns=6)

def provider_from(prior,proof,actual,context,path):
    result=copy.deepcopy(prior);rows={r['edge_id']:r for r in result['records']}
    for r in proof['records']:
        row=rows[r['axis_edge_id']]
        if row['has_existing_correspondence']:raise ValueError('old branch writer cannot be replaced')
        row['has_existing_correspondence']=True;row['correspondence_observations'].append(dict(domain='native_nonnode_boundary_drawing_branch_context',floor=r['floor'],grouped_axis_edges=[r['axis_edge_id']],plan_edges=[r['plan_edge_id']],mapping_id=r['mapping_id'],native_proof_sha256=sha(path),whole_axis_physical_length_mm=None,remote_device_identity_assigned=False))
    result['history_before_nonnode_boundary_branches']=dict(counts=copy.deepcopy(prior['counts']),native_proof_sha256=sha(path))
    result['counts'].update(existing_correspondence_edges=sum(r['has_existing_correspondence']for r in result['records']),mixed_edges_without_any_correspondence=sum(r['classification']=='mixed_horizontal_vertical'and not r['has_existing_correspondence']for r in result['records']),new_nonnode_boundary_branchess=len(proof['records']))
    result['nonnode_boundary_branches_observations']=copy.deepcopy(proof['records']);result=reconcile(result,actual,context)
    for key in ['ordinary_junction_mappings','member_domain_observations','all_current_vertical_DN_domains','current_component_inventory']:
        if result[key]!=prior[key]:raise ValueError('non-node boundary context changed unrelated source identities')
    return result

def refresh(parent,output,path,provider,templates,port):
    parent,output,path,provider,templates=map(lambda p:Path(p).resolve(),(parent,output,path,provider,templates))
    if output.exists()or output.with_suffix('.zip').exists():raise FileExistsError(output)
    before=base.artifact_inventory(parent);proof=verify_output(path.parent);binding=provider_binding(parent,provider)
    if binding['provider']!=proof['inputs']['provider']:raise ValueError('current provider differs from native non-node boundary batch')
    context=context_from(parent,proof,path);m=load(parent/'public/data/manifest.json');old=effective(parent);app=(parent/'public/app.js').read_text('utf8');imports=re.findall(r"from\s*['\"]\./(edge-attributes[A-Za-z0-9_.-]*\.js)['\"]",app)
    if len(imports)!=1:raise ValueError('one actual complete parent facade required')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in MODULES:shutil.copy2(templates/name,output/name)
    facade=output/MODULES[1];text=facade.read_text('utf8')
    if text.count('./edge-attributes-capped-branch.js')!=2:raise ValueError('non-node boundary facade template differs')
    facade.write_text(text.replace('./edge-attributes-capped-branch.js','./'+imports[0]),encoding='utf8');(output/'public/app.js').write_text(app.replace('./'+imports[0],'./edge-attributes-nonnode-boundary.js'),encoding='utf8')
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode_manifest(revised));actual=effective(output);change=delta(old,actual,proof)
    revised['preferredPort']=port;revised['templateHashes'].update({n:sha(output/n)for n in MODULES+['public/app.js']});revised['sourceHashes']['nonnode_boundary_branches']=sha(path);revised['reviewContentHashes'].update(effective_edge_attributes=hashlib.sha256(encode(actual)).hexdigest(),attribute_value_context=hashlib.sha256(encode(context)).hexdigest());revised['nonNodeBoundaryBranchRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(path),implementation=sha(__file__),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode_manifest(revised));index=output/'public/index.html';index.write_text(index.read_text('utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    folder=output/FOLDER;folder.mkdir();shutil.copy2(path,folder/'native-proof.json');(folder/'current-effective.json').write_bytes(encode(actual));(folder/'provider-inventory.json').write_bytes(encode(provider_from(load(provider),proof,actual,context,path)))
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source'];doc,preflight=read_source(source['path']);schema=validate_bundle(output,native_doc=doc,native_source_sha256=source['sha256']);(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source['path'])
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('non-node boundary source/viewer schema failed')
    if base.artifact_inventory(parent)!=before:raise ValueError('parent viewer mutated')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('source graph, components or annotations changed')
    audit=dict(mode=MODE,parent=str(parent),parent_files=before,proof_path=str(path),proof_sha256=sha(path),provider_binding=binding,bundle_id=revised['bundleId'],delta=change,source_preflight=preflight,graph_and_components_exact=True,human_accepted=False,whole_goal_complete=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    return audit

def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);path=Path(a['proof_path']);proof=verify_output(path.parent);m=load(output/'public/data/manifest.json')
    if a['mode']!=MODE or m['nonNodeBoundaryBranchRefresh']['implementation_sha256']!=sha(__file__)or sha(path)!=a['proof_sha256']or m['bundleId']!=a['bundle_id']or base.artifact_inventory(parent)!=a['parent_files']or {n:h for n,h in base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']or context_from(parent,proof,path)!=m['attributeValueContext']:raise ValueError('non-node boundary branch viewer binding changed')
    actual=effective(output)
    if delta(effective(parent),actual,proof)!=a['delta']or encode(provider_from(load(a['provider_binding']['provider']['path']),proof,actual,m['attributeValueContext'],path))!=(output/FOLDER/'provider-inventory.json').read_bytes():raise ValueError('actual non-node boundary branch values or provider differ')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=a['delta'],human_accepted=False)

def main():
    p=argparse.ArgumentParser()
    for n in ['parent','output','proof','parent-provider','templates','verify-output']:p.add_argument('--'+n,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify(a.verify_output)if a.verify_output else refresh(a.parent,a.output,a.proof,a.parent_provider,a.templates,a.port)
    print({k:v for k,v in r.items()if k in ['status','artifact_replay','bundle_id','delta']},flush=True)
if __name__=='__main__':main()
