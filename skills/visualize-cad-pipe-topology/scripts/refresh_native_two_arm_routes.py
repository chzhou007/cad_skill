"""Publish replayed plan continuity and cross-view paths without assigning metrics.

The build may consume the fresh native result in the same bounded operation;
the public standalone verifier always replays its original native owner.
"""
import copy,hashlib,json,shutil,subprocess,sys,zipfile
from pathlib import Path
for n in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/n/'scripts'))
import refresh_attribute_templates as base
from rebuild_current_two_arm_circle_routes import verify_output as native_owner,MODE as NATIVE_MODE
sha,load,encode=base.sha,base.load,base.encoded
MODE='native_two_arm_external_route_viewer_v1'
ALLOWED={'public/two-arm-external-routes.js','public/edge-attributes-two-arm.js'}

def fresh_result(proof,path):
    path=Path(path);receipt=load(path.parent/'receipt.json')
    return receipt['output_sha256'].get(path.name)==sha(path)and json.loads(encode(proof))==load(path)

def effective(bundle):
    b=Path(bundle);script="""import fs from'node:fs';import{pathToFileURL}from'node:url';const m=await import(pathToFileURL(process.argv[1])),g=JSON.parse(fs.readFileSync(process.argv[2])),v=JSON.parse(fs.readFileSync(process.argv[3]));console.log(JSON.stringify(g.edges.map(e=>({edge_id:e.edge_id,values:m.crossViewAttributeCsvValues(e,v.attributeValueContext)}))));"""
    facade='edge-attributes-two-arm.js'if(b/'public/edge-attributes-two-arm.js').exists()else'edge-attributes-anchored-metrics.js'
    r=subprocess.run(['node','--input-type=module','-e',script,str(b/'public'/facade),str(b/'public/data/graph.json'),str(b/'public/data/manifest.json')],capture_output=True,text=True,encoding='utf8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if r.returncode:raise ValueError('two-arm actual attribute reader failed: '+r.stderr)
    return json.loads(r.stdout)

def context_from(proof,path,parent):
    m=load(Path(parent)/'public/data/manifest.json');prior=m['attributeValueContext'];graph=load(Path(parent)/'public/data/graph.json');gh=sha(Path(parent)/'public/data/graph.json')
    if proof.get('mode')!=NATIVE_MODE or any(proof.get(k)is not True for k in('complete_original_adopted_provider_replayed','current_local_topology_parents_replayed','all_current_pipe_circles_screened','original_two_arm_rule_reused','old_source_graphs_unchanged','all_old_provider_observations_preserved'))or proof.get('new_pipe_attribute_values')!=0 or proof.get('physical_Ts_added')!=0 or proof.get('human_accepted')is not False:raise ValueError('unsupported two-arm native source')
    if sha(Path(parent)/'public/data/manifest.json')!=proof['inputs']['viewer_manifest']['sha256']or gh!=m['reviewContentHashes']['viewer_graph']or gh!=prior['current_rendered_graph_sha256']:raise ValueError('two-arm source uses another rendered parent')
    if 'native_two_arm_external_routes'in prior:raise ValueError('two-arm routes already adopted')
    edges={e['edge_id']:e for e in graph['edges']}
    for r in proof['records']:
        e=edges[r['axis_edge_id']]
        if e['system']!=r['system']or [e['start_node_id'],e['end_node_id']]!=r['axis_nodes']or e['attribute_paths']!=r['axis_attribute_paths']or any(e.get(k)!=r['floor']for k in('floor_start','floor_end'))or r['physical_values_assigned']!=0 or r['attribute_adoption_allowed']is not False:raise ValueError('two-arm native/viewer route identity differs')
    context=copy.deepcopy(prior);context['native_two_arm_external_routes']=dict(mode='qualified_native_two_arm_external_routes_v1',records=copy.deepcopy(proof['records']),count=len(proof['records']),original_two_arm_rule_reused=True,new_pipe_attribute_values=0,physical_Ts_added=0,human_accepted=False,source_bindings=dict(raw_axis_graph=prior['source_graph_sha256'],rendered_graph=gh,native_axis_graph=proof['inputs']['axis_graph']['sha256'],native_route_proof=sha(path)))
    return json.loads(encode(context))

def delta(before,after,records):
    old={r['edge_id']:r['values']for r in before};new={r['edge_id']:r['values']for r in after};target={r['axis_edge_id']:r for r in records}
    if old.keys()!=new.keys()or len(target)!=len(records):raise ValueError('two-arm edge inventory differs')
    for eid,values in old.items():
        if any(k not in new[eid]or new[eid][k]!=v for k,v in values.items()):raise ValueError('two-arm route changed an old DN, metric or source value')
        extra={k:v for k,v in new[eid].items()if k not in values}
        if eid not in target:
            if extra:raise ValueError('two-arm unrelated attribute writer')
        elif any(not k.startswith('two_arm_external_')for k in extra)or new[eid].get('two_arm_external_mapping_id')!=target[eid]['mapping_id']or json.loads(new[eid].get('two_arm_external_evidence_json','{}'))!=json.loads(encode(target[eid])):raise ValueError('two-arm source relation not adopted by actual reader')
    return dict(new_correspondences=len(records),all_old244_column_values_exact=True,new_DN_values=0,new_length_values=0,new_vertical_values=0)

def refresh_from_verified_native(parent,output,templates,native_path,port,native_result):
    """Called immediately after the formal native verifier in the same build."""
    parent,output,templates,native_path=map(lambda p:Path(p).resolve(),(parent,output,templates,native_path));archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh external two-arm viewer required')
    proof,provider,local,graphs=native_result
    if not fresh_result(proof,native_path):raise ValueError('fresh native result changed before viewer adoption')
    from two_arm_affected_junctions import replay as replay_junctions
    junction_gate=replay_junctions(proof,graphs)
    before=base.artifact_inventory(parent);m=load(parent/'public/data/manifest.json');context=context_from(proof,native_path,parent);prior=effective(parent);changes={n:sha(templates/n)for n in ALLOWED}
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in changes:shutil.copy2(templates/n,output/n)
    app=output/'public/app.js';text=app.read_text(encoding='utf8');needle="'./edge-attributes-anchored-metrics.js'"
    if text.count(needle)!=1:raise ValueError('two-arm original app import differs')
    app.write_text(text.replace(needle,"'./edge-attributes-two-arm.js'"),encoding='utf8');changes['public/app.js']=sha(app)
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode(revised));actual=effective(output);difference=delta(prior,actual,proof['records']);digest=hashlib.sha256(encode(actual)).hexdigest()
    revised['templateHashes'].update(changes);revised['preferredPort']=port;revised['sourceHashes']['native_two_arm_external_routes']=sha(native_path);revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(context)).hexdigest());revised['nativeTwoArmRouteRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(native_path),implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],source=sha(native_path),templates=changes,effective=digest,implementation=sha(__file__),port=port))).hexdigest()[:20];(output/'public/data/manifest.json').write_bytes(encode(revised));index=output/'public/index.html';index.write_text(index.read_text(encoding='utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    evidence=output/'native-two-arm-refresh';evidence.mkdir();(evidence/'provider-inventory.json').write_bytes(encode(provider));(evidence/'member-local-graph.json').write_bytes(encode(local));(evidence/'horizontal-frontier.json').write_bytes(encode(provider['current_horizontal_frontier']));(evidence/'affected-junctions.json').write_bytes(encode(junction_gate));shutil.copy2(native_path,evidence/'native-proof.json')
    for f in graphs:
        folder=evidence/'plan-reading-graphs'/f;folder.mkdir(parents=True)
        for name in('graph_with_edges.json','assigned_edge_device_instances.csv'):shutil.copy2(native_path.parent/f/name,folder/name)
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,readable=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('two-arm native source/viewer schema failed')
    for name,h in before.items():
        if name.startswith(('public/data/','annotations/'))and name!='public/data/manifest.json'and sha(output/name)!=h:raise ValueError('two-arm route changed original axis data or annotations')
    if base.artifact_inventory(parent)!=before:raise ValueError('two-arm parent artifact changed')
    audit=dict(mode=MODE,status='fresh_native_result_adopted_actual_browser_pending',parent=str(parent),parent_file_hashes=before,native_proof_path=str(native_path),native_proof_sha256=sha(native_path),bundle_id=revised['bundleId'],changes=changes,delta=difference,source_preflight=readable,rendered_axis_graph_and_components_exact=True,old_annotations_preserved=True,human_accepted=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/'native-two-arm-refresh.json').write_bytes(encode(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for name in sorted(base.inventory(output)):z.write(output/name,output.name+'/'+name)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('two-arm viewer package invalid')
    return audit

def verify_from_native_result(output,native_result):
    output=Path(output);a=load(output/'native-two-arm-refresh.json');m=load(output/'public/data/manifest.json');path=Path(a['native_proof_path']);parent=Path(a['parent']);proof,provider,local,graphs=native_result
    if a['mode']!=MODE or m['nativeTwoArmRouteRefresh']['implementation_sha256']!=sha(__file__)or sha(path)!=a['native_proof_sha256']or not fresh_result(proof,path)or context_from(proof,path,parent)!=m['attributeValueContext']or base.artifact_inventory(parent)!=a['parent_file_hashes']or {n:h for n,h in base.artifact_inventory(output).items()if n!='native-two-arm-refresh.json'}!=a['output_hashes']:raise ValueError('two-arm viewer native source/output differs')
    if delta(effective(parent),effective(output),proof['records'])!=a['delta']or encode(provider)!=(output/'native-two-arm-refresh/provider-inventory.json').read_bytes()or encode(local)!=(output/'native-two-arm-refresh/member-local-graph.json').read_bytes():raise ValueError('two-arm actual provider or viewer values differ')
    from two_arm_affected_junctions import replay as replay_junctions
    if encode(replay_junctions(proof,graphs))!=(output/'native-two-arm-refresh/affected-junctions.json').read_bytes():raise ValueError('affected original T role requalification differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],counts=a['delta'],human_accepted=False)

def refresh(parent,output,templates,native_path,port):return refresh_from_verified_native(parent,output,templates,native_path,port,native_owner(Path(native_path).parent))
def verify(output):
    a=load(Path(output)/'native-two-arm-refresh.json');return verify_from_native_result(output,native_owner(Path(a['native_proof_path']).parent))
