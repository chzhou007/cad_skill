"""Keep the old pipe context byte-exact behind an explicit component overlay."""
import argparse
import copy
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path
for skill in ('build-cad-pipe-topology', 'orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]/skill/'scripts'))
import refresh_attribute_templates as base
from confirm_crossview_paths import load, sha, encode
from refresh_reviewed_ring_partition_DN import effective
from rebuild_fragment_component_index import verify_output as index_owner
from fragment_component_index import restore, MODE

AUDIT = 'fragment-component-refresh.json'
FOLDER = 'fragment-component-refresh'


def overlay(proof, path):
    return dict(mode=MODE, parent_graph_path='data/fragment-component-parent-graph.json',
        parent_graph_sha256=proof['inputs']['parent_graph']['sha256'],
        current_graph_sha256=proof['rendered_graph_sha256'], native_proof_sha256=sha(path),
        audit=copy.deepcopy(proof['audit']))


def provider_from(prior, proof, graph_hash, proof_path):
    result = copy.deepcopy(prior)
    inventory = load(proof['inputs']['source_inventory']['path'])
    result['history_before_fragment_component_index'] = dict(
        mode=prior['mode'], counts=copy.deepcopy(prior['counts']),
        current_component_inventory=copy.deepcopy(prior['current_component_inventory']))
    result['mode'] = 'qualified_native_fragment_component_index_provider_v1'
    result['current_component_inventory'].update(
        rendered_components=proof['audit']['current_instances'], rendered_graph_sha256=graph_hash,
        native_inventory=copy.deepcopy(proof['inputs']['source_inventory']),
        source_qualified_component_count=len(inventory['components']),
        pending_source_instance_adoption=len(proof['pending_source_components']),
        unresolved_native_components=[r for r in inventory['records'] if r['status']=='native_or_fragment_owner_unresolved'])
    result['fragment_component_index'] = dict(proof=dict(path=str(proof_path), sha256=sha(proof_path)),
        classifications=copy.deepcopy(proof['classifications']),
        existing_named_scopes_native_replayed=True, native_pipe_attributes_unchanged=True,
        human_accepted=False)
    result['pending_component_detail_differences'] = copy.deepcopy(proof['pending_source_components'])
    result['counts'].update(rendered_component_instances=proof['audit']['current_instances'],
        native_component_ownership_unresolved=len(result['current_component_inventory']['unresolved_native_components']),
        pending_component_detail_differences=len(proof['pending_source_components']))
    for key in ('records','member_domain_observations','ordinary_junction_mappings','remaining_horizontal_attributes'):
        if result[key] != prior[key]: raise ValueError('component publication changed pipe provider observations')
    return result


def patch_app(text):
    needle="if(!componentInventoryGraphContext(attributeManifest.attributeValueContext,actual,data.edges))throw Error('Attribute source context belongs to another rendered graph');"
    replacement="if(!componentInventoryGraphContext(attributeManifest.attributeValueContext,actual,data.edges)&&!await fragmentOverlayGraphContext(attributeManifest,actual,data))throw Error('Attribute source context belongs to another rendered graph');"
    if text.count(needle)!=1: raise ValueError('exact prior guarded graph loader required')
    return "import {fragmentOverlayGraphContext} from './fragment-component-overlay.js';\n"+text.replace(needle,replacement)


def refresh(parent, output, proof_path, templates, port):
    parent, output, proof_path, templates = map(Path, (parent, output, proof_path, templates))
    if output.exists() or output.with_suffix('.zip').exists(): raise FileExistsError(output)
    before=base.artifact_inventory(parent); proof=index_owner(proof_path.parent)
    original=load(parent/'public/data/manifest.json'); graph=load(proof_path.parent/'graph.json')
    if (sha(parent/'public/data/manifest.json') != proof['inputs']['parent_manifest']['sha256']
        or sha(parent/'public/data/graph.json') != proof['inputs']['parent_graph']['sha256']
        or restore(graph) != load(parent/'public/data/graph.json')):
        raise ValueError('component index does not restore this exact viewer')
    old=effective(parent)
    shutil.copytree(parent, output, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(proof_path.parent/'graph.json',output/'public/data/graph.json')
    shutil.copy2(parent/'public/data/graph.json',output/'public/data/fragment-component-parent-graph.json')
    shutil.copy2(templates/'public/fragment-component-overlay.js',output/'public/fragment-component-overlay.js')
    app=output/'public/app.js';app.write_text(patch_app(app.read_text(encoding='utf-8')),encoding='utf-8')
    manifest=copy.deepcopy(original);manifest['componentFragmentOverlay']=overlay(proof,proof_path)
    manifest['instances']=len(graph['instances']);manifest['preferredPort']=port
    changes={n:sha(output/n)for n in ['public/app.js','public/fragment-component-overlay.js']}
    manifest['templateHashes'].update(changes)
    manifest['sourceHashes']['native_fragment_component_index']=sha(proof_path)
    manifest['reviewContentHashes'].update(viewer_graph=sha(output/'public/data/graph.json'),
        component_fragment_overlay=hashlib.sha256(encode(manifest['componentFragmentOverlay'])).hexdigest())
    manifest['bundleId']=hashlib.sha256(encode(dict(parent=original['bundleId'],proof=sha(proof_path),
        changes=changes,implementation=sha(__file__),port=port))).hexdigest()[:20]
    manifest['fragmentComponentRefresh']=dict(mode=MODE,implementation_sha256=sha(__file__),
        parent_bundle_id=original['bundleId'],human_confirmation_inherited=False)
    (output/'public/data/manifest.json').write_bytes(encode(manifest))
    index=output/'public/index.html';index.write_text(index.read_text(encoding='utf-8').replace(original['bundleId'],manifest['bundleId']),encoding='utf-8')
    actual=effective(output)
    if actual!=old: raise ValueError('new components changed effective pipe attributes')
    if manifest['attributeValueContext']!=original['attributeValueContext']:
        raise ValueError('old source contexts must not be rehashed or rebased')
    folder=output/FOLDER;folder.mkdir();shutil.copy2(proof_path,folder/'native-proof.json')
    provider=provider_from(load(proof['inputs']['provider']['path']),proof,proof['rendered_graph_sha256'],proof_path)
    for name,value in [('provider-inventory.json',provider),('current-effective.json',actual)]:
        (folder/name).write_bytes(encode(value))
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    inventory=load(proof['inputs']['source_inventory']['path']);source=inventory['inputs']['source']['path']
    doc,preflight=read_source(source)
    schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source))
    (output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed' or quality['machine_status']!='PASS':
        raise ValueError('native component geometry/schema gate failed')
    if base.artifact_inventory(parent)!=before: raise ValueError('parent viewer mutated')
    for name,h in before.items():
        if name.startswith(('public/data/','annotations/')) and name not in ('public/data/graph.json','public/data/manifest.json') and sha(output/name)!=h:
            raise ValueError('historical data or annotations changed')
    audit=dict(mode=MODE,parent=str(parent),parent_files=before,proof_path=str(proof_path),proof_sha256=sha(proof_path),
        bundle_id=manifest['bundleId'],changes=changes,source_preflight=preflight,
        effective_pipe_attributes_exact=True,old_attribute_context_exact=True,
        added_instances=proof['audit']['added_count'],pending_source_instances=len(proof['pending_source_components']),
        original_instances_preserved=proof['audit']['prior_instances'],current_instances=len(graph['instances']),
        old_annotations_preserved=True,human_accepted=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED)as archive:
        for name in sorted(base.inventory(output)):archive.write(output/name,output.name+'/'+name)
    return audit


def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);path=Path(a['proof_path'])
    proof=index_owner(path.parent);m=load(output/'public/data/manifest.json')
    if (a['mode']!=MODE or a['proof_sha256']!=sha(path) or a['bundle_id']!=m['bundleId']
        or m['fragmentComponentRefresh']['implementation_sha256']!=sha(__file__)
        or base.artifact_inventory(parent)!=a['parent_files']
        or {n:h for n,h in base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']
        or overlay(proof,path)!=m['componentFragmentOverlay']
        or m['attributeValueContext']!=load(parent/'public/data/manifest.json')['attributeValueContext']
        or restore(load(output/'public/data/graph.json'))!=load(parent/'public/data/graph.json')
        or (output/'public/data/fragment-component-parent-graph.json').read_bytes()!=(parent/'public/data/graph.json').read_bytes()
        or effective(output)!=effective(parent)):
        raise ValueError('fragment viewer replay/restoration/attributes differ')
    expected=provider_from(load(proof['inputs']['provider']['path']),proof,proof['rendered_graph_sha256'],path)
    if encode(expected)!=(output/FOLDER/'provider-inventory.json').read_bytes():raise ValueError('complete provider differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],
        adopted=a['added_instances'],pending_source=a['pending_source_instances'],human_accepted=False)


def main():
    p=argparse.ArgumentParser()
    for n in ('parent','output','proof','templates','verify-output'):p.add_argument('--'+n,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        result=verify(a.verify_output)if a.verify_output else refresh(a.parent,a.output,a.proof,a.templates,a.port)
    print({k:v for k,v in result.items()if k in ('status','artifact_replay','bundle_id','added_instances','pending_source_instances')},flush=True)


if __name__=='__main__':main()
