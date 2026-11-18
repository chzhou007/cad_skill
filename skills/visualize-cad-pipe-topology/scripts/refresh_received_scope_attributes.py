"""Adopt new uniform DN and group metrics without changing old source contexts."""
import argparse,collections,copy,hashlib,json,re,shutil,sys,zipfile
from pathlib import Path
for n in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):sys.path.insert(0,str(Path(__file__).resolve().parents[2]/n/'scripts'))
from confirm_crossview_paths import load,sha,encode
from reapply_received_scope_attributes import verify_output,MODE as NATIVE_MODE
from refresh_reviewed_ring_partition_DN import effective
from refresh_candidate_ring_DN import encode_manifest
from refresh_reviewed_fragment_detail import provider_binding
import refresh_uniform_subroute_DN as uniform
import refresh_reviewed_expression_group_metrics as metric
import refresh_attribute_templates as base

MODE='qualified_received_scope_attribute_current_viewer_v1';AUDIT='received-scope-attribute-refresh.json';FOLDER='received-scope-attribute-refresh'
MODULES=['public/received-scope-attributes.js','public/edge-attributes-received-scope.js']
UNIFORM={'received_scope_uniform_DN_scope_id','received_scope_uniform_DN_domains_json','received_scope_uniform_DN_plan_source_sha256'}
METRIC={'received_scope_metric_scope_ids','received_scope_metric_scopes_json','received_scope_metric_source_sha256'}
HOLD={'received_scope_direction_hold_json'};FIELDS=UNIFORM|METRIC|HOLD;SCALARS=uniform.SCALARS


def context_from(parent,proof,path):
    m=load(Path(parent)/'public/data/manifest.json');context=m['attributeValueContext'];graph=load(Path(parent)/'public/data/graph.json')
    if proof['mode']!=NATIVE_MODE or sha(Path(parent)/'public/data/manifest.json')!=proof['inputs']['viewer_manifest']['sha256']or sha(Path(parent)/'public/data/graph.json')!=proof['inputs']['rendered_graph']['sha256']:
        raise ValueError('received source qualification belongs to another current viewer')
    if any(k in context for k in('received_scope_uniform_DN','received_scope_group_metrics','received_scope_direction_holds')):
        raise ValueError('received range context already adopted')
    si=proof['source_inputs'];scope=load(proof['inputs']['received_scope_proof']['path']);result=copy.deepcopy(context)
    # Private typed views reuse both old constructors. Existing roots stay exact.
    private={k:copy.deepcopy(v)for k,v in context.items()if k!='reviewed_uniform_subroute_DN'}
    adapted=dict(mode=uniform.SOURCE_MODE,records=proof['records'],groups=proof['uniform_groups'],
        original_native_group_member_gate_and_caption_owners_reexecuted=proof['original_native_group_member_gate_caption_and_DN_owners_reexecuted'],
        selected_prefix_mapping_freshly_requalified_by_native_group_boundaries_member_roles_and_caption_owners=True,
        graph_mutated=proof['graph_mutated'],components_changed=proof['components_changed'],physical_lengths_assigned=0,vertical_values_assigned=0,human_accepted=False)
    bindings=dict(native_DN_proof=sha(path),plan_source=si['plan_source']['sha256'],plan_graph=si['plan_graph']['sha256'],axis_source=si['iso_source']['sha256'],axis_graph=si['iso_graph']['sha256'])
    result['received_scope_uniform_DN']=uniform.adopt(private,graph,adapted,bindings)['reviewed_uniform_subroute_DN']
    private={k:copy.deepcopy(v)for k,v in context.items()if k!='reviewed_expression_group_metrics'}
    adapted=dict(mode=metric.SOURCE_MODE,records=proof['new_metric_records'],original_native_group_owner_reexecuted=True,original_plan_metric_reader_reused=True,
        per_axis_edge_values_assigned=0,physical_lengths_assigned=0,DN_values_assigned=0,human_accepted=False,
        inputs=dict(plan_source=si['plan_source'],plan_graph=si['plan_graph'],scope_proof=proof['inputs']['received_scope_proof']))
    result['received_scope_group_metrics']=metric.adopt(private,graph,adapted,scope,sha(path))['reviewed_expression_group_metrics']
    result['received_scope_direction_holds']=copy.deepcopy(proof['held_direction_edges'])
    return result


def delta(previous,current,proof):
    old={r['edge_id']:r['values']for r in previous};new={r['edge_id']:r['values']for r in current}
    records={r['axis_edge_id']:r for r in proof['records']};targets={e for r in proof['new_metric_records']for e in r['axis_edges']};holds={r['edge_id']for r in proof['held_direction_edges']}
    if old.keys()!=new.keys():raise ValueError('edge inventory changed')
    promoted=[]
    for eid,before in old.items():
        after=new[eid];record=records.get(eid);allowed=FIELDS|(SCALARS if record and record['whole_horizontal_edge']else set())
        if {k:v for k,v in after.items()if k not in allowed}!={k:v for k,v in before.items()if k not in allowed}:
            raise ValueError('old length, vertical, source evidence or unrelated value changed '+eid)
        if set(after)-set(before)-allowed:raise ValueError('undeclared output field')
        if record:
            if not UNIFORM<=after.keys()or json.loads(after['received_scope_uniform_DN_domains_json'])!=record:
                raise ValueError('source-qualified DN context not actually adopted')
            if record['whole_horizontal_edge']:
                if before.get('diameter_nominal_mm')not in(None,'',record['nominal_mm']):raise ValueError('old known DN conflict')
                if after.get('diameter_nominal_mm')!=record['nominal_mm']:raise ValueError('whole horizontal DN not adopted')
                if before.get('diameter_nominal_mm')in(None,''):promoted.append(eid)
                elif any(after.get(k)!=before.get(k)for k in SCALARS):raise ValueError('old known scalar evidence changed')
        elif any(k in after for k in UNIFORM):raise ValueError('unqualified uniform DN metadata')
        if eid in targets:
            if not METRIC<=after.keys():raise ValueError('shared metric not adopted')
            rows=json.loads(after['received_scope_metric_scopes_json'])
            if any(r['per_axis_edge_length_allocation']is not None or r['aggregation_policy']!='count_once_per_scope_id_not_once_per_edge'for r in rows):raise ValueError('group quantity escaped to individual edge')
        elif any(k in after for k in METRIC):raise ValueError('metric escaped source range')
        if (eid in holds)!=('received_scope_direction_hold_json'in after):raise ValueError('direction hold not retained exactly')
        if eid in holds and json.loads(after['received_scope_direction_hold_json'])!=next(r for r in proof['held_direction_edges']if r['edge_id']==eid):
            raise ValueError('direction hold source evidence changed')
    return dict(new_whole_horizontal_DN_edges=sorted(promoted),new_uniform_scope_edges=sorted(records),new_group_metric_edges=sorted(targets),held_direction_edges=sorted(holds),
        all_old_lengths_vertical_values_and_source_fields_exact=True,all_old_known_DN_preserved=True,new_per_edge_lengths=0,new_vertical_values=0,new_columns=7)


def provider_from(prior,proof,actual,path):
    result=copy.deepcopy(prior);values={r['edge_id']:r['values']for r in actual};new={r['axis_edge_id']:r for r in proof['records']};remaining=[];completed=[]
    for previous in prior['remaining_horizontal_attributes']:
        row=copy.deepcopy(previous);eid=row['edge_id'];row['attributes']=copy.deepcopy(values[eid]);record=new.get(eid)
        if record and record['whole_horizontal_edge']:
            row['known_whole_DN']=values[eid]['diameter_nominal_mm']
            if row['complete_centerline']:completed.append(eid);continue
            row['next_scope']='reviewed_range_per_edge_length_allocation_unresolved'
            row['correspondence_observations'].append(dict(domain='reviewed_uniform_range_without_internal_node_pairing',scope_id=record['source_scope_id'],
                plan_edges=copy.deepcopy(record['plan_remaining_edges']),per_edge_length_allocation=None,ordinary_endpoint_mapping_assigned=False))
        remaining.append(row)
    result['history_before_received_scope_attributes']=dict(counts=copy.deepcopy(prior['counts']),frontier=copy.deepcopy(prior['current_horizontal_frontier']))
    result['remaining_horizontal_attributes']=remaining;counts=dict(collections.Counter(r['next_scope']for r in remaining))
    result['counts'].update(current_effective_whole_DN_known=sum(isinstance(r['values'].get('diameter_nominal_mm'),(int,float))and r['values']['diameter_nominal_mm']>0 for r in actual),
        pure_horizontal_complete_DN_and_centerline=prior['counts']['pure_horizontal_complete_DN_and_centerline']+len(completed),
        pure_horizontal_remaining_attributes=len(remaining),horizontal_next_scopes=counts)
    result['current_horizontal_frontier'].update(records=remaining,pure_horizontal_complete=result['counts']['pure_horizontal_complete_DN_and_centerline'],
        pure_horizontal_remaining_attributes=len(remaining),remaining_by_next_scope=counts,remaining_by_floor=dict(collections.Counter(str(r['floor'])for r in remaining)))
    result.update(mode=MODE,received_uniform_range_DN_observations=copy.deepcopy(proof['records']),received_scope_direction_holds=copy.deepcopy(proof['held_direction_edges']),
        received_scope_group_metrics=dict(native_proof_sha256=sha(path),records=copy.deepcopy(proof['new_metric_records']),aggregation_policy='count_once_per_scope_id_not_once_per_edge',per_edge_lengths_assigned=0))
    for key in('records','member_domain_observations','ordinary_junction_mappings','current_component_inventory'):
        if result[key]!=prior[key]:raise ValueError('received attributes changed mapping identities or components')
    return result


def group_export(context):
    rows=[*context['reviewed_expression_group_metrics']['records'],*context['received_scope_group_metrics']['records']]
    if len({r['scope_id']for r in rows})!=len(rows):raise ValueError('duplicate group aggregation identity')
    return dict(mode='source_qualified_shared_plan_LINE_fragment_metrics_count_once_v1',aggregation_policy='count_once_per_scope_id_not_once_per_edge',
        records=copy.deepcopy(rows),per_axis_edge_length_allocation=None,complete_installed_lengths_unknown=True,human_accepted=False)


def refresh(parent,output,path,provider,templates,port):
    parent,output,path,provider,templates=map(lambda p:Path(p).resolve(),(parent,output,path,provider,templates))
    if output.exists()or output.with_suffix('.zip').exists():raise FileExistsError(output)
    before=base.artifact_inventory(parent);proof=verify_output(path.parent);binding=provider_binding(parent,provider)
    if binding['provider']!=proof['inputs']['provider']:raise ValueError('current actual provider differs from native batch')
    context=context_from(parent,proof,path);m=load(parent/'public/data/manifest.json');old=effective(parent);app=(parent/'public/app.js').read_text('utf8')
    imports=re.findall(r"from\s*['\"]\./(edge-attributes[A-Za-z0-9_.-]*\.js)['\"]",app)
    if len(imports)!=1:raise ValueError('one actual complete parent facade required')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in MODULES:shutil.copy2(templates/n,output/n)
    facade=output/MODULES[1];text=facade.read_text('utf8')
    if text.count('./edge-attributes-candidate-ring.js')!=2:raise ValueError('received facade template changed')
    facade.write_text(text.replace('./edge-attributes-candidate-ring.js','./'+imports[0]),encoding='utf8')
    (output/'public/app.js').write_text(app.replace('./'+imports[0],'./edge-attributes-received-scope.js'),encoding='utf8')
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode_manifest(revised))
    actual=effective(output);change=delta(old,actual,proof);changed={n:sha(output/n)for n in MODULES+['public/app.js']}
    revised['preferredPort']=port;revised['templateHashes'].update(changed);revised['sourceHashes']['received_scope_attributes']=sha(path)
    revised['reviewContentHashes'].update(effective_edge_attributes=hashlib.sha256(encode(actual)).hexdigest(),attribute_value_context=hashlib.sha256(encode(context)).hexdigest())
    revised['receivedScopeAttributeRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(path),implementation=sha(__file__),templates=changed,port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode_manifest(revised));index=output/'public/index.html';html=index.read_text('utf8').replace(m['bundleId'],revised['bundleId'])
    marker='<button data-export="instances">Component instances · CSV</button>'
    if html.count(marker)!=1:raise ValueError('actual export menu differs')
    html=html.replace(marker,marker+'<a href="data/received-scope-group-metrics.json" download style="display:block;padding:8px 12px;color:inherit;text-decoration:none">&#20849;&#20139;&#33539;&#22260;&#37327;&#27979; &#183; JSON</a>')
    index.write_text(html,encoding='utf8');(output/'public/data/received-scope-group-metrics.json').write_bytes(encode(group_export(context)))
    folder=output/FOLDER;folder.mkdir();shutil.copy2(path,folder/'native-proof.json');(folder/'current-effective.json').write_bytes(encode(actual));(folder/'provider-inventory.json').write_bytes(encode(provider_from(load(provider),proof,actual,path)))
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['source_inputs']['iso_source'];doc,preflight=read_source(source['path']);schema=validate_bundle(output,native_doc=doc,native_source_sha256=source['sha256']);(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source['path'])
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('received attribute native source/schema gate failed')
    if base.artifact_inventory(parent)!=before:raise ValueError('parent bundle mutated')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('old source data or annotations changed')
    audit=dict(mode=MODE,parent=str(parent),parent_files=before,proof_path=str(path),proof_sha256=sha(path),provider_binding=binding,bundle_id=revised['bundleId'],
        delta=change,source_preflight=preflight,components_and_graph_exact=True,human_accepted=False,whole_goal_complete=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    return audit


def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);path=Path(a['proof_path']);proof=verify_output(path.parent);m=load(output/'public/data/manifest.json')
    if (a['mode']!=MODE or m['receivedScopeAttributeRefresh']['implementation_sha256']!=sha(__file__)or sha(path)!=a['proof_sha256']or m['bundleId']!=a['bundle_id']
        or base.artifact_inventory(parent)!=a['parent_files']or {n:h for n,h in base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']
        or context_from(parent,proof,path)!=m['attributeValueContext']or delta(effective(parent),effective(output),proof)!=a['delta']
        or encode(group_export(m['attributeValueContext']))!=(output/'public/data/received-scope-group-metrics.json').read_bytes()):
        raise ValueError('received scope viewer replay differs')
    expected=provider_from(load(a['provider_binding']['provider']['path']),proof,effective(output),path)
    if encode(expected)!=(output/FOLDER/'provider-inventory.json').read_bytes():raise ValueError('received scope current provider replay differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=a['delta'],human_accepted=False)


def main():
    p=argparse.ArgumentParser()
    for n in('parent','output','proof','parent-provider','templates','verify-output'):p.add_argument('--'+n,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify(a.verify_output)if a.verify_output else refresh(a.parent,a.output,a.proof,a.parent_provider,a.templates,a.port)
    print({k:v for k,v in r.items()if k in('status','artifact_replay','bundle_id','delta')},flush=True)
if __name__=='__main__':main()
