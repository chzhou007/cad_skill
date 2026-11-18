"""Publish separately owned plan horizontals and native drawing11 verticals.

The original contexts, source graph, components, length writers and individual
correspondence remain immutable. A partly classified main receives only its
already horizontal domains, never a whole-edge scalar.
"""
import argparse,copy,hashlib,json,math,re,shutil,sys,zipfile
from pathlib import Path
for name in ('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/name/'scripts'))
from confirm_crossview_paths import load,sha,encode
from native_replay_session import verify_once
from reapply_inherited_branch_attribute_entries import verify_output as native_verify,MODE as NATIVE_MODE
from refresh_reviewed_ring_partition_DN import effective
from refresh_candidate_ring_DN import encode_manifest
from refresh_reviewed_fragment_detail import provider_binding
from current_effective_provider import reconcile
import refresh_attribute_templates as base

MODE='qualified_inherited_branch_attribute_entries_current_viewer_v1'
CONTEXT='inherited_branch_attribute_entries'
FOLDER='inherited-branch-entries-refresh';AUDIT=FOLDER+'.json'
MODULES=['public/inherited-branch-entries-DN.js','public/edge-attributes-inherited-entries.js','public/checked-source-connection-display.js']
FIELDS={'inherited_entry_DN_scope_id','inherited_entry_DN_T','inherited_entry_DN_domains_json',
    'inherited_entry_DN_plan_source_sha256','inherited_entry_DN_native_proof_sha256','inherited_entry_DN_whole_physical_complete',
    'inherited_entry_vertical_DN_segments_json','inherited_entry_vertical_DN_axis_source_sha256','inherited_entry_vertical_DN_native_proof_sha256'}
SCALARS={'diameter_nominal_mm','diameter_text','diameter_status'}

def require(value,message):
    if not value:raise ValueError(message)

def domain_key(row):return row['path_index'],row['segment_index']

def check_domain(edge,row):
    require(row['edge_id']==edge['edge_id']and row['system']==edge['system']
        and row['scope_points']==edge['attribute_paths'][row['path_index']][row['segment_index']:row['segment_index']+2],
        'native source domain differs from the rendered edge')

def context_from(parent,proof,path,provider,old):
    parent=Path(parent);m=load(parent/'public/data/manifest.json');prior=m['attributeValueContext'];graph=load(parent/'public/data/graph.json')
    require(proof['mode']==NATIVE_MODE and proof['complete_current_native_viewer_and_vertical_parents_replayed']is True
        and proof['all_previous_source_branch_payloads_exact']is True and proof['source_graph_and_original_routes_unchanged']is True
        and proof['raw_normalization_gap_never_promoted_to_measured_LINE']is True and proof['vertical_values_from_axis11_only']is True,
        'original source, branch and vertical parents must be independently replayed')
    require(proof['graph_mutated']is False and proof['components_changed']is False and proof['human_accepted']is False
        and proof['physical_lengths_assigned']==proof['individual_device_mappings_assigned']==0,'unsupported source graph, length or identity change')
    require(CONTEXT not in prior and sha(parent/'public/data/manifest.json')==proof['inputs']['viewer_manifest']['sha256'],
        'new source composition belongs to another current viewer')
    require(encode(old)==Path(proof['inputs']['current_effective']['path']).read_bytes(),'native composition used another current effective parent')
    received=load(proof['inputs']['received_attribute_proof']['path']);plan=received['source_inputs']['plan_source'];plan_graph=received['source_inputs']['plan_graph']
    floors=[int(k.rsplit('_',1)[1])for k,v in provider['inputs'].items()if k.startswith('plan_source_')and v==plan]
    require(len(floors)==1 and provider['inputs']['plan_graph_'+str(floors[0])]==plan_graph,'unique current native plan namespace required')
    source_hash=proof['inputs']['axis_source']['sha256'];proof_hash=sha(path)
    edges={e['edge_id']:e for e in graph['edges']};values={r['edge_id']:r['values']for r in old};records=[];used_vertical=[]
    new_vertical={}
    for row in proof['new_vertical_records']:
        key=(row['edge_id'],*domain_key(row));require(key not in new_vertical,'competing independently qualified vertical domain')
        require(row['source']=='axis11_original_native_caption_T_and_replayed_normalization'and row['raw_source_coverage_not_promoted']is True
            and row['physical_length_mm']is None and row['whole_edge_DN_assigned']is False and row['human_accepted']is False,
            'new vertical cannot claim a length, raw coverage, HIL or whole-edge value')
        new_vertical[key]=row
    for kind,natives in [('branch',proof['records']),('partial_main',proof['new_partial_main_records'])]:
        for native in natives:
            eid=native['axis_edge_id'];edge=edges[eid];nominal=native['nominal_mm']
            require(type(nominal)in(int,float)and math.isfinite(nominal)and nominal>0 and native['floor']==floors[0]
                and edge['floor_start']==edge['floor_end']==native['floor']and native['system']==edge['system']
                and native['axis_attribute_paths']==edge['attribute_paths']and native['axis_nodes']==[edge['start_node_id'],edge['end_node_id']],
                'actual source branch geometry, nominal DN, floor or system differs')
            horizontal=copy.deepcopy(native['horizontal_segment_domains']);seen=set()
            for row in horizontal:
                check_domain(edge,row);key=domain_key(row)
                require(key not in seen and row['direction_class']=='horizontal'and row['native_source_status']=='single_source_line_covers',
                    'new horizontal value lacks a unique original horizontal domain')
                seen.add(key)
            require(bool(horizontal),'source record has no qualified horizontal domains')
            expected={(pi,si)for pi,p in enumerate(edge['attribute_paths'])for si in range(len(p)-1)};retained=[];added=[]
            excluded=copy.deepcopy(native.get('excluded_other_direction_domains',[]));display=native.get('excluded_marker_display_segment')
            if kind=='branch':
                require(len(edge['attribute_paths'])==1 and (0,display)in expected and not excluded,'one original marker display domain required')
                expected.remove((0,display));require(seen<=expected,'horizontal DN cannot cover a marker display interior')
                prior_vertical=json.loads(values[eid].get('axis_rule_vertical_DN_segments_json','[]'))
                require(isinstance(prior_vertical,list),'retained original vertical domains must be a list')
                for key in sorted(expected-seen):
                    original=[r for r in prior_vertical if r.get('edge_id')==eid and domain_key(r)==key]
                    fresh=new_vertical.get((eid,*key));require(not(original and fresh),'new vertical competes with a retained original owner')
                    if fresh:
                        check_domain(edge,fresh);require(fresh['nominal_mm']==nominal,'independent plan/axis vertical DN conflict')
                        row=copy.deepcopy(fresh);row.update(direction_class='vertical',axis_source_sha256=source_hash,
                            native_proof_sha256=proof_hash,source_field='inherited_entry_vertical_DN_segments_json',new_vertical_value_assigned=True)
                        added.append(row);used_vertical.append((eid,*key));seen.add(key)
                    elif len(original)==1:
                        v=original[0];check_domain(edge,v)
                        require(v['nominal_mm']==nominal and v['axis_source_sha256']==source_hash and v['human_accepted']is False,
                            'retained axis11 source or DN conflicts with the plan horizontal domain')
                        retained.append(dict(edge_id=eid,path_index=key[0],segment_index=key[1],scope_points=copy.deepcopy(v['scope_points']),
                            nominal_mm=nominal,system=edge['system'],axis_source_sha256=source_hash,
                            source_field='axis_rule_vertical_DN_segments_json',new_vertical_value_assigned=False));seen.add(key)
                    else:require(not original,'duplicate retained vertical source domains')
                complete=seen==expected
            else:
                require(display is None and excluded and native['whole_horizontal_edge']is False
                    and native['original_direction_thresholds_unchanged']is True,'partial main must retain its original unresolved direction domains')
                for row in excluded:
                    check_domain(edge,row);key=domain_key(row)
                    require(key not in seen and row['direction_class']in('vertical','undetermined')and row['new_DN_assigned']is None
                        and row['physical_length_mm']is None,'partial main reclassified or filled another direction domain')
                    seen.add(key)
                require(seen==expected,'partial main source partition incomplete');complete=False
            records.append(dict(kind=kind,axis_edge_id=eid,axis_nodes=copy.deepcopy(native['axis_nodes']),axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),
                system=edge['system'],floor=native['floor'],nominal_mm=nominal,axis_T=native.get('axis_T'),main_arms=copy.deepcopy(native.get('main_arms',[])),
                source_scope_id=native.get('main_source_scope_id',native.get('source_scope_id')),horizontal_segment_domains=horizontal,
                excluded_marker_display_segment=display,retained_vertical_domains=retained,new_axis11_vertical_domains=added,
                excluded_other_direction_domains=excluded,whole_physical_DN_complete=complete,plan_source_sha256=plan['sha256'],axis_source_sha256=source_hash,
                axis_labels_validation_only=True,individual_device_correspondence_assigned=False,physical_length_mm=None,
                related_HIL_confirmation_inherited=False,human_accepted=False))
    require(len({r['axis_edge_id']for r in records})==len(records),'competing branch/partial-main writer')
    require(set(used_vertical)==set(new_vertical)and len(used_vertical)==len(new_vertical),'not every new independent vertical domain was used exactly once')
    result=copy.deepcopy(prior);result[CONTEXT]=dict(mode=MODE,records=records,count=len(records),
        source_bindings=dict(native_proof=proof_hash,parent_provider=proof['inputs']['provider']['sha256'],native_axis_graph=proof['inputs']['axis_graph']['sha256'],
            native_axis_source=source_hash,rendered_graph=sha(parent/'public/data/graph.json'),attribute_context_graph=prior['current_rendered_graph_sha256'],
            plan_source=plan['sha256'],plan_graph=plan_graph['sha256']),complete_original_native_replay=True,all_previous_source_branch_payloads_exact=True,
        graph_mutated=False,components_changed=False,new_axis11_vertical_domains=len(new_vertical),physical_lengths_assigned=0,
        individual_device_mappings_assigned=0,human_accepted=False)
    # A freshly replayed native owner may return tuples inside its full
    # normalization evidence. The manifest/Node boundary represents those
    # as arrays. Compare the actual serializable context on both sides,
    # retaining the complete evidence rather than dropping nested fields.
    return json.loads(encode(result))

def delta(previous,current,context):
    old={r['edge_id']:r['values']for r in previous};new={r['edge_id']:r['values']for r in current};targets={r['axis_edge_id']:r for r in context[CONTEXT]['records']}
    require(old.keys()==new.keys(),'source entry adoption changed edge inventory');promoted=[];changed=[]
    for eid,before in old.items():
        after=new[eid];row=targets.get(eid);allowed=FIELDS|(SCALARS if row and row['whole_physical_DN_complete']else set())
        require({k:v for k,v in after.items()if k not in allowed}=={k:v for k,v in before.items()if k not in allowed},
            'old lengths, vertical source cells, mapping or unrelated values changed '+eid)
        if row:
            require(json.loads(after.get('inherited_entry_DN_domains_json','null'))==row,'new source record not actually adopted '+eid)
            if row['new_axis11_vertical_domains']:
                require(json.loads(after.get('inherited_entry_vertical_DN_segments_json','null'))==row['new_axis11_vertical_domains'],
                    'new native drawing11 vertical source fields are not effective')
            else:require(not any(k in after for k in FIELDS if k.startswith('inherited_entry_vertical')),'new vertical field escaped its source domain')
            if row['whole_physical_DN_complete']:
                known=before.get('diameter_nominal_mm');require(known in(None,'',row['nominal_mm']),'old whole-edge DN conflicts')
                require(after.get('diameter_nominal_mm')==row['nominal_mm'],'complete branch DN not effective '+eid)
                if known in(None,''):promoted.append(eid)
                else:require(all(after.get(k)==before.get(k)for k in SCALARS),'old scalar writer changed')
        else:require(not any(k in after for k in FIELDS),'new source entry escaped its qualified scope')
        changed.extend(dict(edge_id=eid,field=k,before=before.get(k),after=after.get(k))for k in sorted(set(before)|SCALARS)if before.get(k)!=after.get(k))
    return dict(new_whole_DN_edges=sorted(promoted),new_horizontal_DN_domains=sum(len(r['horizontal_segment_domains'])for r in targets.values()),
        new_axis11_vertical_domains=sum(len(r['new_axis11_vertical_domains'])for r in targets.values()),
        partial_main_edges=[r['axis_edge_id']for r in targets.values()if r['kind']=='partial_main'],old_field_changes=changed,
        all_old_lengths_vertical_source_fields_components_and_mappings_exact=True,new_lengths=0,new_individual_device_mappings=0,new_columns=len(FIELDS))

def provider_from(prior,proof,actual,context,path):
    result=reconcile(prior,actual,context);n=proof['counts']['new_axis11_vertical_domains']
    require(prior['counts']['all_current_vertical_DN_domains']==prior['all_current_vertical_DN_domains']==proof['counts']['previous_known_vertical_domains'],
        'current provider vertical parent differs from the independently replayed source parent')
    result['history_before_inherited_branch_entries']=dict(counts=copy.deepcopy(prior['counts']),native_proof_sha256=sha(path))
    result['mode']=MODE;result['inherited_branch_attribute_entry_observations']=copy.deepcopy(context[CONTEXT]['records'])
    result['all_current_vertical_DN_domains']+=n;result['counts']['all_current_vertical_DN_domains']+=n
    result['new_inherited_entry_axis11_vertical_domains']=copy.deepcopy(proof['new_vertical_records'])
    for key in ('records','ordinary_junction_mappings','member_domain_observations','current_component_inventory'):
        require(result[key]==prior[key],'new DN source entry changed mappings, components or source observations')
    return result

def qualify_connection_display(app):
    """Retain legacy raw-coverage evidence while displaying the new proof scope."""
    marker='    const connection=e.source_wave_omission'
    header='    header.innerHTML=`<div class="detail-eyebrow"><h2>Pipe details</h2>'
    require(app.count(marker)==1 and app.count(header)==1,'one original source-coverage connection header required')
    require('checked-source-connection-display.js'not in app,'connection display already decorated')
    app="import {localConnectionDescription} from './checked-source-connection-display.js';\n"+app
    app=app.replace(marker,'    const rawSourceConnection=e.source_wave_omission')
    return app.replace(header,'    const connection=localConnectionDescription(e,data.attribute_value_context,crossViewAttributeCsvValues(e,data.attribute_value_context),zh,rawSourceConnection);\n'+header)

def bundle_identity(parent_bundle,proof_digest,implementation,port,ui_hashes):
    return hashlib.sha256(encode(dict(parent=parent_bundle,proof=proof_digest,implementation=implementation,port=port,ui_modules=ui_hashes))).hexdigest()[:20]

def refresh(parent,output,path,provider,templates,port):
    parent,output,path,provider,templates=map(lambda p:Path(p).resolve(),(parent,output,path,provider,templates))
    require(not output.exists()and not output.with_suffix('.zip').exists(),'fresh inherited-entry viewer output required')
    before=base.artifact_inventory(parent);proof=verify_once(path.parent,native_verify);binding=provider_binding(parent,provider)
    require(binding['provider']==proof['inputs']['provider'],'current provider differs from the independently replayed source composition')
    old=effective(parent);context=context_from(parent,proof,path,load(provider),old);m=load(parent/'public/data/manifest.json')
    app=(parent/'public/app.js').read_text('utf8');imports=re.findall(r"from\s*['\"]\./(edge-attributes[A-Za-z0-9_.-]*\.js)['\"]",app)
    require(len(imports)==1,'one actual parent attribute facade required')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in MODULES:shutil.copy2(templates/name,output/name)
    facade=output/MODULES[1];text=facade.read_text('utf8');require(text.count('./edge-attributes-plan-seeded-branch.js')==2,'inherited source facade template differs')
    facade.write_text(text.replace('./edge-attributes-plan-seeded-branch.js','./'+imports[0]),encoding='utf8')
    (output/'public/app.js').write_text(qualify_connection_display(app.replace('./'+imports[0],'./edge-attributes-inherited-entries.js')),encoding='utf8')
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode_manifest(revised))
    actual=effective(output);change=delta(old,actual,context);revised['preferredPort']=port
    ui_hashes={n:sha(output/n)for n in MODULES+['public/app.js']}
    revised['templateHashes'].update(ui_hashes);revised['sourceHashes']['inherited_branch_attribute_entries']=sha(path)
    revised['reviewContentHashes'].update(effective_edge_attributes=hashlib.sha256(encode(actual)).hexdigest(),attribute_value_context=hashlib.sha256(encode(context)).hexdigest())
    revised['inheritedBranchAttributeEntryRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=bundle_identity(m['bundleId'],sha(path),sha(__file__),port,ui_hashes)
    (output/'public/data/manifest.json').write_bytes(encode_manifest(revised));index=output/'public/index.html';index.write_text(index.read_text('utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    folder=output/FOLDER;folder.mkdir();shutil.copy2(path,folder/'native-proof.json');(folder/'current-effective.json').write_bytes(encode(actual))
    (folder/'provider-inventory.json').write_bytes(encode(provider_from(load(provider),proof,actual,context,path)))
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source'];doc,preflight=read_source(source['path']);schema=validate_bundle(output,native_doc=doc,native_source_sha256=source['sha256'])
    (output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source['path'])
    require(schema['status']=='passed'and quality['machine_status']=='PASS','new source entry viewer schema/source comparison failed')
    require(base.artifact_inventory(parent)==before,'published parent viewer mutated')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json':require(sha(output/n)==h,'old source data or annotations changed')
    audit=dict(mode=MODE,parent=str(parent),parent_files=before,proof_path=str(path),proof_sha256=sha(path),provider_binding=binding,
        bundle_id=revised['bundleId'],delta=change,source_preflight=preflight,graph_and_components_exact=True,human_accepted=False,whole_goal_complete=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED)as archive:
        for n in sorted(base.inventory(output)):archive.write(output/n,output.name+'/'+n)
    return audit

def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);path=Path(a['proof_path']);proof=verify_once(path.parent,native_verify)
    m=load(output/'public/data/manifest.json');old=effective(parent);prior=load(a['provider_binding']['provider']['path'])
    require(a['mode']==MODE and m['inheritedBranchAttributeEntryRefresh']['implementation_sha256']==sha(__file__)and sha(path)==a['proof_sha256']
        and m['bundleId']==a['bundle_id']and base.artifact_inventory(parent)==a['parent_files']
        and {n:h for n,h in base.artifact_inventory(output).items()if n!=AUDIT}==a['output_hashes'],'new entry viewer binding changed')
    context=context_from(parent,proof,path,prior,old);require(context==m['attributeValueContext'],'new source entry context differs')
    actual=effective(output);require(delta(old,actual,context)==a['delta'],'actual facade values differ')
    require(encode(provider_from(prior,proof,actual,context,path))==(output/FOLDER/'provider-inventory.json').read_bytes(),'current provider differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=a['delta'],human_accepted=False)

def main():
    p=argparse.ArgumentParser()
    for name in ('parent','output','proof','parent-provider','templates','verify-output'):p.add_argument('--'+name,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        result=verify(a.verify_output)if a.verify_output else refresh(a.parent,a.output,a.proof,a.parent_provider,a.templates,a.port)
    print({k:v for k,v in result.items()if k in ('status','artifact_replay','bundle_id','delta')},flush=True)
if __name__=='__main__':main()
