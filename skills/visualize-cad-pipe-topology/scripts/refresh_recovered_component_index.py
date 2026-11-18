"""Publish a checked component index over the exact qualified pipe graph."""
import copy,hashlib,json,shutil,sys,zipfile
from pathlib import Path
for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    p=str(Path(__file__).resolve().parents[2]/name/'scripts')
    if p not in sys.path:sys.path.insert(0,p)
import refresh_attribute_templates as base
from rebuild_recovered_component_index import verify_output as native_owner
from recovered_component_graph_bridge import edge_bases,restore,MODE as NATIVE_MODE
sha,load,encoded=base.sha,base.load,base.encoded
MODE='qualified_recovered_component_viewer_index_v1'
ALLOWED={'public/app.js','public/edge-attributes.js','public/component-inventory-attribute-bridge.js'}


def context_from(proof,path,parent_manifest):
    original=load(parent_manifest);prior=original['attributeValueContext'];inputs=proof['inputs']
    if inputs['parent_viewer_manifest']['sha256']!=sha(parent_manifest)or inputs['parent_rendered_graph']['sha256']!=prior['rendered_graph_sha256']or proof['mode']!=NATIVE_MODE or proof['complete_parent_and_native_inventory_replayed']is not True or proof['pipe_graph_restoration_exact']is not True:raise ValueError('component index is outside original qualified attribute ancestry')
    context=copy.deepcopy(prior)
    if context.get('component_inventory_bridge'):raise ValueError('component inventory bridge already published')
    context['current_rendered_graph_sha256']=proof['rendered_graph_sha256']
    context['component_inventory_bridge']=dict(mode='native_recovered_component_attribute_scope_bridge_v1',native_source_replayed=True,complete_parent_replayed=True,pipe_graph_restoration_exact=True,native_proof_sha256=sha(path),current_rendered_graph_sha256=proof['rendered_graph_sha256'],attribute_parent_rendered_graph_sha256=prior['rendered_graph_sha256'],edge_bases=copy.deepcopy(proof['protected_edge_bases']),unknown_physical_parameters_assigned=0,human_accepted=False)
    return context


def exact_attributes(prior,current):
    if prior!=current:raise ValueError('component indexing changed a qualified effective pipe attribute')
    return dict(edges=len(prior),all_prior_effective_pipe_values_exact=True,new_DN_or_length_values=0)


def refresh(parent,output,templates,native_proof,port=10365):
    parent,output,templates,native_proof=map(lambda p:Path(p).resolve(),(parent,output,templates,native_proof));archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh external component-index viewer required')
    before=base.artifact_inventory(parent);proof=native_owner(native_proof.parent);original=load(parent/'public/data/manifest.json')
    if proof['inputs']['parent_viewer_manifest']['sha256']!=sha(parent/'public/data/manifest.json'):raise ValueError('component index uses another parent viewer')
    native_graph=native_proof.parent/'graph.json';graph=load(native_graph)
    if sha(native_graph)!=proof['rendered_graph_sha256']or restore(graph,proof['audit'])!=load(parent/'public/data/graph.json')or edge_bases(graph)!=proof['protected_edge_bases']:raise ValueError('component graph does not restore its exact parent topology')
    context=context_from(proof,native_proof,parent/'public/data/manifest.json');old_values=base.effective_attributes(parent);changes={n:sha(templates/n)for n in ALLOWED}
    if any((parent/n).exists()and sha(parent/n)==h for n,h in changes.items()):raise ValueError('all component-index attribute readers required')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in changes:shutil.copy2(templates/n,output/n)
    shutil.copy2(native_graph,output/'public/data/graph.json');cfg=load(parent/'visualization-config.json');cfg['device_types'].append(load(proof['inputs']['display_type_policy']['path']));(output/'visualization-config.json').write_bytes(encoded(cfg));manifest=copy.deepcopy(original);manifest['attributeValueContext']=context;manifest['instances']=len(graph['instances']);(output/'public/data/manifest.json').write_bytes(encoded(manifest))
    effective=base.effective_attributes(output);delta=exact_attributes(old_values,effective);digest=hashlib.sha256(encoded(effective)).hexdigest()
    manifest['templateHashes'].update(changes);manifest['preferredPort']=port;manifest['reviewContentHashes'].update(viewer_graph=sha(native_graph),effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encoded(context)).hexdigest());manifest['sourceHashes']['recovered_component_index']=sha(native_proof);manifest['sourceHashes']['recovered_component_rendered_graph']=sha(native_graph)
    manifest['componentIndexRefresh']=dict(mode=MODE,parent_bundle_id=original['bundleId'],implementation_sha256=sha(__file__),native_proof_sha256=sha(native_proof),component_rows_added=proof['component_rows_added'],pipe_graph_restoration_exact=True,human_confirmation_inherited=False)
    manifest['bundleId']=hashlib.sha256(encoded(dict(parent=original['bundleId'],native=sha(native_proof),graph=sha(native_graph),templates=changes,implementation=sha(__file__),port=port))).hexdigest()[:20];(output/'public/data/manifest.json').write_bytes(encoded(manifest));index=output/'public/index.html';index.write_text(index.read_text(encoding='utf8').replace(original['bundleId'],manifest['bundleId']),encoding='utf8')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encoded(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('recovered component native geometry/schema gate failed')
    for name,h in before.items():
        if name.startswith(('public/data/','annotations/'))and name not in('public/data/manifest.json','public/data/graph.json')and sha(output/name)!=h:raise ValueError('component index changed historical data/annotations')
    if base.artifact_inventory(parent)!=before:raise ValueError('component index mutated original viewer')
    evidence=output/'recovered-component-index';evidence.mkdir();shutil.copy2(native_proof,evidence/'native-proof.json');(evidence/'parent-effective.json').write_bytes(encoded(old_values));(evidence/'current-effective.json').write_bytes(encoded(effective))
    audit=dict(mode=MODE,status='native_recovered_component_index_and_all_pipe_attributes_passed_actual_browser_pending',parent=str(parent),parent_file_hashes=before,parent_bundle_id=original['bundleId'],bundle_id=manifest['bundleId'],native_proof_path=str(native_proof),native_proof_sha256=sha(native_proof),changes=changes,delta=delta,counts=dict(prior_instances=proof['audit']['original_instances_preserved'],added_instances=proof['component_rows_added'],current_instances=len(graph['instances']),source_unresolved=len(proof['unresolved_native_components'])),effective_attribute_sha256=digest,source_preflight=preflight,old_instance_ids_and_payloads_preserved=True,old_annotations_preserved=True,related_confirmation_invalidated=True,human_accepted=False)
    audit['output_hashes']={n:h for n,h in base.artifact_inventory(output).items()if n!='recovered-component-index.json'};(output/'recovered-component-index.json').write_bytes(encoded(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('recovered component viewer archive failed')
    return audit


def verify(output):
    output=Path(output);audit=load(output/'recovered-component-index.json');manifest=load(output/'public/data/manifest.json');parent=Path(audit['parent']);path=Path(audit['native_proof_path'])
    if audit['mode']!=MODE or audit['bundle_id']!=manifest['bundleId']or manifest['componentIndexRefresh']['implementation_sha256']!=sha(__file__)or base.artifact_inventory(parent)!=audit['parent_file_hashes']:raise ValueError('component viewer identity changed')
    proof=native_owner(path.parent)
    if sha(path)!=audit['native_proof_sha256']or context_from(proof,path,parent/'public/data/manifest.json')!=manifest['attributeValueContext']or sha(output/'public/data/graph.json')!=proof['rendered_graph_sha256']or restore(load(output/'public/data/graph.json'),proof['audit'])!=load(parent/'public/data/graph.json'):raise ValueError('component viewer source, graph, or attribute bridge changed')
    if {n:h for n,h in base.artifact_inventory(output).items()if n!='recovered-component-index.json'}!=audit['output_hashes']:raise ValueError('component viewer payload changed')
    actual=base.effective_attributes(output);delta=exact_attributes(base.effective_attributes(parent),actual)
    if delta!=audit['delta']or hashlib.sha256(encoded(actual)).hexdigest()!=audit['effective_attribute_sha256']:raise ValueError('component viewer effective pipe attributes changed')
    return dict(status='pending',artifact_replay='passed',bundle_id=manifest['bundleId'],counts=audit['counts'],all_prior_effective_pipe_values_exact=True,human_accepted=False)
