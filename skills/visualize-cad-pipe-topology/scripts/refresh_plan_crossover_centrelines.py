"""Adopt independently checked native DN rules without changing prior values."""
import copy,hashlib,json,shutil,subprocess
from pathlib import Path
import refresh_anchored_terminal_branches as prior
from reapply_plan_crossover_centerlines import verify_output,MODE as NATIVE_MODE
sha,load,encode=prior.sha,prior.load,prior.encode
MODE='native_plan_crossover_centreline_viewer_v1'
AUDIT='native-plan-crossover-centreline-refresh.json';EVIDENCE='plan-crossover-centreline-refresh'
FIELDS={'plan_crossover_complete_XY_centerline_mm','plan_crossover_centerline_evidence_json','plan_crossover_centerline_source_sha256'}
TEMPLATES=('public/plan-crossover-centreline.js','public/edge-attributes-plan-crossover.js')
key=lambda r:(r['edge_id'],r['path_index'],r['segment_index'])

def effective(bundle):
    bundle=Path(bundle);facade='edge-attributes-plan-crossover.js' if (bundle/'public/edge-attributes-plan-crossover.js').exists() else 'edge-attributes-axis-rule.js'
    js="import fs from'node:fs';import{pathToFileURL}from'node:url';const p=process.argv[1],m=JSON.parse(fs.readFileSync(p+'/public/data/manifest.json')),g=JSON.parse(fs.readFileSync(p+'/public/data/graph.json')),a=await import(pathToFileURL(p+'/public/"+facade+"'));console.log(JSON.stringify(g.edges.map(e=>({edge_id:e.edge_id,values:a.crossViewAttributeCsvValues(e,m.attributeValueContext)}))))"
    result=subprocess.run(['node','--input-type=module','-e',js,str(bundle)],capture_output=True,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('complete actual attribute reader failed: '+result.stderr)
    return json.loads(result.stdout)

def context_from(parent,proof,path):
    parent=Path(parent);m=load(parent/'public/data/manifest.json');context=copy.deepcopy(m['attributeValueContext']);g=load(parent/'public/data/graph.json');edges={e['edge_id']:e for e in g['edges']}
    if proof['mode']!=NATIVE_MODE or proof['complete_original_member_batch_replayed'] is not True or proof['old_complete_lengths_not_targeted'] is not True or any(proof[k]!=0 for k in ('DN_values_assigned','vertical_values_assigned','installed_lengths_assigned','physical_gap_lengths_assigned'))or proof['source_graphs_mutated']is not False or proof['human_accepted']is not False or 'plan_crossover_centrelines'in context:raise ValueError('invalid source XY centreline adoption contract')
    if any(sha(v['path'])!=v['sha256']for v in proof['inputs'].values())or sha(parent/'public/data/manifest.json')!=proof['inputs']['parent_viewer_manifest']['sha256']:raise ValueError('original source/parent changed')
    if sha(parent/'public/data/graph.json')!=context['current_rendered_graph_sha256']or proof['parent_bundle_id']!=m['bundleId']:raise ValueError('current rendered graph/parent differs')
    rows=[]
    for r in proof['records']:
        e=edges[r['axis_edge_id']];metric=r['metric']
        if r['axis_nodes']!=[e['start_node_id'],e['end_node_id']]or r['axis_attribute_paths']!=e['attribute_paths']or r['system']!=e['system']or any(e[k]!=r['floor']for k in('floor_start','floor_end'))or r['complete_horizontal_centerline_projection_mm']!=metric['complete_horizontal_centerline_projection_mm']or not metric['crossover_projections']:raise ValueError('current XY source domain differs')
        if r['installed_length_mm']is not None or r['net_pipe_cut_length_mm']is not None or r['related_HIL_confirmation_inherited']is not False or r['DN_changed']is not False or metric['measurement_kind']!='floor_plan_complete_XY_centerline_projection_not_installed_length':raise ValueError('XY projection is not an installed length or DN change')
        rows.append(copy.deepcopy(r))
    if len(rows)!=proof['counts']['new_complete_XY_projections']or len({r['axis_edge_id']for r in rows})!=len(rows):raise ValueError('complete unique XY source population required')
    context['plan_crossover_centrelines']=dict(mode='qualified_plan_crossover_complete_XY_centrelines_v1',records=rows,count=len(rows),source_bindings=dict(native_axis_graph=proof['inputs']['axis_graph']['sha256'],rendered_graph=sha(parent/'public/data/graph.json'),native_proof=sha(path)),DN_values_assigned=0,vertical_values_assigned=0,installed_lengths_assigned=0,physical_gap_lengths_assigned=0,source_graphs_mutated=False,human_accepted=False)
    # Native profile/T readers may return tuples. Compare and publish their
    # actual JSON wire shape, as the older metric adoption owner already does.
    return json.loads(encode(context))

def delta(before,after,context):
    old={r['edge_id']:r['values']for r in before};new={r['edge_id']:r['values']for r in after};rows={r['axis_edge_id']:r for r in context['plan_crossover_centrelines']['records']};changed=[]
    if old.keys()!=new.keys():raise ValueError('edge population changed')
    for eid,values in old.items():
        actual=new[eid]
        if {k:v for k,v in actual.items()if k not in FIELDS}!=values:raise ValueError('historical effective attribute changed '+eid)
        if eid in rows:
            r=rows[eid]
            if actual.get('plan_crossover_complete_XY_centerline_mm')!=r['complete_horizontal_centerline_projection_mm']or json.loads(actual.get('plan_crossover_centerline_evidence_json','null'))!=r or actual.get('plan_crossover_centerline_source_sha256')!=r['plan_source_sha256']:raise ValueError('source-qualified XY centreline not actually adopted')
            changed.append(eid)
        elif actual!=values:raise ValueError('unrelated effective attribute changed')
    return dict(changed_edges=changed,new_complete_XY_centrelines=len(rows),all_old_effective_values_exact=True,new_DN=0,new_vertical_values=0,new_installed_lengths=0)

def provider_from(proof,path):
    provider=copy.deepcopy(load(proof['inputs']['parent_provider']['path']));targets={r['axis_edge_id']:r for r in proof['records']};todo=provider['remaining_horizontal_attributes'];matched=[r for r in todo if r['edge_id']in targets]
    if len(matched)!=len(targets)or any(r['complete_centerline']is not False for r in matched):raise ValueError('new complete projection must belong to an old length-pending scope')
    if any(not isinstance(r['known_whole_DN'],(int,float))or r['known_whole_DN']<=0 for r in matched):raise ValueError('this provider adoption requires separately known original DN')
    provider['history_before_plan_crossover_centrelines']=dict(counts=copy.deepcopy(provider['counts']),target_frontiers=copy.deepcopy(matched))
    provider['remaining_horizontal_attributes']=[r for r in todo if r['edge_id']not in targets]
    for key,change in [('pure_horizontal_complete_centerline',len(targets)),('pure_horizontal_complete_DN_and_centerline',len(targets)),('pure_horizontal_remaining_attributes',-len(targets))]:provider['counts'][key]+=change
    for r in matched:
        scopes=provider['counts']['horizontal_next_scopes'];scopes[r['next_scope']]-=1
        if scopes[r['next_scope']]==0:del scopes[r['next_scope']]
    provider['plan_crossover_centreline_observations']=dict(native_proof_sha256=sha(path),records=copy.deepcopy(proof['records']),measurement_kind='complete_plan_XY_projection_not_installed_length',installed_lengths_assigned=0,human_accepted=False)
    return provider


def refresh(parent,output,proof_path,templates,port):
    parent,output,proof_path,templates=map(lambda p:Path(p).resolve(),(parent,output,proof_path,templates))
    if output.exists() or parent in output.parents or output==parent:raise ValueError('fresh external viewer output required')
    proof=verify_output(proof_path.parent);inventory=prior.base.artifact_inventory(parent);context=context_from(parent,proof,proof_path);old=effective(parent);m=load(parent/'public/data/manifest.json')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in TEMPLATES:shutil.copy2(templates/name,output/name)
    app=output/'public/app.js';s=app.read_text(encoding='utf-8');old_import="from './edge-attributes-axis-rule.js';"
    if s.count(old_import)!=1:raise ValueError('current complete reader entry differs')
    app.write_text(s.replace(old_import,"from './edge-attributes-plan-crossover.js';"),encoding='utf-8')
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode(revised));actual=effective(output);change=delta(old,actual,context);digest=hashlib.sha256(encode(actual)).hexdigest()
    revised['preferredPort']=port;revised['templateHashes'].update({n:sha(templates/n) for n in TEMPLATES});revised['templateHashes']['public/app.js']=sha(app);revised['sourceHashes']['native_plan_crossover_centrelines']=sha(proof_path)
    revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(context)).hexdigest());revised['nativePlanCrossoverCentrelineRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(proof_path),implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(proof_path),effective=digest,templates={n:sha(templates/n) for n in TEMPLATES},implementation=sha(__file__),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode(revised));index=output/'public/index.html';index.write_text(index.read_text(encoding='utf-8').replace(m['bundleId'],revised['bundleId']),encoding='utf-8')
    provider=provider_from(proof,proof_path)
    evidence=output/EVIDENCE;evidence.mkdir();(evidence/'provider-inventory.json').write_bytes(encode(provider));(evidence/'current-effective.json').write_bytes(encode(actual));shutil.copy2(proof_path,evidence/'native-proof.json')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed' or quality['machine_status']!='PASS':raise ValueError('native source/schema gate failed')
    for n,h in inventory.items():
        if n.startswith(('public/data/','annotations/')) and n!='public/data/manifest.json' and sha(output/n)!=h:raise ValueError('source payload or annotation changed')
    if prior.base.artifact_inventory(parent)!=inventory:raise ValueError('parent changed')
    audit=dict(mode=MODE,status='independent_native_and_actual_complete_reader_passed_browser_pending',parent=str(parent),parent_file_hashes=inventory,proof_path=str(proof_path),proof_sha256=sha(proof_path),bundle_id=revised['bundleId'],templates={n:sha(templates/n) for n in TEMPLATES},delta=change,source_preflight=preflight,parent_native_replay_performed=False,new_plan_crossover_native_replay_performed=True,old_annotations_preserved=True,human_accepted=False)
    audit['output_hashes']=prior.base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit));return audit

def verify(output):
    output=Path(output);audit=load(output/AUDIT);parent=Path(audit['parent']);path=Path(audit['proof_path']);proof=verify_output(path.parent);m=load(output/'public/data/manifest.json')
    if (audit['mode']!=MODE or audit['bundle_id']!=m['bundleId'] or sha(path)!=audit['proof_sha256'] or m['nativePlanCrossoverCentrelineRefresh']['implementation_sha256']!=sha(__file__)
        or prior.base.artifact_inventory(parent)!=audit['parent_file_hashes'] or {n:h for n,h in prior.base.artifact_inventory(output).items() if n!=AUDIT}!=audit['output_hashes'] or context_from(parent,proof,path)!=m['attributeValueContext']):raise ValueError('viewer source, context or artifact changed')
    if delta(effective(parent),effective(output),m['attributeValueContext'])!=audit['delta']:raise ValueError('actual paired reader delta differs')
    provider=provider_from(proof,path)
    if encode(provider)!=(output/EVIDENCE/'provider-inventory.json').read_bytes():raise ValueError('provider inheritance changed')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=audit['delta'],human_accepted=False)
