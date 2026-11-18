"""Compose source-qualified chain correspondence, DN and centreline attributes."""
import copy,hashlib,json,shutil,subprocess,sys,zipfile
from pathlib import Path
for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):sys.path.insert(0,str(Path(__file__).resolve().parents[2]/name/'scripts'))
import refresh_attribute_templates as base
from reapply_complementary_plan_attributes import verify_output as native_owner,MODE as NATIVE_MODE
from complementary_plan_attribute_application import adopt_provider
sha,load,encode=base.sha,base.load,base.encoded
MODE='native_complementary_plan_attribute_viewer_v1'
ALLOWED={'public/complementary-plan-attributes.js','public/edge-attributes-complementary.js'}

def effective(bundle):
    b=Path(bundle);facade='edge-attributes-complementary.js'if(b/'public/edge-attributes-complementary.js').exists()else'edge-attributes-two-arm.js'
    script="import fs from'node:fs';import{pathToFileURL}from'node:url';const m=await import(pathToFileURL(process.argv[1])),g=JSON.parse(fs.readFileSync(process.argv[2])),v=JSON.parse(fs.readFileSync(process.argv[3]));console.log(JSON.stringify(g.edges.map(e=>({edge_id:e.edge_id,values:m.crossViewAttributeCsvValues(e,v.attributeValueContext)}))));"
    r=subprocess.run(['node','--input-type=module','-e',script,str(b/'public'/facade),str(b/'public/data/graph.json'),str(b/'public/data/manifest.json')],capture_output=True,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if r.returncode:raise ValueError('complementary actual attribute reader failed: '+r.stderr)
    return json.loads(r.stdout)

def fresh_result(proof,path):
    path=Path(path);receipt=load(path.parent/'receipt.json')
    return receipt['output_sha256'].get(path.name)==sha(path)and json.loads(encode(proof))==load(path)

def context_from(proof,path,parent):
    m=load(Path(parent)/'public/data/manifest.json');prior=m['attributeValueContext'];graph=load(Path(parent)/'public/data/graph.json');gh=sha(Path(parent)/'public/data/graph.json')
    if proof.get('mode')!=NATIVE_MODE or any(proof.get(k)is not True for k in('complete_corrected_parent_replayed','original_complete_DN_parent_replayed','current_T_and_original_metric_owners_reused','all_current_complementary_intervals_screened','all_original_known_plan_DN_preserved','all_historical_main_roles_reapplied'))or any(proof.get(k)is not False for k in('source_graphs_mutated','source_components_reassigned','axis_values_used_for_horizontal_DN','human_accepted'))or any(proof.get(k)!=0 for k in('vertical_values_assigned','installed_lengths_assigned')):raise ValueError('unsupported complementary plan native source')
    if sha(Path(parent)/'public/data/manifest.json')!=proof['inputs']['viewer_manifest']['sha256']or gh!=prior['current_rendered_graph_sha256']or gh!=m['reviewContentHashes']['viewer_graph']:raise ValueError('complementary attributes use another rendered parent')
    if 'complementary_plan_attributes'in prior:raise ValueError('complementary attributes already adopted')
    by={e['edge_id']:e for e in graph['edges']}
    for r in proof['records']:
        e=by[r['axis_edge_id']]
        if e['system']!=r['system']or[e['start_node_id'],e['end_node_id']]!=r['axis_nodes']or e['attribute_paths']!=r['axis_attribute_paths']or any(e.get(k)!=r['floor']for k in('floor_start','floor_end'))or r['source_bindings']['parent_proof']!=proof['inputs']['parent_proof']['sha256']:raise ValueError('complementary metric identity or original correspondence differs')
    context=copy.deepcopy(prior);context['complementary_plan_attributes']=dict(mode='qualified_complementary_plan_attributes_v1',records=copy.deepcopy(proof['records']),count=len(proof['records']),
        complete_corrected_parent_replayed=True,current_T_and_original_metric_owners_reused=True,all_historical_main_roles_reapplied=True,source_graphs_mutated=False,vertical_values_assigned=0,installed_lengths_assigned=0,human_accepted=False,
        source_bindings=dict(raw_axis_graph=prior['source_graph_sha256'],rendered_graph=gh,native_axis_graph=proof['inputs']['axis_graph']['sha256'],native_parent_proof=proof['inputs']['parent_proof']['sha256'],native_attribute_proof=sha(path)))
    return json.loads(encode(context))

def delta(before,after,records):
    old={r['edge_id']:r['values']for r in before};new={r['edge_id']:r['values']for r in after};targets={r['axis_edge_id']:r for r in records};allowed={'diameter_nominal_mm','diameter_text','diameter_status'};changes=[]
    if old.keys()!=new.keys()or len(targets)!=len(records):raise ValueError('complementary edge inventory differs')
    for eid,prior in old.items():
        actual=new[eid];record=targets.get(eid)
        for key,value in prior.items():
            if key not in actual:raise ValueError('old attribute column missing')
            if actual[key]!=value:
                if record is None or record['nominal_mm']is None or key not in allowed or prior.get('diameter_nominal_mm')not in('',None):raise ValueError('unexpected old attribute mutation '+eid+'/'+key)
                changes.append([eid,key])
        extra={k:v for k,v in actual.items()if k not in prior}
        if record is None:
            if extra:raise ValueError('unrelated complementary attribute writer')
        else:
            for key in extra:
                if key.startswith('complementary_'):continue
                if record['nominal_mm']is None or key not in allowed or prior.get('diameter_nominal_mm')not in('',None):raise ValueError('unqualified new generic attribute')
                # These are existing CSV columns whose prior sparse reader
                # omitted the keys; their actual exported cells were blank.
                changes.append([eid,key])
            if actual.get('complementary_plan_centerline_mm')!=record['complete_horizontal_centerline_mm']or actual.get('complementary_mapping_id')!=record['source_scope_id']or json.loads(actual.get('complementary_evidence_json','{}'))!=json.loads(encode(record)):raise ValueError('new source-qualified attributes were not adopted')
            if record['nominal_mm']is not None and(actual.get('diameter_nominal_mm')!=record['nominal_mm']or actual.get('diameter_text')!='DN'+format(record['nominal_mm'],'g')or actual.get('diameter_status')!='source_checked_current_T_plan_DN'):raise ValueError('actual whole DN differs from source')
    return dict(new_complete_centerlines=len(records),new_whole_DN=sum(r['nominal_mm']is not None for r in records),declared_old_column_changes=changes,
                all_other_old248_column_values_exact=True,new_vertical_values=0,new_installed_lengths=0)

def refresh_from_native_result(parent,output,templates,native_path,port,native_result):
    parent,output,templates,native_path=map(lambda p:Path(p).resolve(),(parent,output,templates,native_path));archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh complementary attribute viewer required')
    proof,provider=native_result
    if not fresh_result(proof,native_path):raise ValueError('fresh native attribute result changed before adoption')
    before=base.artifact_inventory(parent);m=load(parent/'public/data/manifest.json');context=context_from(proof,native_path,parent);prior=effective(parent);changes={n:sha(templates/n)for n in ALLOWED}
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in changes:shutil.copy2(templates/n,output/n)
    app=output/'public/app.js';text=app.read_text(encoding='utf-8');needle="'./edge-attributes-two-arm.js'"
    if text.count(needle)!=1:raise ValueError('original current attribute import differs')
    app.write_text(text.replace(needle,"'./edge-attributes-complementary.js'"),encoding='utf-8');changes['public/app.js']=sha(app)
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode(revised));actual=effective(output);difference=delta(prior,actual,proof['records']);current_provider=adopt_provider(provider,proof,actual);digest=hashlib.sha256(encode(actual)).hexdigest()
    revised['templateHashes'].update(changes);revised['preferredPort']=port;revised['sourceHashes']['native_complementary_plan_attributes']=sha(native_path);revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(context)).hexdigest())
    revised['nativeComplementaryPlanAttributeRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(native_path),implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],source=sha(native_path),templates=changes,effective=digest,implementation=sha(__file__),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode(revised));index=output/'public/index.html';index.write_text(index.read_text(encoding='utf-8').replace(m['bundleId'],revised['bundleId']),encoding='utf-8')
    evidence=output/'complementary-native-attribute-refresh';evidence.mkdir();(evidence/'provider-inventory.json').write_bytes(encode(current_provider));(evidence/'horizontal-frontier.json').write_bytes(encode(current_provider['current_horizontal_frontier']));(evidence/'current-effective.json').write_bytes(encode(actual));shutil.copy2(native_path,evidence/'native-proof.json')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('complementary source/viewer schema failed')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('source axis graph, components or annotation history changed')
    if base.artifact_inventory(parent)!=before:raise ValueError('complementary refresh changed original bundle')
    audit=dict(mode=MODE,status='native_source_values_adopted_actual_browser_and_independent_gate_pending',parent=str(parent),parent_file_hashes=before,native_proof_path=str(native_path),native_proof_sha256=sha(native_path),changes=changes,bundle_id=revised['bundleId'],delta=difference,source_preflight=preflight,
               rendered_graph_and1574_component_instances_exact=True,all_old_correspondences_preserved=True,old_annotations_preserved=True,human_accepted=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/'native-complementary-plan-attribute-refresh.json').write_bytes(encode(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('complementary viewer package failed')
    return audit

def verify_from_native_result(output,native_result):
    output=Path(output);audit=load(output/'native-complementary-plan-attribute-refresh.json');m=load(output/'public/data/manifest.json');path=Path(audit['native_proof_path']);parent=Path(audit['parent']);proof,provider=native_result
    if audit['mode']!=MODE or m['nativeComplementaryPlanAttributeRefresh']['implementation_sha256']!=sha(__file__)or not fresh_result(proof,path)or sha(path)!=audit['native_proof_sha256']or context_from(proof,path,parent)!=m['attributeValueContext']or base.artifact_inventory(parent)!=audit['parent_file_hashes']or{n:h for n,h in base.artifact_inventory(output).items()if n!='native-complementary-plan-attribute-refresh.json'}!=audit['output_hashes']:raise ValueError('complementary source/viewer binding changed')
    actual=effective(output)
    if delta(effective(parent),actual,proof['records'])!=audit['delta']or encode(adopt_provider(provider,proof,actual))!=(output/'complementary-native-attribute-refresh/provider-inventory.json').read_bytes():raise ValueError('actual complementary provider or values differ')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=audit['delta'],human_accepted=False)

def refresh(parent,output,templates,native_path,port):return refresh_from_native_result(parent,output,templates,native_path,port,native_owner(Path(native_path).parent))
def verify(output):
    a=load(Path(output)/'native-complementary-plan-attribute-refresh.json');return verify_from_native_result(output,native_owner(Path(a['native_proof_path']).parent))
