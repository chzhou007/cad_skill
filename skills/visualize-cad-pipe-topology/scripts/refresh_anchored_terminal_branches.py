"""Publish native drawing branch contexts without any whole-edge writer."""
import copy,hashlib,json,shutil,subprocess,sys,zipfile
from pathlib import Path
for n in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):sys.path.insert(0,str(Path(__file__).resolve().parents[2]/n/'scripts'))
import refresh_attribute_templates as base
from reapply_anchored_terminal_branches import verify_output as native_owner,MODE as NATIVE_MODE
from anchored_terminal_branch_provider import adopt_provider
sha,load,encode=base.sha,base.load,base.encoded
MODE='native_anchored_terminal_branch_viewer_v1'
ALLOWED={'public/anchored-terminal-branches.js','public/edge-attributes-terminal-branches.js'}
def effective(bundle):
    b=Path(bundle);facade='edge-attributes-terminal-branches.js'if(b/'public/edge-attributes-terminal-branches.js').exists()else'edge-attributes-complementary.js'
    js="import fs from'node:fs';import{pathToFileURL}from'node:url';const m=await import(pathToFileURL(process.argv[1])),g=JSON.parse(fs.readFileSync(process.argv[2])),v=JSON.parse(fs.readFileSync(process.argv[3]));console.log(JSON.stringify(g.edges.map(e=>({edge_id:e.edge_id,values:m.crossViewAttributeCsvValues(e,v.attributeValueContext)}))));"
    p=subprocess.run(['node','--input-type=module','-e',js,str(b/'public'/facade),str(b/'public/data/graph.json'),str(b/'public/data/manifest.json')],capture_output=True,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if p.returncode:raise ValueError('actual branch attribute reader failed: '+p.stderr)
    return json.loads(p.stdout)
def fresh(proof,path):
    receipt=load(Path(path).parent/'receipt.json')
    if receipt['output_sha256']!=sha(path)or json.loads(encode(proof))!=load(path):raise ValueError('fresh native branch proof changed')
def context_from(proof,path,parent):
    m=load(Path(parent)/'public/data/manifest.json');prior=m['attributeValueContext'];graph=load(Path(parent)/'public/data/graph.json');gh=sha(Path(parent)/'public/data/graph.json')
    if proof.get('mode')!=NATIVE_MODE or any(proof.get(k)is not True for k in('complete_published_parent_replayed','all_current_independent_main_third_arms_screened'))or any(proof.get(k)is not False for k in('graph_mutated','old_providers_replaced','human_accepted'))or any(proof.get(k)!=0 for k in('remote_equipment_identities_assigned','physical_ports_created','whole_axis_DN_assigned','whole_axis_lengths_assigned','vertical_values_assigned')):raise ValueError('unsupported native branch context')
    if sha(Path(parent)/'public/data/manifest.json')!=proof['inputs']['parent_viewer_manifest']['sha256']or gh!=prior['current_rendered_graph_sha256']or gh!=m['reviewContentHashes']['viewer_graph']or'anchored_terminal_branches'in prior:raise ValueError('branch context uses another rendered parent')
    by={e['edge_id']:e for e in graph['edges']}
    for r in proof['records']:
        e=by[r['axis_edge_id']];native=r['native_checks']['iso']['snapshot']['edges'][0]
        if any(e[k]!=native[k]for k in('edge_id','system','start_node_id','end_node_id','attribute_paths'))or any(e.get(k)!=r['floor']for k in('floor_start','floor_end')):raise ValueError('branch source edge differs from actual rendered graph')
    context=copy.deepcopy(prior);context['anchored_terminal_branches']=dict(mode='qualified_anchored_terminal_drawing_branches_v1',records=copy.deepcopy(proof['records']),count=len(proof['records']),
        complete_published_parent_replayed=True,all_current_independent_main_third_arms_screened=True,graph_mutated=False,old_providers_replaced=False,
        remote_equipment_identities_assigned=0,physical_ports_created=0,whole_axis_DN_assigned=0,whole_axis_lengths_assigned=0,vertical_values_assigned=0,human_accepted=False,
        source_bindings=dict(raw_axis_graph=prior['source_graph_sha256'],rendered_graph=gh,native_axis_graph=proof['inputs']['axis_graph']['sha256'],plan_source=proof['inputs']['plan_source']['sha256'],plan_graph=proof['inputs']['plan_graph']['sha256'],native_branch_proof=sha(path),parent_attribute_proof=proof['inputs']['parent_proof']['sha256']))
    return json.loads(encode(context))
def delta(before,after,records):
    old={x['edge_id']:x['values']for x in before};new={x['edge_id']:x['values']for x in after};targets={r['axis_edge_id']:r for r in records}
    if old.keys()!=new.keys()or len(targets)!=len(records):raise ValueError('branch edge inventory differs')
    for eid,prior in old.items():
        actual=new[eid]
        if any(k not in actual or actual[k]!=v for k,v in prior.items()):raise ValueError('an old pipe attribute changed '+eid)
        extra={k:v for k,v in actual.items()if k not in prior};r=targets.get(eid)
        if r is None:
            if extra:raise ValueError('unrelated new branch writer')
        elif len(extra)!=8 or any(not k.startswith('anchored_branch_')for k in extra)or actual.get('anchored_branch_mapping_id')!=r['mapping_id']or actual.get('anchored_branch_plan_pipe_XY_mm')!=r['plan_horizontal_projection']['value_mm']or json.loads(actual.get('anchored_branch_evidence_json','{}'))!=json.loads(encode(r)):raise ValueError('native branch context not adopted by actual reader')
    return dict(new_drawing_branch_contexts=len(records),all_old256_column_values_exact=True,new_whole_DN_values=0,new_complete_horizontal_lengths=0,new_vertical_values=0)
def refresh_from_native_result(parent,output,templates,path,port,native_result):
    parent,output,templates,path=map(lambda x:Path(x).resolve(),(parent,output,templates,path));archive=output.with_suffix('.zip');proof=native_result
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh branch viewer required')
    fresh(proof,path);before=base.artifact_inventory(parent);m=load(parent/'public/data/manifest.json');context=context_from(proof,path,parent);prior=effective(parent);changes={n:sha(templates/n)for n in ALLOWED}
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in changes:shutil.copy2(templates/n,output/n)
    app=output/'public/app.js';s=app.read_text('utf-8');needle="'./edge-attributes-complementary.js'"
    if s.count(needle)!=1:raise ValueError('current attribute facade differs')
    connection="['Connection',connection]"
    if s.count(connection)!=1:raise ValueError('current connection property differs')
    s=s.replace(connection,'...anchoredTerminalConnectionProperties(e,data.attribute_value_context,connection)')
    s="import{anchoredTerminalConnectionProperties}from './anchored-terminal-branches.js';\n"+s.replace(needle,"'./edge-attributes-terminal-branches.js'")
    app.write_text(s,encoding='utf-8');changes['public/app.js']=sha(app)
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode(revised));actual=effective(output);difference=delta(prior,actual,proof['records']);provider=adopt_provider(load(proof['inputs']['parent_provider']['path']),proof,actual);digest=hashlib.sha256(encode(actual)).hexdigest()
    revised['templateHashes'].update(changes);revised['preferredPort']=port;revised['sourceHashes']['native_anchored_terminal_branches']=sha(path);revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(context)).hexdigest());revised['nativeAnchoredTerminalBranchRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(path),implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],source=sha(path),templates=changes,effective=digest,implementation=sha(__file__),port=port))).hexdigest()[:20];(output/'public/data/manifest.json').write_bytes(encode(revised));index=output/'public/index.html';index.write_text(index.read_text('utf-8').replace(m['bundleId'],revised['bundleId']),encoding='utf-8')
    evidence=output/'anchored-terminal-branch-refresh';evidence.mkdir();(evidence/'provider-inventory.json').write_bytes(encode(provider));(evidence/'current-effective.json').write_bytes(encode(actual));shutil.copy2(path,evidence/'native-proof.json')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('source/viewer branch schema failed')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('source graph, components or historical annotation changed')
    if base.artifact_inventory(parent)!=before:raise ValueError('original viewer changed')
    audit=dict(mode=MODE,status='native_branch_contexts_adopted_actual_browser_and_independent_gate_pending',parent=str(parent),parent_file_hashes=before,native_proof_path=str(path),native_proof_sha256=sha(path),changes=changes,bundle_id=revised['bundleId'],delta=difference,source_preflight=preflight,rendered_graph_and1574_component_instances_exact=True,old_annotations_preserved=True,human_accepted=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/'native-anchored-terminal-branch-refresh.json').write_bytes(encode(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('branch viewer archive failed')
    return audit
def verify_from_native_result(output,proof):
    output=Path(output);a=load(output/'native-anchored-terminal-branch-refresh.json');m=load(output/'public/data/manifest.json');parent=Path(a['parent']);path=Path(a['native_proof_path']);fresh(proof,path)
    if a['mode']!=MODE or m['nativeAnchoredTerminalBranchRefresh']['implementation_sha256']!=sha(__file__)or sha(path)!=a['native_proof_sha256']or context_from(proof,path,parent)!=m['attributeValueContext']or base.artifact_inventory(parent)!=a['parent_file_hashes']or{n:h for n,h in base.artifact_inventory(output).items()if n!='native-anchored-terminal-branch-refresh.json'}!=a['output_hashes']:raise ValueError('native branch viewer binding changed')
    actual=effective(output)
    if delta(effective(parent),actual,proof['records'])!=a['delta']or encode(adopt_provider(load(proof['inputs']['parent_provider']['path']),proof,actual))!=(output/'anchored-terminal-branch-refresh/provider-inventory.json').read_bytes():raise ValueError('actual branch provider or values differ')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=a['delta'],human_accepted=False)
def verify(output):
    a=load(Path(output)/'native-anchored-terminal-branch-refresh.json');return verify_from_native_result(output,native_owner(Path(a['native_proof_path']).parent))
