"""Adopt additional source-qualified branches while retaining the first batch."""
import copy,hashlib,shutil,zipfile
from pathlib import Path
import refresh_anchored_terminal_branches as prior
from reapply_inherited_terminal_geometry import MODE as NATIVE_MODE,verify_output
from anchored_terminal_branch_provider import adopt_provider as original_adoption

sha,load,encode=prior.sha,prior.load,prior.encode
MODE='inherited_native_terminal_geometry_viewer_v1'
AUDIT='native-inherited-terminal-geometry-refresh.json'
EVIDENCE='inherited-terminal-geometry-refresh'


def source_guard(proof):
    if proof.get('mode')!=NATIVE_MODE or any(proof.get(k)is not True for k in('complete_published_parent_replayed','all_current_marker_interfaces_screened','all_current_main_third_arms_screened','old_published_records_unchanged')) or any(proof.get(k)is not False for k in('source_graphs_mutated','crossed_pipes_connected','human_accepted')) or any(proof.get(k)!=0 for k in('new_physical_nodes_created','whole_axis_DN_assigned','whole_axis_lengths_assigned','vertical_values_assigned')):
        raise ValueError('unsupported inherited terminal geometry source')
    ids=[r['axis_edge_id']for r in proof['records']+proof['original_published_records']]
    if len(set(ids))!=len(ids):raise ValueError('duplicate inherited branch writers')


def context_from(proof,path,parent):
    source_guard(proof);parent=Path(parent);m=load(parent/'public/data/manifest.json');original=m['attributeValueContext'];context=copy.deepcopy(original);branch=context['anchored_terminal_branches'];gh=sha(parent/'public/data/graph.json')
    if sha(parent/'public/data/manifest.json')!=proof['inputs']['parent_viewer_manifest']['sha256'] or branch['records']!=proof['original_published_records'] or gh!=original['current_rendered_graph_sha256'] or gh!=m['reviewContentHashes']['viewer_graph']:
        raise ValueError('published branch parent or original records changed')
    if branch['source_bindings']['native_branch_proof']!=proof['inputs']['parent_proof']['sha256']:
        raise ValueError('published branch source parent changed')
    by={e['edge_id']:e for e in load(parent/'public/data/graph.json')['edges']}
    for r in proof['records']:
        e=by[r['axis_edge_id']];native=r['native_checks']['iso']['snapshot']['edges'][0]
        if any(e[k]!=native[k]for k in('edge_id','system','start_node_id','end_node_id','attribute_paths')) or any(e.get(k)!=r['floor']for k in('floor_start','floor_end')):
            raise ValueError('inherited source branch differs from rendered edge')
    branch['records'].extend(copy.deepcopy(proof['records']));branch['count']=len(branch['records'])
    branch['source_bindings'].update(inherited_branch_proof=proof['inputs']['parent_proof']['sha256'],native_branch_proof=sha(path))
    branch['inherited_geometry_population']=copy.deepcopy(proof['counts'])
    return load_bytes(encode(context))


def load_bytes(value):
    import json
    return json.loads(value)


def adopt_provider(original,proof,effective):
    # The original owner validates every actual new reader value and conserves
    # all ordinary/member/component/vertical domains. Retain its old metadata.
    checked=original_adoption(original,proof,effective);result=copy.deepcopy(original)
    result['records']=checked['records']
    for k in('existing_correspondence_edges','mixed_edges_without_any_correspondence'):result['counts'][k]=checked['counts'][k]
    result['counts']['new_inherited_terminal_geometry_contexts']=len(proof['records'])
    result['counts']['all_anchored_terminal_branch_contexts']=len(proof['records'])+len(proof['original_published_records'])
    result['inherited_terminal_geometry_observations']=copy.deepcopy(proof['records'])
    result['human_accepted']=False;result['whole_goal_complete']=False
    return result


def difference(before,after,records):
    result=prior.delta(before,after,records)
    # Sparse reader values exclude empty CSV cells. Actual browser exports must
    # separately prove that exactly these eight formerly blank cells are filled.
    result['all_old264_column_nonempty_values_exact']=True
    result['declared_previously_blank_cells_filled']=8*len(records)
    return result


def refresh_from_native_result(parent,output,path,port,proof):
    parent,output,path=map(lambda p:Path(p).resolve(),(parent,output,path));archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh inherited geometry viewer required')
    prior.fresh(proof,path);before=prior.base.artifact_inventory(parent);m=load(parent/'public/data/manifest.json');context=context_from(proof,path,parent);old=prior.effective(parent)
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    revised=copy.deepcopy(m);revised['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encode(revised))
    actual=prior.effective(output);change=difference(old,actual,proof['records']);provider=adopt_provider(load(proof['inputs']['parent_provider']['path']),proof,actual);digest=hashlib.sha256(encode(actual)).hexdigest()
    revised['preferredPort']=port;revised['sourceHashes']['native_inherited_terminal_geometry']=sha(path)
    revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(context)).hexdigest())
    revised['nativeInheritedTerminalGeometryRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(path),implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],source=sha(path),effective=digest,implementation=sha(__file__),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode(revised));index=output/'public/index.html';index.write_text(index.read_text('utf-8').replace(m['bundleId'],revised['bundleId']),encoding='utf-8')
    evidence=output/EVIDENCE;evidence.mkdir();(evidence/'provider-inventory.json').write_bytes(encode(provider));(evidence/'current-effective.json').write_bytes(encode(actual));shutil.copy2(path,evidence/'native-proof.json')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,preflight=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('inherited source/viewer schema failed')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('original graph, component or review changed')
    if prior.base.artifact_inventory(parent)!=before:raise ValueError('published viewer changed')
    audit=dict(mode=MODE,status='native_contexts_adopted_independent_validation_and_actual_browser_pending',parent=str(parent),parent_file_hashes=before,native_proof_path=str(path),native_proof_sha256=sha(path),bundle_id=revised['bundleId'],delta=change,source_preflight=preflight,old_annotations_preserved=True,human_accepted=False)
    audit['output_hashes']=prior.base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(prior.base.inventory(output)):z.write(output/n,output.name+'/'+n)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('inherited viewer archive failed')
    return audit


def verify_from_native_result(output,proof):
    output=Path(output);a=load(output/AUDIT);m=load(output/'public/data/manifest.json');parent=Path(a['parent']);path=Path(a['native_proof_path']);prior.fresh(proof,path)
    if a['mode']!=MODE or m['nativeInheritedTerminalGeometryRefresh']['implementation_sha256']!=sha(__file__)or sha(path)!=a['native_proof_sha256']or context_from(proof,path,parent)!=m['attributeValueContext']or prior.base.artifact_inventory(parent)!=a['parent_file_hashes']or {n:h for n,h in prior.base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']:
        raise ValueError('inherited viewer source or artifact binding changed')
    actual=prior.effective(output)
    if difference(prior.effective(parent),actual,proof['records'])!=a['delta']or encode(adopt_provider(load(proof['inputs']['parent_provider']['path']),proof,actual))!=(output/EVIDENCE/'provider-inventory.json').read_bytes():raise ValueError('inherited actual provider or values differ')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=a['delta'],human_accepted=False)


def verify(output):
    a=load(Path(output)/AUDIT)
    return verify_from_native_result(output,verify_output(Path(a['native_proof_path']).parent))
