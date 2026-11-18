"""Replace one restorable component overlay while preserving current pipe values."""
import argparse,copy,hashlib,json,shutil,sys,zipfile
from pathlib import Path
for skill in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/skill/'scripts'))
import refresh_attribute_templates as base
from confirm_crossview_paths import load,sha,encode
from refresh_candidate_ring_DN import encode_manifest
from refresh_reviewed_ring_partition_DN import effective
from refresh_fragment_component_index import overlay,provider_from as original_provider
from reviewed_fragment_detail_index import verify_output,preserve_current,MODE as NATIVE_MODE
from fragment_component_index import restore

MODE='received_fragment_detail_current_viewer_adoption_v1';AUDIT='reviewed-fragment-detail-refresh.json';FOLDER='reviewed-fragment-detail-refresh'


def provider_binding(parent,path):
    parent,path=Path(parent).resolve(),Path(path).resolve()
    if not path.is_relative_to(parent):raise ValueError('actual current provider must be in the parent bundle')
    m=load(parent/'public/data/manifest.json');relative=path.relative_to(parent).as_posix();candidates=[]
    for p in parent.glob('*refresh.json'):
        audit=load(p)
        if audit.get('bundle_id')==m['bundleId']and audit.get('output_hashes',{}).get(relative)==sha(path):candidates.append(p)
    if len(candidates)!=1:raise ValueError('one actual current provider publication receipt required')
    provider=load(path);graph=load(parent/'public/data/graph.json')
    if provider['counts']['rendered_component_instances']!=len(graph['instances']):raise ValueError('provider component census is stale')
    return dict(provider=dict(path=str(path),sha256=sha(path)),audit=dict(path=str(candidates[0]),sha256=sha(candidates[0])))


def provider_from(prior,proof,graph_hash,path):
    result=original_provider(prior,proof,graph_hash,path)
    result['history_before_received_fragment_detail']=dict(previous_fragment_index=copy.deepcopy(prior.get('fragment_component_index')),
        previous_fragment_history=copy.deepcopy(prior.get('history_before_fragment_component_index')),
        previous_pending_detail=copy.deepcopy(prior.get('pending_component_detail_differences')))
    if 'history_before_fragment_component_index'in prior:
        result['history_before_fragment_component_index']=copy.deepcopy(prior['history_before_fragment_component_index'])
    result['mode']=MODE;result['reviewed_detail_new_component_instances']=proof['current_component_conservation']['new_instances']
    return result


def context_checks(parent,proof,path,graph):
    m=load(Path(parent)/'public/data/manifest.json');old=load(Path(parent)/'public/data/graph.json')
    if proof.get('application_mode')!=NATIVE_MODE or sha(Path(parent)/'public/data/graph.json')!=proof['received_detail_inputs']['current_graph']['sha256']:
        raise ValueError('reviewed detail does not start at this actual rendered graph')
    preservation=preserve_current(old,graph,proof['current_component_conservation']['source_handles'])
    if preservation!=proof['current_component_conservation']:raise ValueError('reviewed detail component conservation differs')
    parentgraph=Path(parent)/'public/data/fragment-component-parent-graph.json'
    if (sha(parentgraph)!=proof['inputs']['parent_graph']['sha256']or restore(graph)!=load(parentgraph)
        or m['attributeValueContext']['current_rendered_graph_sha256']!=sha(parentgraph)):
        raise ValueError('component replacement does not restore the unchanged attribute source')
    if not m.get('componentFragmentOverlay'):raise ValueError('an existing qualified fragment overlay is required')
    return preservation


def refresh(parent,output,path,provider,port):
    parent,output,path,provider=map(lambda p:Path(p).resolve(),(parent,output,path,provider))
    if output.exists()or output.with_suffix('.zip').exists():raise FileExistsError(output)
    before=base.artifact_inventory(parent);proof=verify_output(path.parent);graph=load(path.parent/'graph.json')
    kept=context_checks(parent,proof,path,graph);binding=provider_binding(parent,provider)
    original=load(parent/'public/data/manifest.json');oldvalues=effective(parent)
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(path.parent/'graph.json',output/'public/data/graph.json');m=copy.deepcopy(original)
    m['componentFragmentOverlay']=overlay(proof,path);m['instances']=len(graph['instances']);m['preferredPort']=port
    m['sourceHashes']['native_fragment_component_index']=sha(path)
    m['reviewContentHashes'].update(viewer_graph=sha(output/'public/data/graph.json'),
        component_fragment_overlay=hashlib.sha256(encode(m['componentFragmentOverlay'])).hexdigest())
    m['bundleId']=hashlib.sha256(encode(dict(parent=original['bundleId'],proof=sha(path),provider=binding,
        implementation=sha(__file__),port=port))).hexdigest()[:20]
    m['reviewedFragmentDetailRefresh']=dict(mode=MODE,parent_bundle_id=original['bundleId'],implementation_sha256=sha(__file__),
        exact_old_attribute_context_retained=True,human_confirmation_inherited=False)
    (output/'public/data/manifest.json').write_bytes(encode_manifest(m))
    index=output/'public/index.html';index.write_text(index.read_text('utf8').replace(original['bundleId'],m['bundleId']),encoding='utf8')
    actual=effective(output)
    if actual!=oldvalues or m['attributeValueContext']!=original['attributeValueContext']:
        raise ValueError('reviewed component replacement changed effective pipe values or contexts')
    folder=output/FOLDER;folder.mkdir();shutil.copy2(path,folder/'native-proof.json')
    (folder/'current-effective.json').write_bytes(encode(actual))
    (folder/'provider-inventory.json').write_bytes(encode(provider_from(load(provider),proof,sha(output/'public/data/graph.json'),path)))
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=load(proof['inputs']['source_inventory']['path'])['inputs']['source'];doc,preflight=read_source(source['path'])
    schema=validate_bundle(output,native_doc=doc,native_source_sha256=source['sha256']);(output/'validation-report.json').write_bytes(encode(schema))
    quality=check(output,source['path'])
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('reviewed component native geometry/schema gate failed')
    if base.artifact_inventory(parent)!=before:raise ValueError('parent bundle mutated')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n not in('public/data/graph.json','public/data/manifest.json')and sha(output/n)!=h:
            raise ValueError('source payload or annotations changed')
    audit=dict(mode=MODE,parent=str(parent),parent_files=before,proof_path=str(path),proof_sha256=sha(path),provider_binding=binding,
        bundle_id=m['bundleId'],preservation=kept,old_attribute_context_exact=True,effective_pipe_attributes_exact=True,
        source_preflight=preflight,old_annotations_preserved=True,human_accepted=False,whole_goal_complete=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    return audit


def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);path=Path(a['proof_path']);proof=verify_output(path.parent)
    m=load(output/'public/data/manifest.json');graph=load(output/'public/data/graph.json');binding=a['provider_binding']
    if (a['mode']!=MODE or m['reviewedFragmentDetailRefresh']['implementation_sha256']!=sha(__file__)
        or sha(path)!=a['proof_sha256']or a['bundle_id']!=m['bundleId']or base.artifact_inventory(parent)!=a['parent_files']
        or {n:h for n,h in base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']
        or provider_binding(parent,binding['provider']['path'])!=binding
        or context_checks(parent,proof,path,graph)!=a['preservation']
        or m['componentFragmentOverlay']!=overlay(proof,path)
        or m['attributeValueContext']!=load(parent/'public/data/manifest.json')['attributeValueContext']
        or effective(output)!=effective(parent)):
        raise ValueError('reviewed fragment viewer replay differs')
    expected=provider_from(load(binding['provider']['path']),proof,sha(output/'public/data/graph.json'),path)
    if encode(expected)!=(output/FOLDER/'provider-inventory.json').read_bytes():raise ValueError('current provider replay differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],new_instances=a['preservation']['new_instances'],human_accepted=False)


def main():
    p=argparse.ArgumentParser()
    for n in('parent','output','proof','parent-provider','verify-output'):p.add_argument('--'+n,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify(a.verify_output)if a.verify_output else refresh(a.parent,a.output,a.proof,a.parent_provider,a.port)
    print({k:v for k,v in r.items()if k in('status','artifact_replay','bundle_id','preservation')},flush=True)
if __name__=='__main__':main()
