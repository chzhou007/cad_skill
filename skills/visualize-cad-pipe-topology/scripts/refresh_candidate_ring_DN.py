"""Append candidate ring DN through the actual parent app facade."""
import argparse,copy,hashlib,json,re,shutil,sys,zipfile
from pathlib import Path
for name in ('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    directory=str(Path(__file__).resolve().parents[2]/name/'scripts')
    if directory not in sys.path:sys.path.insert(0,directory)
import refresh_reviewed_ring_partition_DN as original
from reapply_candidate_ring_crossview_DN import verify_output,MODE as NATIVE_MODE
base=original.base;sha,load,encode=original.sha,original.load,original.encode
MODE='qualified_reviewed_candidate_ring_DN_viewer_v1'
KEY='reviewed_candidate_ring_partition_DN';AUDIT='candidate-ring-DN-refresh.json';FOLDER='candidate-ring-DN-refresh'
MODULES=['public/reviewed-candidate-ring-DN.js','public/edge-attributes-candidate-ring.js']


def encode_manifest(value):
    """Keep prior nested key order: the app exports evidence with JSON.stringify."""
    return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')


def context_from(parent,proof,path):
    m=load(Path(parent)/'public/data/manifest.json');prior=m['attributeValueContext']
    if (proof['mode']!=NATIVE_MODE or proof['existing_mappings_source_requalified'] is not True
        or proof['old_native_mapping_IDs_preserved'] is not True or proof['new_correspondences_assigned']!=0
        or proof['source_graphs_mutated'] is not False or proof['physical_lengths_assigned']!=0
        or proof['vertical_values_assigned']!=0 or proof['DN_used_for_mapping'] is not False or proof['human_accepted'] is not False):
        raise ValueError('native candidate partition/mapping proof required')
    if (sha(Path(parent)/'public/data/manifest.json')!=proof['inputs']['viewer_manifest']['sha256']
        or sha(Path(parent)/'public/data/graph.json')!=proof['inputs']['rendered_graph']['sha256']
        or prior['current_rendered_graph_sha256']!=proof['inputs']['attribute_context_graph']['sha256'] or KEY in prior):
        raise ValueError('candidate DN parent source/context differs')
    from reapply_candidate_ring_crossview_DN import attribute_graph_binding
    if attribute_graph_binding(load(Path(parent)/'public/data/graph.json'),m,proof['inputs'])!=proof['inherited_attribute_graph_binding']:
        raise ValueError('candidate DN lost the existing component-overlay binding')
    result=copy.deepcopy(prior)
    result[KEY]=dict(mode='qualified_reviewed_candidate_ring_partition_DN_v1',records=copy.deepcopy(proof['records']),
        count=len(proof['records']),source_graphs_mutated=False,new_correspondences_assigned=0,
        physical_lengths_assigned=0,vertical_values_assigned=0,human_accepted=False,
        source_bindings=dict(raw_axis_graph=prior['source_graph_sha256'],rendered_graph=prior['current_rendered_graph_sha256'],
            actual_viewer_graph=proof['inputs']['rendered_graph']['sha256'],
            native_axis_graph=proof['inputs']['axis_graph']['sha256'],plan_graph=proof['inputs']['plan_graph']['sha256'],
            plan_source=proof['inputs']['plan_source']['sha256'],axis_source=proof['inputs']['axis_source']['sha256'],
            native_crossview_proof=sha(path),native_partition_proof=proof['inputs']['partition']['sha256']))
    return result


def delta(before,after,records):
    """Keep all old partition fields; delegate other invariants to the old guard."""
    old={r['edge_id']:r['values'] for r in before};new={r['edge_id']:r['values'] for r in after}
    if old.keys()!=new.keys():raise ValueError('candidate DN edge inventory changed')
    for eid,values in old.items():
        if any(new[eid].get(k)!=v for k,v in values.items() if k.startswith('reviewed_partition_')):
            raise ValueError('historical partition evidence changed')
    def adapted(rows):
        return [dict(edge_id=r['edge_id'],values={k.replace('candidate_ring_partition_','reviewed_partition_',1):v
            for k,v in r['values'].items() if not k.startswith('reviewed_partition_')}) for r in rows]
    return original.delta(adapted(before),adapted(after),records)


def current_parent_provider(parent):
    """Publication inherits the actual parent inventory, not its older map basis."""
    parent=Path(parent);path=parent/'effective-provider-refresh/provider-inventory.json'
    audit=load(parent/'effective-provider-refresh.json');manifest=load(parent/'public/data/manifest.json')
    rel=path.relative_to(parent).as_posix()
    if (audit['bundle_id']!=manifest['bundleId'] or audit['output_hashes'].get(rel)!=sha(path)
        or manifest.get('effectiveProviderRefresh',{}).get('mode')!='actual_effective_member_DN_and_provider_refresh_v1'):
        raise ValueError('actual current parent provider receipt differs')
    result=load(path);graph=load(parent/'public/data/graph.json')
    count=len(graph['instances'])
    if result['counts']['rendered_component_instances']!=count:
        raise ValueError('current parent component inventory differs from rendered graph')
    return dict(path=str(path.resolve()),sha256=sha(path))


def provider_from(proof,actual,parent_provider=None):
    basis=load(proof['inputs']['provider']['path'])
    if parent_provider is not None:
        if sha(parent_provider['path'])!=parent_provider['sha256']:raise ValueError('publication provider changed')
        old=load(parent_provider['path'])
        if old['ordinary_junction_mappings']!=basis['ordinary_junction_mappings']:
            raise ValueError('publication provider mappings differ from native qualified basis')
        adapted=copy.deepcopy(proof);adapted['inputs']['provider']=parent_provider
    else:old=basis;adapted=proof
    result=original.provider_from(adapted,actual)
    result['candidate_ring_DN_observations']=result.pop('reviewed_partition_DN_observations')
    result['candidate_ring_completion_edges']=result.pop('new_reviewed_partition_complete_axis_edges')
    result['history_before_candidate_ring_DN']=result.pop('history_before_reviewed_partition_DN')
    for key in ('reviewed_partition_DN_observations','new_reviewed_partition_complete_axis_edges','history_before_reviewed_partition_DN'):
        if key in old:result[key]=copy.deepcopy(old[key])
    result['mode']=MODE;result['counts']['current_effective_whole_DN_known']=sum(
        isinstance(r['values'].get('diameter_nominal_mm'),(int,float)) and r['values']['diameter_nominal_mm']>0 for r in actual)
    return result


def refresh(parent,output,templates,path,port):
    parent,output,templates,path=map(lambda p:Path(p).resolve(),(parent,output,templates,path))
    if output.exists() or output.with_suffix('.zip').exists():raise FileExistsError(output)
    before=base.artifact_inventory(parent);proof=verify_output(path.parent);context=context_from(parent,proof,path)
    parent_provider=current_parent_provider(parent)
    m=load(parent/'public/data/manifest.json');old=original.effective(parent)
    app=(parent/'public/app.js').read_text('utf8');imports=re.findall(r"from\s*['\"]\./(edge-attributes[A-Za-z0-9_.-]*\.js)['\"]",app)
    if len(imports)!=1:raise ValueError('one actual complete parent facade required')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in MODULES:shutil.copy2(templates/n,output/n)
    facade=output/'public/edge-attributes-candidate-ring.js';text=facade.read_text('utf8')
    if text.count('./edge-attributes-effective-provider.js')!=2:raise ValueError('candidate facade template changed')
    facade.write_text(text.replace('./edge-attributes-effective-provider.js','./'+imports[0]),encoding='utf8')
    (output/'public/app.js').write_text(app.replace('./'+imports[0],'./edge-attributes-candidate-ring.js'),encoding='utf8')
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode_manifest(revised))
    actual=original.effective(output);change=delta(old,actual,proof['records']);digest=hashlib.sha256(encode(actual)).hexdigest()
    changed={n:sha(output/n) for n in MODULES+['public/app.js']};revised['preferredPort']=port
    revised['templateHashes'].update(changed);revised['sourceHashes'][KEY]=sha(path)
    revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(context)).hexdigest())
    revised['candidateRingDNRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(path),
        implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(path),templates=changed,effective=digest,port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode_manifest(revised));index=output/'public/index.html'
    index.write_text(index.read_text('utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    folder=output/FOLDER;folder.mkdir();(folder/'current-effective.json').write_bytes(encode(actual))
    (folder/'provider-inventory.json').write_bytes(encode(provider_from(proof,actual,parent_provider)));shutil.copy2(path,folder/'native-proof.json')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,readable=read_source(source)
    schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema))
    quality=check(output,source)
    if schema['status']!='passed' or quality['machine_status']!='PASS':raise ValueError('candidate DN native viewer gate failed')
    if before!=base.artifact_inventory(parent):raise ValueError('parent viewer changed')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/')) and n!='public/data/manifest.json' and sha(output/n)!=h:
            raise ValueError('source payload or annotations changed')
    audit=dict(mode=MODE,status='native_and_actual_reader_passed_browser_pending',parent=str(parent),parent_file_hashes=before,
        proof_path=str(path),proof_sha256=sha(path),publication_parent_provider=parent_provider,bundle_id=revised['bundleId'],templates=changed,delta=change,
        source_preflight=readable,old_annotations_preserved=True,human_accepted=False,whole_goal_complete=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED) as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    return audit


def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);path=Path(a['proof_path']);proof=verify_output(path.parent)
    m=load(output/'public/data/manifest.json')
    if (a['mode']!=MODE or a['bundle_id']!=m['bundleId'] or sha(path)!=a['proof_sha256']
        or m['candidateRingDNRefresh']['implementation_sha256']!=sha(__file__)
        or base.artifact_inventory(parent)!=a['parent_file_hashes']
        or {n:h for n,h in base.artifact_inventory(output).items() if n!=AUDIT}!=a['output_hashes']
        or context_from(parent,proof,path)!=m['attributeValueContext']):raise ValueError('candidate viewer source or bytes changed')
    actual=original.effective(output)
    if (current_parent_provider(parent)!=a['publication_parent_provider'] or delta(original.effective(parent),actual,proof['records'])!=a['delta']
        or encode(provider_from(proof,actual,a['publication_parent_provider']))!=(output/FOLDER/'provider-inventory.json').read_bytes()):
        raise ValueError('candidate viewer values or provider replay differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=a['delta'],human_accepted=False)


def main():
    p=argparse.ArgumentParser()
    for k in ('parent','output','templates','proof','verify-output'):p.add_argument('--'+k,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        result=verify(a.verify_output) if a.verify_output else refresh(a.parent,a.output,a.templates,a.proof,a.port)
    print(json.dumps(result.get('delta',result),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
