"""Adopt source-qualified horizontal metrics without changing old DN or geometry."""
import copy,hashlib,json,shutil,sys,zipfile,subprocess
from pathlib import Path
for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    path=str(Path(__file__).resolve().parents[2]/name/'scripts')
    if path not in sys.path:sys.path.insert(0,path)
import refresh_attribute_templates as base
from reapply_anchored_plan_metrics import verify_output as native_owner,inventory_from,MODE as NATIVE_MODE
sha,load,encoded=base.sha,base.load,base.encoded
MODE='qualified_anchored_native_plan_metric_viewer_v1'
ALLOWED={'public/edge-attributes-anchored-metrics.js','public/anchored-native-plan-metrics.js'}

def effective_attributes(bundle):
    """Read the explicitly enabled version; preserve the original reader bytes."""
    script="""import fs from 'node:fs';import{pathToFileURL}from'node:url';const m=await import(pathToFileURL(process.argv[1])),g=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),manifest=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));process.stdout.write(JSON.stringify(g.edges.map(e=>({edge_id:e.edge_id,values:m.crossViewAttributeCsvValues(e,manifest.attributeValueContext)}))));"""
    result=subprocess.run(['node','--input-type=module','-e',script,str(Path(bundle)/'public/edge-attributes-anchored-metrics.js'),str(Path(bundle)/'public/data/graph.json'),str(Path(bundle)/'public/data/manifest.json')],capture_output=True,text=True,encoding='utf8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('versioned metric attribute reader failed: '+result.stderr)
    return json.loads(result.stdout)

def context_from(proof,path,parent):
    m=load(Path(parent)/'public/data/manifest.json');prior=m['attributeValueContext'];graph_path=Path(parent)/'public/data/graph.json';graph=load(graph_path)
    if proof['mode']!=NATIVE_MODE or any(proof.get(k)is not True for k in('complete_original_provider_replayed','all_pending_horizontal_length_scopes_screened','original_metric_readers_reused','native_T_paths_components_and_joint_origins_replayed'))or any(proof.get(k)is not False for k in('source_graphs_mutated','component_owners_changed','human_accepted'))or any(proof.get(k)!=0 for k in('DN_values_assigned','vertical_values_assigned','installed_lengths_assigned')):raise ValueError('unsupported anchored native metric source')
    if sha(Path(parent)/'public/data/manifest.json')!=proof['inputs']['viewer_manifest']['sha256']or sha(graph_path)!=m['reviewContentHashes']['viewer_graph']or sha(graph_path)!=prior['current_rendered_graph_sha256']:raise ValueError('metric uses another qualified rendered parent')
    if load(Path(parent)/'validation-report.json')['status']!='passed'or load(Path(parent)/'quality-gate.json')['machine_status']!='PASS':raise ValueError('original viewer source/schema qualification missing')
    if 'anchored_plan_metrics'in prior:raise ValueError('anchored metrics already composed')
    edges={e['edge_id']:e for e in graph['edges']};records=[]
    for r in proof['records']:
        e=edges[r['axis_edge_id']]
        if e['system']!=r['system']or [e['start_node_id'],e['end_node_id']]!=r['axis_nodes']or e['attribute_paths']!=r['axis_attribute_paths']or any(e.get(k)!=r['floor']for k in('floor_start','floor_end')):raise ValueError('anchored metric native identity or scope differs')
        value=r['complete_horizontal_centerline_mm']
        if not isinstance(value,(int,float))or isinstance(value,bool)or value<=0 or r['projection']['value_mm']!=value or r['DN_evidence_changed']is not False or r['related_HIL_confirmation_inherited']is not False:raise ValueError('invalid native metric value or confirmation')
        records.append(copy.deepcopy(r))
    if len(records)!=proof['counts']['complete_centerlines']or len({r['axis_edge_id']for r in records})!=len(records):raise ValueError('complete unique metric cohort required')
    result=copy.deepcopy(prior);result['anchored_plan_metrics']=dict(mode='qualified_anchored_native_plan_metrics_v1',records=records,count=len(records),original_metric_readers_reused=True,source_graphs_mutated=False,component_owners_changed=False,DN_values_assigned=0,vertical_values_assigned=0,installed_lengths_assigned=0,human_accepted=False,
        source_bindings=dict(raw_axis_graph=prior['source_graph_sha256'],rendered_graph=sha(graph_path),native_axis_graph=proof['inputs']['axis_graph']['sha256'],native_metric_proof=sha(path)))
    return json.loads(encoded(result))

def delta(prior,current,records):
    old={r['edge_id']:r['values']for r in prior};new={r['edge_id']:r['values']for r in current};target={r['axis_edge_id']:r for r in records}
    if old.keys()!=new.keys()or len(target)!=len(records):raise ValueError('metric edge inventory differs')
    for eid,before in old.items():
        after=new[eid]
        if any(k not in after or after[k]!=v for k,v in before.items()):raise ValueError('old effective attribute changed '+eid)
        extra={k:v for k,v in after.items()if k not in before}
        if eid not in target:
            if extra:raise ValueError('unrelated metric attribute writer')
            continue
        r=target[eid]
        if any(not k.startswith('anchored_metric_')for k in extra)or after.get('anchored_metric_complete_centerline_mm')!=r['complete_horizontal_centerline_mm']or after.get('anchored_metric_mapping_id')!=r['source_scope_id']or json.loads(after.get('anchored_metric_evidence_json','{}'))!=json.loads(encoded(r)):raise ValueError('metric CSV differs from native proof')
    return dict(new_complete_horizontal_centerlines=len(records),all_old_effective_attribute_values_exact=True,new_DN_values=0,new_vertical_values=0,new_installed_lengths=0)

def refresh(parent,output,templates,native_path,port):
    parent,output,templates,native_path=map(lambda p:Path(p).resolve(),(parent,output,templates,native_path));archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh external metric viewer required')
    before=base.artifact_inventory(parent);m=load(parent/'public/data/manifest.json');proof=native_owner(native_path.parent);context=context_from(proof,native_path,parent);prior=base.effective_attributes(parent);changes={n:sha(templates/n)for n in ALLOWED}
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in changes:shutil.copy2(templates/name,output/name)
    app=output/'public/app.js';text=app.read_text(encoding='utf8');needle="'./edge-attributes.js'"
    if text.count(needle)!=1:raise ValueError('original app attribute import is not unique')
    app.write_text(text.replace(needle,"'./edge-attributes-anchored-metrics.js'"),encoding='utf8');changes['public/app.js']=sha(app)
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encoded(revised));actual=effective_attributes(output);difference=delta(prior,actual,proof['records']);digest=hashlib.sha256(encoded(actual)).hexdigest()
    revised['templateHashes'].update(changes);revised['preferredPort']=port;revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encoded(context)).hexdigest());revised['sourceHashes']['anchored_native_plan_metrics']=sha(native_path)
    revised['anchoredNativeMetricRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(native_path),implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encoded(dict(parent=m['bundleId'],native=sha(native_path),templates=changes,effective=digest,implementation=sha(__file__),port=port))).hexdigest()[:20];(output/'public/data/manifest.json').write_bytes(encoded(revised));index=output/'public/index.html';index.write_text(index.read_text(encoding='utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,readable=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encoded(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('metric viewer native source/schema failed')
    for name,h in before.items():
        if name.startswith(('public/data/','annotations/'))and name!='public/data/manifest.json'and sha(output/name)!=h:raise ValueError('old source graph/components or annotations changed')
    if base.artifact_inventory(parent)!=before:raise ValueError('metric viewer changed original parent')
    evidence=output/'anchored-native-metric-refresh';evidence.mkdir();(evidence/'parent-effective.json').write_bytes(encoded(prior));(evidence/'current-effective.json').write_bytes(encoded(actual));shutil.copy2(native_path,evidence/'native-proof.json')
    provider=inventory_from(load(proof['inputs']['provider']['path']),proof,actual);(evidence/'provider-inventory.json').write_bytes(encoded(provider));(evidence/'horizontal-frontier.json').write_bytes(encoded(provider['current_horizontal_frontier']))
    audit=dict(mode=MODE,status='native_metric_context_and_source_schema_passed_actual_browser_pending',parent=str(parent),parent_file_hashes=before,parent_bundle_id=m['bundleId'],bundle_id=revised['bundleId'],native_proof_path=str(native_path),native_proof_sha256=sha(native_path),changes=changes,delta=difference,effective_attribute_sha256=digest,source_preflight=readable,rendered_graph_unchanged=True,component_assignments_unchanged=True,old_annotations_preserved=True,human_confirmation_inherited=False,human_accepted=False)
    audit['output_hashes']={n:h for n,h in base.artifact_inventory(output).items()if n!='anchored-native-metric-refresh.json'};(output/'anchored-native-metric-refresh.json').write_bytes(encoded(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('metric viewer ZIP failed')
    return audit

def verify(output):
    output=Path(output);a=load(output/'anchored-native-metric-refresh.json');m=load(output/'public/data/manifest.json');parent=Path(a['parent']);path=Path(a['native_proof_path'])
    if a['mode']!=MODE or m['bundleId']!=a['bundle_id']or m['anchoredNativeMetricRefresh']['implementation_sha256']!=sha(__file__)or base.artifact_inventory(parent)!=a['parent_file_hashes']:raise ValueError('metric viewer qualification changed')
    proof=native_owner(path.parent)
    if sha(path)!=a['native_proof_sha256']or context_from(proof,path,parent)!=m['attributeValueContext']or {n:h for n,h in base.artifact_inventory(output).items()if n!='anchored-native-metric-refresh.json'}!=a['output_hashes']:raise ValueError('metric viewer source or output changed')
    actual=effective_attributes(output)
    if delta(base.effective_attributes(parent),actual,proof['records'])!=a['delta']or hashlib.sha256(encoded(actual)).hexdigest()!=a['effective_attribute_sha256']:raise ValueError('metric effective values differ')
    provider=inventory_from(load(proof['inputs']['provider']['path']),proof,actual)
    if encoded(provider)!=(output/'anchored-native-metric-refresh/provider-inventory.json').read_bytes()or encoded(provider['current_horizontal_frontier'])!=(output/'anchored-native-metric-refresh/horizontal-frontier.json').read_bytes():raise ValueError('metric provider/frontier adoption differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],counts=a['delta'],human_accepted=False)
