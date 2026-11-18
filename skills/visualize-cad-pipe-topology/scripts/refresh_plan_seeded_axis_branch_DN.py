"""Adopt plan-owned branch horizontals and retain drawing11 vertical evidence."""
import argparse,copy,hashlib,json,re,shutil,sys,zipfile
from pathlib import Path
for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/name/'scripts'))
from confirm_crossview_paths import load,sha,encode
from reapply_plan_seeded_axis_branch_DN import verify_output,MODE as NATIVE_MODE
from refresh_reviewed_ring_partition_DN import effective
from refresh_candidate_ring_DN import encode_manifest
from refresh_reviewed_fragment_detail import provider_binding
from current_effective_provider import reconcile
import refresh_attribute_templates as base

MODE='qualified_plan_seeded_axis_branch_DN_current_viewer_v1'
CONTEXT='plan_seeded_axis_branch_DN';AUDIT='plan-seeded-branch-DN-refresh.json';FOLDER='plan-seeded-branch-DN-refresh'
MODULES=['public/plan-seeded-branch-DN.js','public/edge-attributes-plan-seeded-branch.js']
FIELDS={'plan_branch_DN_scope_id','plan_branch_DN_T','plan_branch_DN_domains_json','plan_branch_DN_plan_source_sha256','plan_branch_DN_native_proof_sha256','plan_branch_DN_whole_physical_complete'}
SCALARS={'diameter_nominal_mm','diameter_text','diameter_status'}

def require(value,message):
    if not value:raise ValueError(message)

def retained_vertical_domains(edge,record,values,source_hash):
    """Exact source-domain partition, never just equal values or row counts."""
    horizontal={(s['path_index'],s['segment_index'])for s in record['horizontal_segment_domains']}
    display=(0,record['excluded_marker_display_segment'])
    expected={(pi,si)for pi,path in enumerate(edge['attribute_paths'])for si in range(len(path)-1)}-{display}-horizontal
    text=values.get('axis_rule_vertical_DN_segments_json','[]')
    rows=json.loads(text);require(isinstance(rows,list),'retained vertical source rows required')
    result=[]
    for pi,si in sorted(expected):
        matches=[r for r in rows if r.get('edge_id')==edge['edge_id']and r.get('path_index')==pi and r.get('segment_index')==si]
        if len(matches)!=1:return [],False
        row=matches[0]
        if (row.get('scope_points')!=edge['attribute_paths'][pi][si:si+2]or row.get('nominal_mm')!=record['nominal_mm']
            or row.get('system')!=edge['system']or row.get('axis_source_sha256')!=source_hash
            or row.get('human_accepted')is not False):return [],False
        result.append(dict(edge_id=edge['edge_id'],path_index=pi,segment_index=si,scope_points=copy.deepcopy(row['scope_points']),
            nominal_mm=row['nominal_mm'],system=row['system'],axis_source_sha256=source_hash,
            source_field='axis_rule_vertical_DN_segments_json',new_vertical_value_assigned=False))
    return result,True

def context_from(parent,proof,path,provider,old):
    parent=Path(parent);m=load(parent/'public/data/manifest.json');prior=m['attributeValueContext'];graph=load(parent/'public/data/graph.json')
    require(proof['mode']==NATIVE_MODE and proof['complete_original_plan_main_owners_independently_replayed']is True
        and proof['actual_current_main_contexts_exact']is True and proof['human_accepted']is False,'complete native main/branch owner replay required')
    require(sha(parent/'public/data/manifest.json')==proof['inputs']['viewer_manifest']['sha256']and CONTEXT not in prior,
            'plan-seeded branch source belongs to another viewer')
    require(proof['graph_mutated']is False and proof['components_changed']is False
        and proof['vertical_values_assigned']==proof['physical_lengths_assigned']==proof['individual_equipment_correspondences_assigned']==0,
            'unsupported source graph, vertical, length or identity change')
    received=load(proof['inputs']['received_proof']['path']);source=received['source_inputs']['plan_source'];plan_graph=received['source_inputs']['plan_graph']
    floors=[int(k.rsplit('_',1)[1])for k,v in provider['inputs'].items()if k.startswith('plan_source_')and v==source]
    require(len(floors)==1 and provider['inputs']['plan_graph_'+str(floors[0])]==plan_graph,'one current native plan source namespace required')
    edges={e['edge_id']:e for e in graph['edges']};values={r['edge_id']:r['values']for r in old};records=[]
    for native in proof['records']:
        eid=native['axis_edge_id'];edge=edges[eid]
        require(native['floor']==floors[0]and native['axis_attribute_paths']==edge['attribute_paths']
            and native['axis_nodes']==[edge['start_node_id'],edge['end_node_id']]and native['system']==edge['system'],
            'actual rendered branch geometry, floor or system differs')
        retained,complete=retained_vertical_domains(edge,native,values[eid],proof['inputs']['axis_source']['sha256'])
        records.append(dict(axis_edge_id=eid,axis_nodes=native['axis_nodes'],axis_attribute_paths=native['axis_attribute_paths'],
            system=native['system'],floor=native['floor'],nominal_mm=native['nominal_mm'],axis_T=native['axis_T'],
            main_arms=native['main_arms'],source_scope_id=native['main_source_scope_id'],
            horizontal_segment_domains=copy.deepcopy(native['horizontal_segment_domains']),
            excluded_marker_display_segment=native['excluded_marker_display_segment'],retained_vertical_domains=retained,
            whole_physical_DN_complete=complete,plan_source_sha256=source['sha256'],native_axis_source_sha256=proof['inputs']['axis_source']['sha256'],
            axis_labels_validation_only=True,individual_device_correspondence_assigned=False,new_vertical_values_assigned=0,
            physical_length_mm=None,related_HIL_confirmation_inherited=False,human_accepted=False))
    require(len({r['axis_edge_id']for r in records})==len(records),'competing branch DN writer')
    result=copy.deepcopy(prior);result[CONTEXT]=dict(mode=MODE,records=records,count=len(records),
        source_bindings=dict(native_proof=sha(path),parent_provider=sha(proof['inputs']['provider']['path']),
            native_axis_graph=proof['inputs']['axis_graph']['sha256'],native_axis_source=proof['inputs']['axis_source']['sha256'],
            rendered_graph=sha(parent/'public/data/graph.json'),attribute_context_graph=prior['current_rendered_graph_sha256'],
            plan_source=source['sha256'],plan_graph=plan_graph['sha256']),
        complete_original_native_replay=True,graph_mutated=False,vertical_values_assigned=0,physical_lengths_assigned=0,
        individual_device_correspondences_assigned=0,human_accepted=False)
    return result

def delta(previous,current,proof,context):
    old={r['edge_id']:r['values']for r in previous};new={r['edge_id']:r['values']for r in current}
    targets={r['axis_edge_id']:r for r in context[CONTEXT]['records']};promoted=[]
    require(old.keys()==new.keys(),'branch DN changed edge inventory')
    for eid,before in old.items():
        after=new[eid];row=targets.get(eid);allowed=FIELDS|(SCALARS if row and row['whole_physical_DN_complete']else set())
        require({k:v for k,v in after.items()if k not in allowed}=={k:v for k,v in before.items()if k not in allowed},
                'old length, vertical evidence, mapping or unrelated value changed '+eid)
        if row:
            require(json.loads(after.get('plan_branch_DN_domains_json','null'))==row and FIELDS<=after.keys(),'branch DN context not actually adopted '+eid)
            if row['whole_physical_DN_complete']:
                known=before.get('diameter_nominal_mm')
                require(known in(None,'',row['nominal_mm']),'old whole DN conflicts')
                require(after.get('diameter_nominal_mm')==row['nominal_mm'],'complete physical branch DN not effective')
                if known in(None,''):promoted.append(eid)
                else:require(all(after.get(k)==before.get(k)for k in SCALARS),'old scalar writer changed')
        else:require(not any(k in after for k in FIELDS),'branch DN escaped qualified source scope')
    return dict(new_whole_physical_DN_edges=sorted(promoted),qualified_branch_DN_edges=sorted(targets),
        new_horizontal_DN_domains=sum(len(r['horizontal_segment_domains'])for r in targets.values()),
        all_old_known_DN_values_preserved=True,all_old_lengths_vertical_values_and_mapping_fields_exact=True,
        new_lengths=0,new_vertical_values=0,new_individual_device_mappings=0,new_columns=len(FIELDS))

def provider_from(prior,proof,actual,context,path):
    result=reconcile(prior,actual,context)
    result['history_before_plan_seeded_branch_DN']=dict(counts=copy.deepcopy(prior['counts']),native_proof_sha256=sha(path))
    result['plan_seeded_axis_branch_DN_observations']=copy.deepcopy(context[CONTEXT]['records'])
    result['mode']=MODE
    for key in('records','ordinary_junction_mappings','member_domain_observations','all_current_vertical_DN_domains','current_component_inventory'):
        require(result[key]==prior[key],'branch scalar adoption changed mappings, components or vertical ownership')
    return result

def refresh(parent,output,path,provider,templates,port):
    parent,output,path,provider,templates=map(lambda p:Path(p).resolve(),(parent,output,path,provider,templates))
    require(not output.exists()and not output.with_suffix('.zip').exists(),'fresh branch DN viewer output required')
    before=base.artifact_inventory(parent);proof=verify_output(path.parent);binding=provider_binding(parent,provider)
    require(binding['provider']==proof['inputs']['provider'],'actual provider differs from native branch batch')
    old=effective(parent);context=context_from(parent,proof,path,load(provider),old);m=load(parent/'public/data/manifest.json')
    app=(parent/'public/app.js').read_text('utf8');imports=re.findall(r"from\s*['\"]\./(edge-attributes[A-Za-z0-9_.-]*\.js)['\"]",app)
    require(len(imports)==1,'one actual complete parent facade required')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in MODULES:shutil.copy2(templates/name,output/name)
    facade=output/MODULES[1];text=facade.read_text('utf8');require(text.count('./edge-attributes-nonnode-boundary.js')==2,'branch DN facade template differs')
    facade.write_text(text.replace('./edge-attributes-nonnode-boundary.js','./'+imports[0]),encoding='utf8')
    (output/'public/app.js').write_text(app.replace('./'+imports[0],'./edge-attributes-plan-seeded-branch.js'),encoding='utf8')
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode_manifest(revised))
    actual=effective(output);change=delta(old,actual,proof,context);revised['preferredPort']=port
    revised['templateHashes'].update({n:sha(output/n)for n in MODULES+['public/app.js']});revised['sourceHashes']['plan_seeded_axis_branch_DN']=sha(path)
    revised['reviewContentHashes'].update(effective_edge_attributes=hashlib.sha256(encode(actual)).hexdigest(),attribute_value_context=hashlib.sha256(encode(context)).hexdigest())
    revised['planSeededBranchDNRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(path),implementation=sha(__file__),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode_manifest(revised));index=output/'public/index.html';index.write_text(index.read_text('utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    folder=output/FOLDER;folder.mkdir();shutil.copy2(path,folder/'native-proof.json');(folder/'current-effective.json').write_bytes(encode(actual))
    (folder/'provider-inventory.json').write_bytes(encode(provider_from(load(provider),proof,actual,context,path)))
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source'];doc,preflight=read_source(source['path']);schema=validate_bundle(output,native_doc=doc,native_source_sha256=source['sha256'])
    (output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source['path'])
    require(schema['status']=='passed'and quality['machine_status']=='PASS','branch DN native source/viewer schema failed')
    require(base.artifact_inventory(parent)==before,'parent viewer mutated')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json':require(sha(output/n)==h,'old source data or annotation changed')
    audit=dict(mode=MODE,parent=str(parent),parent_files=before,proof_path=str(path),proof_sha256=sha(path),provider_binding=binding,
        bundle_id=revised['bundleId'],delta=change,source_preflight=preflight,graph_and_components_exact=True,human_accepted=False,whole_goal_complete=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED)as archive:
        for n in sorted(base.inventory(output)):archive.write(output/n,output.name+'/'+n)
    return audit

def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);path=Path(a['proof_path']);proof=verify_output(path.parent)
    m=load(output/'public/data/manifest.json');old=effective(parent);prior=load(a['provider_binding']['provider']['path'])
    require(a['mode']==MODE and m['planSeededBranchDNRefresh']['implementation_sha256']==sha(__file__)and sha(path)==a['proof_sha256']
        and m['bundleId']==a['bundle_id']and base.artifact_inventory(parent)==a['parent_files']
        and {n:h for n,h in base.artifact_inventory(output).items()if n!=AUDIT}==a['output_hashes'],'branch DN viewer binding changed')
    context=context_from(parent,proof,path,prior,old);require(context==m['attributeValueContext'],'branch DN context differs')
    actual=effective(output);require(delta(old,actual,proof,context)==a['delta'],'branch DN actual values differ')
    require(encode(provider_from(prior,proof,actual,context,path))==(output/FOLDER/'provider-inventory.json').read_bytes(),'branch DN current provider differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=a['delta'],human_accepted=False)

def main():
    p=argparse.ArgumentParser()
    for name in('parent','output','proof','parent-provider','templates','verify-output'):p.add_argument('--'+name,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        result=verify(a.verify_output)if a.verify_output else refresh(a.parent,a.output,a.proof,a.parent_provider,a.templates,a.port)
    print({k:v for k,v in result.items()if k in('status','artifact_replay','bundle_id','delta')},flush=True)
if __name__=='__main__':main()
