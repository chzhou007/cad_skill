"""Adopt only qualified horizontal DN; keep every length and vertical provider."""
import argparse,copy,hashlib,shutil,sys,zipfile
from pathlib import Path
for n in ['build-cad-pipe-topology','orchestrate-cad-drawing-pipeline']:sys.path.insert(0,str(Path(__file__).resolve().parents[2]/n/'scripts'))
from confirm_crossview_paths import load,sha,encode
from reviewed_uniform_subroute_DN import verify_output as verify_source,MODE as SOURCE_MODE
from refresh_reviewed_expression_group_metrics import verify as verify_parent
from refresh_reviewed_ring_partition_DN import effective
import refresh_attribute_templates as base
MODE='reviewed_uniform_lower_subroute_DN_viewer_v1';AUDIT='uniform-subroute-DN-refresh.json';FOLDER='uniform-subroute-DN-refresh'
MODULES=['public/edge-attributes-uniform-subroute.js','public/reviewed-uniform-subroute-DN.js']
FIELDS={'uniform_subroute_DN_scope_id','uniform_subroute_DN_domains_json','uniform_subroute_DN_plan_source_sha256'}
SCALARS={'diameter_nominal_mm','diameter_text','diameter_status'}

def adopt(context,graph,proof,bindings):
    if 'reviewed_uniform_subroute_DN'in context:raise ValueError('uniform subroute already adopted')
    if (proof['mode']!=SOURCE_MODE or proof['original_native_group_member_gate_and_caption_owners_reexecuted']is not True
        or proof['selected_prefix_mapping_freshly_requalified_by_native_group_boundaries_member_roles_and_caption_owners']is not True
        or proof['graph_mutated']is not False or proof['components_changed']is not False or proof['physical_lengths_assigned']!=0 or proof['vertical_values_assigned']!=0 or proof['human_accepted']is not False):raise ValueError('source qualification incomplete')
    result=copy.deepcopy(context);edges={e['edge_id']:e for e in graph['edges']};records=copy.deepcopy(proof['records']);vertical=[copy.deepcopy(s)for g in proof['groups']for s in g['excluded_vertical_domains']]
    for r in records:
        e=edges[r['axis_edge_id']]
        if (e['system']!=r['system']or e['floor_start']!=r['floor']or e['floor_end']!=r['floor']or [e['start_node_id'],e['end_node_id']]!=r['axis_nodes']or e['attribute_paths']!=r['axis_attribute_paths']or r['physical_length_mm']is not None or r['per_axis_edge_length_allocation']is not None or r['human_accepted']is not False):raise ValueError('current horizontal DN scope differs')
        for s in r['horizontal_segment_domains']:
            if s['direction_class']!='horizontal'or s['native_source_status']!='single_source_line_covers'or e['attribute_paths'][s['path_index']][s['segment_index']:s['segment_index']+2]!=s['scope_points']:raise ValueError('original horizontal source domain differs')
    if len({r['axis_edge_id']for r in records})!=len(records):raise ValueError('competing DN scope writers')
    result['reviewed_uniform_subroute_DN']=dict(mode='qualified_reviewed_uniform_lower_subroute_plan_DN_v1',records=records,count=len(records),excluded_vertical_domains=vertical,native_source_owners_reexecuted=True,selected_prefix_source_requalified=True,raw_graph_changed=False,physical_lengths_assigned=0,vertical_values_assigned=0,human_accepted=False,source_bindings=dict(bindings,rendered_attribute_graph=context['current_rendered_graph_sha256']))
    return result

def context_from(parent,proof,path):
    m=load(Path(parent)/'public/data/manifest.json')
    if sha(Path(parent)/'public/data/manifest.json')!=proof['inputs']['current_viewer_manifest']['sha256']:raise ValueError('source-qualified current viewer differs')
    group=load(proof['inputs']['group_metric_proof']['path']);scope=load(group['inputs']['scope_proof']['path'])
    if m['sourceHashes']['main_dxf']!=scope['inputs']['iso_source']['sha256']:raise ValueError('axis drawing changed')
    bindings=dict(native_DN_proof=sha(path),plan_source=scope['inputs']['plan_source']['sha256'],plan_graph=scope['inputs']['plan_graph']['sha256'],axis_source=scope['inputs']['iso_source']['sha256'],axis_graph=scope['inputs']['iso_graph']['sha256'])
    return adopt(m['attributeValueContext'],load(Path(parent)/'public/data/graph.json'),proof,bindings)

def delta(before,after,records):
    old={r['edge_id']:r['values']for r in before};new={r['edge_id']:r['values']for r in after};targets={r['axis_edge_id']:r for r in records};changed=[];whole=[]
    if old.keys()!=new.keys():raise ValueError('edge population changed')
    for eid,values in old.items():
        current=new[eid];row=targets.get(eid)
        if row is None:
            if current!=values:raise ValueError('unrelated old attribute changed '+eid)
            continue
        allowed=FIELDS|SCALARS if row['whole_horizontal_edge']else FIELDS
        if {k:v for k,v in current.items()if k not in allowed}!={k:v for k,v in values.items()if k not in allowed}:raise ValueError('old length, vertical or other attribute changed '+eid)
        if any(k not in current for k in FIELDS):raise ValueError('DN source metadata not adopted '+eid)
        if row['whole_horizontal_edge']:
            if values.get('diameter_nominal_mm')not in [None,'',row['nominal_mm']]:raise ValueError('old known DN conflict')
            if current.get('diameter_nominal_mm')!=row['nominal_mm']or current.get('diameter_text')!='DN'+str(int(row['nominal_mm'])):raise ValueError('whole horizontal DN not effectively adopted')
            if values.get('diameter_nominal_mm')in [None,'']:whole.append(eid)
        changed.append(eid)
    return dict(DN_scope_edges=sorted(changed),new_whole_horizontal_DN_edges=sorted(whole),old_known_DN_preserved=True,all_lengths_and_vertical_values_exact=True,new_physical_lengths=0,new_vertical_values=0,new_columns=3)

def refresh(parent,output,path,templates,port):
    parent,output,path,templates=[Path(p).resolve()for p in [parent,output,path,templates]]
    if output.exists()or output.with_suffix('.zip').exists():raise FileExistsError(output)
    verify_parent(parent);proof=verify_source(path.parent);before=base.artifact_inventory(parent);m=load(parent/'public/data/manifest.json');context=context_from(parent,proof,path);old=effective(parent);shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in MODULES:shutil.copy2(templates/n,output/n)
    app=output/'public/app.js';s=app.read_text(encoding='utf8');assert s.count("from './edge-attributes-expression-group.js'")==1;app.write_text(s.replace("from './edge-attributes-expression-group.js'","from './edge-attributes-uniform-subroute.js'"),encoding='utf8')
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode(revised));actual=effective(output);change=delta(old,actual,proof['records']);revised['preferredPort']=port;revised['templateHashes'].update({n:sha(output/n)for n in MODULES+['public/app.js']});revised['sourceHashes']['reviewed_uniform_subroute_DN']=sha(path);revised['reviewContentHashes'].update(effective_edge_attributes=hashlib.sha256(encode(actual)).hexdigest(),attribute_value_context=hashlib.sha256(encode(context)).hexdigest());revised['uniformSubrouteDNRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],implementation_sha256=sha(__file__),native_proof_sha256=sha(path),human_confirmation_inherited=False);revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(path),context=context,templates={n:sha(output/n)for n in MODULES+['public/app.js']},port=port))).hexdigest()[:20];(output/'public/data/manifest.json').write_bytes(encode(revised));index=output/'public/index.html';index.write_text(index.read_text(encoding='utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    folder=output/FOLDER;folder.mkdir();(folder/'current-effective.json').write_bytes(encode(actual));shutil.copy2(path,folder/'native-proof.json');provider=load(parent/'reviewed-expression-group-metric-refresh/provider-inventory.json');provider['uniform_subroute_DN_adoption']=dict(native_proof_sha256=sha(path),new_whole_horizontal_DN_edges=change['new_whole_horizontal_DN_edges'],scope_edge_count=len(proof['records']),vertical_values_assigned=0,new_lengths=0);provider['counts']['current_effective_whole_DN_known']=sum(isinstance(r['values'].get('diameter_nominal_mm'),(int,float))and r['values']['diameter_nominal_mm']>0 for r in actual);(folder/'provider-inventory.json').write_bytes(encode(provider))
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    group=load(proof['inputs']['group_metric_proof']['path']);scope=load(group['inputs']['scope_proof']['path']);source=scope['inputs']['iso_source']['path'];doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('native drawing gate failed')
    if before!=base.artifact_inventory(parent):raise ValueError('parent mutated')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('old graph/data/annotations changed')
    audit=dict(mode=MODE,parent=str(parent),parent_files=before,proof_path=str(path),proof_sha256=sha(path),bundle_id=revised['bundleId'],delta=change,source_preflight=preflight,human_accepted=False,output_hashes=base.artifact_inventory(output));(output/AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    return audit

def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);p=Path(a['proof_path']);verify_parent(parent);proof=verify_source(p.parent);m=load(output/'public/data/manifest.json')
    if (a['mode']!=MODE or sha(p)!=a['proof_sha256']or m['bundleId']!=a['bundle_id']or m['uniformSubrouteDNRefresh']['implementation_sha256']!=sha(__file__)or base.artifact_inventory(parent)!=a['parent_files']or {n:h for n,h in base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']or context_from(parent,proof,p)!=m['attributeValueContext']or delta(effective(parent),effective(output),proof['records'])!=a['delta']):raise ValueError('uniform DN viewer source or adoption differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=a['delta'],human_accepted=False)

def main():
    p=argparse.ArgumentParser()
    for n in ['parent','output','proof','templates','verify-output']:p.add_argument('--'+n,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify(a.verify_output)if a.verify_output else refresh(a.parent,a.output,a.proof,a.templates,a.port)
    print({k:v for k,v in r.items()if k in ['mode','status','artifact_replay','bundle_id','delta']},flush=True)
if __name__=='__main__':main()
