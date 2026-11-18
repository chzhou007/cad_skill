"""Adopt source group metrics without allocating lengths to axis edges."""
import argparse,copy,hashlib,shutil,sys,zipfile
from pathlib import Path
for n in ['build-cad-pipe-topology','orchestrate-cad-drawing-pipeline']:sys.path.insert(0,str(Path(__file__).resolve().parents[2]/n/'scripts'))
from confirm_crossview_paths import load,sha,encode
from reviewed_expression_metrics import verify_output as verify_source,MODE as SOURCE_MODE
from refresh_expanded_main_seed_bend_DN import verify as verify_parent
from refresh_reviewed_ring_partition_DN import effective
import refresh_attribute_templates as base

MODE='reviewed_expression_group_metric_viewer_v1';AUDIT='reviewed-expression-group-metric-refresh.json';FOLDER='reviewed-expression-group-metric-refresh'
MODULES=['public/edge-attributes-expression-group.js','public/reviewed-expression-group-metrics.js']
FIELDS={'shared_plan_metric_scope_ids','shared_plan_metric_scopes_json','shared_plan_metric_source_sha256'}

def adopt(context,graph,proof,scope,proof_hash):
    result=copy.deepcopy(context)
    if 'reviewed_expression_group_metrics'in result:raise ValueError('group context already adopted')
    if (proof['mode']!=SOURCE_MODE or proof['original_native_group_owner_reexecuted']is not True or proof['original_plan_metric_reader_reused']is not True
        or any(proof[k]!=0 for k in ['per_axis_edge_values_assigned','physical_lengths_assigned','DN_values_assigned'])or proof['human_accepted']is not False):raise ValueError('source group metric qualification required')
    for k in ['plan_graph','plan_source']:
        if proof['inputs'][k]!=scope['inputs'][k]:raise ValueError('group source namespace changed')
    targets={e['edge_id']:e for e in graph['edges']};parents={r['scope_id']:r for r in scope['records']};records=[]
    if len(parents)!=len(scope['records']):raise ValueError('ambiguous source group identity')
    for r in proof['records']:
        p=parents[r['scope_id']]
        if (p['status']!='native_bounded_range_correspondence'or r['axis_edges']!=p['views']['iso']['route']['edges']or r['plan_edges']!=p['views']['plan']['route']['edges']
            or r['per_axis_edge_length_allocation']is not None or r['per_axis_edge_DN_assignment']is not None or r['complete_group_physical_length_mm']is not None or r['human_accepted']is not False):raise ValueError('qualified route or unknown allocation changed')
        originals={e['edge_id']:e for e in p['views']['iso']['source_snapshot']['edges']};members=[]
        for eid in r['axis_edges']:
            raw=originals[eid];e=targets[eid]
            for key in ['system','start_node_id','end_node_id','attribute_paths']:
                if e[key]!=raw[key]:raise ValueError('current source member geometry changed '+eid)
            floors=[e['floor_start'],e['floor_end']]
            if any(f!=r['floor']for f in floors)or e['system']!=r['system']:raise ValueError('current source member floor or system differs')
            members.append(dict(edge_id=eid,system=e['system'],start_node_id=e['start_node_id'],end_node_id=e['end_node_id'],attribute_paths=copy.deepcopy(e['attribute_paths']),floors=floors))
        records.append(dict(copy.deepcopy(r),axis_members=members))
    result['reviewed_expression_group_metrics']=dict(mode='qualified_reviewed_expression_group_metrics_v1',records=records,count=len(records),per_axis_edge_values_assigned=0,human_accepted=False,
        source_bindings=dict(plan_source=proof['inputs']['plan_source']['sha256'],plan_graph=proof['inputs']['plan_graph']['sha256'],axis_source=scope['inputs']['iso_source']['sha256'],axis_graph=scope['inputs']['iso_graph']['sha256'],native_metric_proof=proof_hash,native_scope_proof=proof['inputs']['scope_proof']['sha256'],rendered_attribute_graph=context['current_rendered_graph_sha256']))
    return result

def delta(before,after,context):
    old={r['edge_id']:r['values']for r in before};new={r['edge_id']:r['values']for r in after};target={e for r in context['reviewed_expression_group_metrics']['records']for e in r['axis_edges']};changed=[]
    if old.keys()!=new.keys():raise ValueError('edge population changed')
    for eid,values in old.items():
        current=new[eid]
        if {k:v for k,v in current.items()if k not in FIELDS}!=values:raise ValueError('old pipe values changed '+eid)
        if eid in target:
            if any(k not in current for k in FIELDS):raise ValueError('source group metadata not effectively adopted '+eid)
            changed.append(eid)
        elif current!=values:raise ValueError('unrelated edge changed '+eid)
    return dict(group_metadata_edges=sorted(changed),old_pipe_values_exact=True,new_per_axis_edge_length_values=0,new_DN_values=0,new_columns=len(FIELDS))

def context_from(parent,proof,path):
    m=load(Path(parent)/'public/data/manifest.json');scope=load(proof['inputs']['scope_proof']['path'])
    if sha(scope['inputs']['iso_source']['path'])!=m['sourceHashes']['main_dxf']:raise ValueError('viewer and source drawing differ')
    return adopt(m['attributeValueContext'],load(Path(parent)/'public/data/graph.json'),proof,scope,sha(path))

def refresh(parent,output,proofpath,templates,port):
    parent,output,proofpath,templates=[Path(p).resolve()for p in [parent,output,proofpath,templates]]
    if output.exists()or output.with_suffix('.zip').exists():raise FileExistsError(output)
    verify_parent(parent);proof=verify_source(proofpath.parent);before=base.artifact_inventory(parent);m=load(parent/'public/data/manifest.json');context=context_from(parent,proof,proofpath);old=effective(parent)
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in MODULES:shutil.copy2(templates/n,output/n)
    app=output/'public/app.js';s=app.read_text(encoding='utf8');assert s.count("from './edge-attributes-reviewed-ring.js'")==1;s=s.replace("from './edge-attributes-reviewed-ring.js'","from './edge-attributes-expression-group.js'");app.write_text(s,encoding='utf8')
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode(revised));actual=effective(output);change=delta(old,actual,context)
    revised['preferredPort']=port;revised['templateHashes'].update({n:sha(output/n)for n in MODULES+['public/app.js']});revised['sourceHashes']['reviewed_expression_group_metrics']=sha(proofpath)
    revised['reviewContentHashes'].update(effective_edge_attributes=hashlib.sha256(encode(actual)).hexdigest(),attribute_value_context=hashlib.sha256(encode(context)).hexdigest())
    revised['reviewedExpressionGroupMetricRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],implementation_sha256=sha(__file__),native_metric_proof_sha256=sha(proofpath),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(proofpath),context=context,templates={n:sha(output/n)for n in MODULES+['public/app.js']},port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode(revised));index=output/'public/index.html';index.write_text(index.read_text(encoding='utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    folder=output/FOLDER;folder.mkdir();(folder/'current-effective.json').write_bytes(encode(actual));shutil.copy2(proofpath,folder/'native-proof.json')
    provider=load(parent/'expanded-main-seed-bend-refresh/provider-inventory.json');provider['reviewed_expression_group_metric_metadata']=dict(native_proof_sha256=sha(proofpath),shared_groups=len(proof['records']),axis_member_edges=len(change['group_metadata_edges']),per_axis_edge_values_assigned=0);(folder/'provider-inventory.json').write_bytes(encode(provider))
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=load(proof['inputs']['scope_proof']['path'])['inputs']['iso_source']['path'];doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('native source or bundle gate failed')
    if before!=base.artifact_inventory(parent):raise ValueError('parent mutated')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('old graph, data or annotations changed')
    audit=dict(mode=MODE,parent=str(parent),parent_files=before,proof_path=str(proofpath),proof_sha256=sha(proofpath),bundle_id=revised['bundleId'],delta=change,source_preflight=preflight,human_accepted=False,output_hashes=base.artifact_inventory(output));(output/AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    return audit

def verify(output):
    output=Path(output);a=load(output/AUDIT);p=Path(a['proof_path']);parent=Path(a['parent']);verify_parent(parent);proof=verify_source(p.parent);m=load(output/'public/data/manifest.json')
    if (a['mode']!=MODE or sha(p)!=a['proof_sha256']or a['bundle_id']!=m['bundleId']or m['reviewedExpressionGroupMetricRefresh']['implementation_sha256']!=sha(__file__)or base.artifact_inventory(parent)!=a['parent_files']or{n:h for n,h in base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']or context_from(parent,proof,p)!=m['attributeValueContext']or delta(effective(parent),effective(output),m['attributeValueContext'])!=a['delta']):raise ValueError('group viewer evidence or adoption differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=a['delta'],human_accepted=False)

def main():
    p=argparse.ArgumentParser()
    for n in ['parent','output','proof','templates','verify-output']:p.add_argument('--'+n,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify(a.verify_output)if a.verify_output else refresh(a.parent,a.output,a.proof,a.templates,a.port)
    print({k:v for k,v in r.items()if k in ['mode','status','artifact_replay','bundle_id','delta']},flush=True)
if __name__=='__main__':main()
