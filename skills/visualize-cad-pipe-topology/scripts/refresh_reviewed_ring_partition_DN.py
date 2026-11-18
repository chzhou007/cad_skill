"""Publish requalified plan DN with original geometry, lengths and evidence."""
import argparse, collections, copy, hashlib, json, re, shutil, subprocess, sys, zipfile
from pathlib import Path
for name in ('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    directory=str(Path(__file__).resolve().parents[2]/name/'scripts')
    if directory not in sys.path:sys.path.insert(0,directory)
import refresh_attribute_templates as base
from reapply_reviewed_ring_crossview_DN import verify_output, MODE as NATIVE_MODE
sha,load,encode=base.sha,base.load,base.encoded
MODE='qualified_reviewed_ring_partition_DN_viewer_v1'
AUDIT='reviewed-ring-DN-refresh.json';EVIDENCE='reviewed-ring-DN-refresh'
TEMPLATES=('public/reviewed-ring-partition-DN.js','public/edge-attributes-reviewed-ring.js')
FIELDS={'reviewed_partition_mapping_id','reviewed_partition_plan_edge','reviewed_partition_plan_nominal_mm',
        'reviewed_partition_whole_axis_nominal_mm','reviewed_partition_source_sha256','reviewed_partition_evidence_json'}
STANDARD={'diameter_nominal_mm','diameter_text','diameter_status'}


def effective(bundle):
    """Use the actual app facade; a retained legacy file does not select it."""
    bundle=Path(bundle)
    imports=re.findall(r"from\s*['\"]\./(edge-attributes[A-Za-z0-9_.-]*\.js)['\"]",
                       (bundle/'public/app.js').read_text(encoding='utf-8'))
    if len(imports)!=1 or not (bundle/'public'/imports[0]).is_file():
        raise ValueError('one actual local app attribute reader required')
    script="""import fs from'node:fs';import{pathToFileURL}from'node:url';const p=process.argv[1],a=await import(pathToFileURL(p+'/public/'+process.argv[2])),g=JSON.parse(fs.readFileSync(p+'/public/data/graph.json')),m=JSON.parse(fs.readFileSync(p+'/public/data/manifest.json'));console.log(JSON.stringify(g.edges.map(e=>({edge_id:e.edge_id,values:a.crossViewAttributeCsvValues(e,m.attributeValueContext)}))));"""
    result=subprocess.run(['node','--input-type=module','-e',script,str(bundle),imports[0]],capture_output=True,
        text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('actual current attribute reader failed: '+result.stderr)
    return json.loads(result.stdout)


def context_from(parent,proof,path):
    m=load(Path(parent)/'public/data/manifest.json');prior=m['attributeValueContext']
    if (proof['mode']!=NATIVE_MODE or proof['existing_mappings_source_requalified']is not True
        or proof['old_native_mapping_IDs_preserved']is not True or proof['new_correspondences_assigned']!=0
        or proof['source_graphs_mutated']is not False or proof['physical_lengths_assigned']!=0
        or proof['vertical_values_assigned']!=0 or proof['DN_used_for_mapping']is not False
        or proof['human_accepted']is not False):raise ValueError('qualified reviewed source/mapping proof required')
    if (sha(Path(parent)/'public/data/manifest.json')!=proof['inputs']['viewer_manifest']['sha256']
        or sha(Path(parent)/'public/data/graph.json')!=proof['inputs']['rendered_graph']['sha256']
        or prior['current_rendered_graph_sha256']!=proof['inputs']['rendered_graph']['sha256']
        or 'reviewed_ring_partition_DN'in prior):raise ValueError('reviewed DN parent/source/context differs')
    result=copy.deepcopy(prior)
    result['reviewed_ring_partition_DN']=dict(mode='qualified_reviewed_ring_partition_DN_v1',
        records=copy.deepcopy(proof['records']),count=len(proof['records']),source_graphs_mutated=False,
        new_correspondences_assigned=0,physical_lengths_assigned=0,vertical_values_assigned=0,human_accepted=False,
        source_bindings=dict(raw_axis_graph=prior['source_graph_sha256'],rendered_graph=prior['current_rendered_graph_sha256'],
            native_axis_graph=proof['inputs']['axis_graph']['sha256'],plan_graph=proof['inputs']['plan_graph']['sha256'],
            plan_source=proof['inputs']['plan_source']['sha256'],axis_source=proof['inputs']['axis_source']['sha256'],
            native_crossview_proof=sha(path),native_partition_proof=proof['inputs']['partition']['sha256']))
    return json.loads(encode(result))


def delta(previous,current,records):
    old={r['edge_id']:r['values']for r in previous};new={r['edge_id']:r['values']for r in current}
    targets={r['axis_edge_id']:r for r in records}
    if old.keys()!=new.keys()or len(targets)!=len(records):raise ValueError('DN edge inventory differs')
    whole=[];mixed=[]
    for eid,before in old.items():
        after=new[eid]
        if eid not in targets:
            if after!=before:raise ValueError('unrelated attribute changed '+eid)
            continue
        row=targets[eid]
        if any(k not in after or after[k]!=v for k,v in before.items()if k not in STANDARD):
            raise ValueError('prior values, source history or length changed '+eid)
        if set(after)-set(before)-FIELDS-STANDARD:raise ValueError('undeclared DN output field')
        prior=before.get('diameter_nominal_mm')
        if isinstance(prior,(int,float))and prior>0:
            if after.get('diameter_nominal_mm')!=prior:raise ValueError('previously known whole DN changed')
        if after.get('reviewed_partition_plan_nominal_mm')!=row['nominal_mm']or after.get('reviewed_partition_mapping_id')!=row['mapping_id']:
            raise ValueError('source-qualified plan DN not adopted')
        if json.loads(after.get('reviewed_partition_evidence_json','null'))!=json.loads(encode(row)):
            raise ValueError('DN source evidence differs')
        if row['whole_axis_nominal_mm']is not None:
            if after.get('diameter_nominal_mm')!=row['nominal_mm']or after.get('reviewed_partition_whole_axis_nominal_mm')!=row['nominal_mm']:
                raise ValueError('whole horizontal DN not adopted')
            whole.append(eid)
        else:
            if (after.get('diameter_nominal_mm','')!=before.get('diameter_nominal_mm','')
                or after.get('diameter_text','')!=before.get('diameter_text','')
                or after.get('reviewed_partition_whole_axis_nominal_mm')!=''):
                raise ValueError('mixed plan DN escaped to whole/vertical scope')
            mixed.append(eid)
    return dict(new_whole_horizontal_DN_edges=sorted(whole),new_mixed_plan_branch_DN_scopes=sorted(mixed),
        old_known_numeric_values_and_historical_provider_evidence_exact=True,unknown_DN_statuses_updated=True,
        all_prior_lengths_and_vertical_values_exact=True,new_lengths=0,new_vertical_values=0)


def provider_from(proof,actual):
    old=load(proof['inputs']['provider']['path']);result=copy.deepcopy(old)
    values={r['edge_id']:r['values']for r in actual};targets={r['axis_edge_id']:r for r in proof['records']}
    remaining=[];completed=[]
    for row in old['remaining_horizontal_attributes']:
        eid=row['edge_id'];record=targets.get(eid)
        if record and record['whole_axis_nominal_mm']is not None:
            if row['known_whole_DN']is not None or row['complete_centerline']is not True:
                raise ValueError('whole DN completion requires a previously unknown DN and independently complete length')
            if values[eid].get('diameter_nominal_mm')!=record['nominal_mm']:raise ValueError('provider value not actually adopted')
            completed.append(eid)
        else:remaining.append(copy.deepcopy(row))
    expected={r['axis_edge_id']for r in proof['records']if r['whole_axis_nominal_mm']is not None}
    if set(completed)!=expected:raise ValueError('reviewed whole DN does not match complete current frontier')
    result['history_before_reviewed_partition_DN']=dict(mode=old['mode'],counts=copy.deepcopy(old['counts']),
        completed_frontier_rows=[copy.deepcopy(r)for r in old['remaining_horizontal_attributes']if r['edge_id']in expected])
    result.update(mode=MODE,remaining_horizontal_attributes=remaining,
        reviewed_partition_DN_observations=copy.deepcopy(proof['records']),
        new_reviewed_partition_complete_axis_edges=sorted(completed),human_accepted=False,whole_goal_complete=False)
    counts=dict(collections.Counter(r['next_scope']for r in remaining))
    result['counts'].update(pure_horizontal_complete_DN_and_centerline=old['counts']['pure_horizontal_complete_DN_and_centerline']+len(completed),
        pure_horizontal_remaining_attributes=len(remaining),horizontal_next_scopes=counts)
    frontier=copy.deepcopy(old['current_horizontal_frontier'])
    frontier.update(records=remaining,pure_horizontal_complete=result['counts']['pure_horizontal_complete_DN_and_centerline'],
        pure_horizontal_complete_centerline=old['counts']['pure_horizontal_complete_centerline'],
        pure_horizontal_remaining_attributes=len(remaining),remaining_by_next_scope=counts,
        remaining_by_floor=dict(collections.Counter(str(r['floor'])for r in remaining)))
    result['current_horizontal_frontier']=frontier
    for key in ('records','member_domain_observations','ordinary_junction_mappings','current_component_inventory'):
        if result[key]!=old[key]:raise ValueError('DN application changed mappings or component owners')
    return result


def refresh(parent,output,templates,proof_path,port):
    parent,output,templates,proof_path=map(lambda p:Path(p).resolve(),(parent,output,templates,proof_path))
    if output.exists()or output.with_suffix('.zip').exists():raise FileExistsError(output)
    inventory=base.artifact_inventory(parent);proof=verify_output(proof_path.parent)
    context=context_from(parent,proof,proof_path);old=effective(parent);m=load(parent/'public/data/manifest.json')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in TEMPLATES:shutil.copy2(templates/name,output/name)
    app=output/'public/app.js';text=app.read_text(encoding='utf-8');needle="'./edge-attributes-plan-crossover.js'"
    if text.count(needle)!=1:raise ValueError('explicit prior complete app facade required')
    app.write_text(text.replace(needle,"'./edge-attributes-reviewed-ring.js'"),encoding='utf-8')
    revised=copy.deepcopy(m);revised['attributeValueContext']=context
    (output/'public/data/manifest.json').write_bytes(encode(revised));actual=effective(output)
    change=delta(old,actual,proof['records']);digest=hashlib.sha256(encode(actual)).hexdigest()
    revised['preferredPort']=port;changes={n:sha(output/n)for n in (*TEMPLATES,'public/app.js')}
    revised['templateHashes'].update(changes);revised['sourceHashes']['reviewed_ring_partition_DN']=sha(proof_path)
    revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(context)).hexdigest())
    revised['reviewedRingDNRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(proof_path),
        implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(proof_path),templates=changes,
        effective=digest,implementation=sha(__file__),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode(revised));index=output/'public/index.html'
    index.write_text(index.read_text(encoding='utf-8').replace(m['bundleId'],revised['bundleId']),encoding='utf-8')
    folder=output/EVIDENCE;folder.mkdir();provider=provider_from(proof,actual)
    for name,value in [('provider-inventory.json',provider),('current-effective.json',actual)]:
        (folder/name).write_bytes(encode(value))
    shutil.copy2(proof_path,folder/'native-proof.json')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,readable=read_source(source)
    schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema))
    quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('reviewed DN native source/schema gate failed')
    for name,digest_before in inventory.items():
        if name.startswith(('public/data/','annotations/'))and name!='public/data/manifest.json'and sha(output/name)!=digest_before:
            raise ValueError('source payload or historical annotations changed')
    if base.artifact_inventory(parent)!=inventory:raise ValueError('parent viewer changed')
    audit=dict(mode=MODE,status='native_source_and_actual_app_reader_passed_browser_pending',parent=str(parent),parent_file_hashes=inventory,
        proof_path=str(proof_path),proof_sha256=sha(proof_path),bundle_id=revised['bundleId'],templates=changes,delta=change,
        source_preflight=readable,old_annotations_preserved=True,human_accepted=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED)as z:
        for name in sorted(base.inventory(output)):z.write(output/name,output.name+'/'+name)
    return audit


def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);path=Path(a['proof_path'])
    proof=verify_output(path.parent);m=load(output/'public/data/manifest.json')
    if (a['mode']!=MODE or m['bundleId']!=a['bundle_id']or sha(path)!=a['proof_sha256']
        or m['reviewedRingDNRefresh']['implementation_sha256']!=sha(__file__)
        or base.artifact_inventory(parent)!=a['parent_file_hashes']
        or {n:h for n,h in base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']
        or context_from(parent,proof,path)!=m['attributeValueContext']):raise ValueError('reviewed DN source, parent or output changed')
    actual=effective(output)
    if delta(effective(parent),actual,proof['records'])!=a['delta']or encode(provider_from(proof,actual))!=(output/EVIDENCE/'provider-inventory.json').read_bytes():
        raise ValueError('reviewed DN effective reader or complete provider differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=a['delta'],human_accepted=False)


def main():
    p=argparse.ArgumentParser()
    for k in ('parent','output','templates','proof','verify-output'):p.add_argument('--'+k,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args()
    result=verify(a.verify_output)if a.verify_output else refresh(a.parent,a.output,a.templates,a.proof,a.port)
    print(json.dumps({k:v for k,v in result.items()if k in ('status','artifact_replay','bundle_id','delta')},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
