"""Refresh attribute presentation on an unchanged, qualified portable artifact.

This reuses the rendered artifact; it never reconstructs a graph or substitutes
for its topology owner's native comparison. Changed source inputs require a
normal rebuild instead. Historical annotations remain under their old identity.
"""
import argparse,copy,hashlib,json,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path

MODE='qualified_native_viewer_confirmed_member_attribute_refresh_v2'
ALLOWED={'public/edge-attributes.js','public/full-batch-plan-attributes.js','public/app.js'}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf8'))
def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8')
def inventory(root):return {p.relative_to(root).as_posix():sha(p)for p in Path(root).rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc'}
def artifact_inventory(root):
    # Launch diagnostics are operational output, not rendered/source content.
    return {p:h for p,h in inventory(root).items()if not p.startswith('startup-logs/')}

def parent_check(parent,graph,devices,source,legend,comparison):
    parent=Path(parent);manifest=load(parent/'public/data/manifest.json');quality=load(parent/'quality-gate.json');report=load(comparison)
    inputs={'graph':graph,'devices':devices,'main_dxf':source}
    if manifest['sourceHashes'].get('legend_dxf'):
        if legend is None:raise ValueError('original legend source is required')
        inputs['legend_dxf']=legend
    if any(sha(p)!=manifest['sourceHashes'][key]for key,p in inputs.items()):raise ValueError('native inputs changed; rebuild instead of refreshing presentation')
    if report.get('errors')!=[]or report.get('graph_sha256')!=sha(graph):raise ValueError('original topology source comparison does not qualify this graph')
    if quality.get('machine_status')!='PASS'or quality['graph_sha256']!=sha(parent/'public/data/graph.json'):raise ValueError('parent native rendering has not passed')
    if load(parent/'validation-report.json').get('status')!='passed':raise ValueError('parent schema check has not passed')
    for name,digest in manifest['templateHashes'].items():
        content=(parent/name).read_bytes()
        if name=='public/index.html':content=content.decode('utf8').replace(manifest['bundleId'],'__BUILD_ID__').encode('utf8')
        if hashlib.sha256(content).hexdigest()!=digest:raise ValueError('parent template bytes changed: '+name)
    if manifest.get('reviewContentHashes',{}).get('viewer_graph')!=quality['graph_sha256']:raise ValueError('rendered source identity is not exact')
    return manifest,inputs

def revised_manifest(original,changes,effective_hash,implementation_hash,port,context=None):
    if not changes or not set(changes)<=ALLOWED:raise ValueError('only the declared attribute templates may change')
    if not isinstance(port,int)or isinstance(port,bool)or not 1024<=port<=65535:raise ValueError('explicit local viewer port required')
    result=copy.deepcopy(original);result['templateHashes'].update(changes);result['preferredPort']=port
    # Effective presentation changes require review invalidation even though
    # canonical and rendered graph bytes do not change.
    result.setdefault('reviewContentHashes',{})['effective_edge_attributes']=effective_hash
    if context is not None:
        result['attributeValueContext']=copy.deepcopy(context)
        result['reviewContentHashes']['attribute_value_context']=hashlib.sha256(encoded(context)).hexdigest()
    result['attributeTemplateRefresh']=dict(mode=MODE,parent_bundle_id=original['bundleId'],changed_templates=changes,
        implementation_sha256=implementation_hash,source_reconstruction_performed=False,human_confirmation_inherited=False)
    result['bundleId']=hashlib.sha256(encoded(dict(parent=original['bundleId'],templates=changes,effective=effective_hash,implementation=implementation_hash,port=port))).hexdigest()[:20]
    return result

def effective_attributes(bundle):
    script="""import fs from 'node:fs';import{pathToFileURL}from'node:url';
const m=await import(pathToFileURL(process.argv[1])),g=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),manifest=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
process.stdout.write(JSON.stringify(g.edges.map(e=>({edge_id:e.edge_id,values:m.crossViewAttributeCsvValues(e,manifest.attributeValueContext)}))));"""
    result=subprocess.run(['node','--input-type=module','-e',script,str(Path(bundle)/'public/edge-attributes.js'),str(Path(bundle)/'public/data/graph.json'),str(Path(bundle)/'public/data/manifest.json')],capture_output=True,text=True,encoding='utf8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('actual effective CSV reader failed: '+result.stderr)
    return json.loads(result.stdout)

def refresh(parent,graph,devices,source,legend,comparison,templates,output,port,group_policy=None,member_proof=None):
    parent,templates,output=map(lambda p:Path(p).resolve(),(parent,templates,output));archive=output.with_name(output.name+'.zip')
    if output.exists()or archive.exists():raise FileExistsError(output)
    if parent==output or parent in output.parents:raise ValueError('new bundle must be outside its parent')
    manifest,inputs=parent_check(parent,graph,devices,source,legend,comparison);before=artifact_inventory(parent)
    context=None;native=load(graph)
    if native.get('sourceFullPlanBatchAttributes'):
        if group_policy is None:raise ValueError('complete batch presentation requires its source-pinned group orientation policy')
        from uniform_path_group_DN_context import from_artifact
        expected=manifest['sourceHashes'].get('full_batch_plan_policy')
        context=from_artifact(graph,parent/'public/data/graph.json',group_policy,manifest['sourceHashes']['graph'],expected)
        inputs['group_policy']=Path(group_policy)
    if member_proof is None or context is None:raise ValueError('confirmed member proof and source-qualified group policy required')
    from confirmed_member_plan_attribute_context import from_artifact as member_context
    context['member_plan_runs']=member_context(graph,parent/'public/data/graph.json',member_proof,manifest['sourceHashes']['graph'],load(group_policy)['isometric_horizontal_directions_degrees'])
    inputs['member_proof']=Path(member_proof)
    original_inputs={str(p):sha(p)for p in list(inputs.values())+[Path(comparison)]};changes={}
    for name in ALLOWED:
        replacement=templates/name
        if not replacement.is_file():raise ValueError('complete attribute template dependency set required')
        if manifest['templateHashes'].get(name)!=sha(replacement):changes[name]=sha(replacement)
    if not changes:raise ValueError('no attribute template change to package')
    implementation_hash=sha(__file__);shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    prior=effective_attributes(parent)
    for name in changes:
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(templates/name,target)
    if context is not None:
        provisional=copy.deepcopy(manifest);provisional['attributeValueContext']=context
        (output/'public/data/manifest.json').write_bytes(encoded(provisional))
    current=effective_attributes(output);current_hash=hashlib.sha256(encoded(current)).hexdigest()
    revised=revised_manifest(manifest,changes,current_hash,implementation_hash,port,context)
    (output/'public/data/manifest.json').write_bytes(encoded(revised))
    p=output/'public/index.html';p.write_text(p.read_text(encoding='utf8').replace(manifest['bundleId'],revised['bundleId']),encoding='utf8')
    shutil.copyfile(output/'quality-gate.json',output/'quality-gate-parent.json');shutil.copyfile(output/'validation-report.json',output/'validation-report-parent.json')
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    doc,preflight=read_source(source);validation=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source))
    (output/'validation-report.json').write_bytes(encoded(validation));quality=check(output,source)
    if quality['machine_status']!='PASS':raise ValueError('refreshed artifact fails actual native rendering check')
    # Every source/graph/CAD/component payload and old annotation stays exact.
    for name,digest in before.items():
        if name.startswith(('public/data/','annotations/'))and name!='public/data/manifest.json'and sha(output/name)!=digest:raise ValueError('source data or historical annotation changed')
    if artifact_inventory(parent)!=before or any(sha(p)!=h for p,h in original_inputs.items()):raise ValueError('parent or native inputs changed during refresh')
    if any(sha(templates/name)!=h for name,h in changes.items()):raise ValueError('attribute templates changed during refresh')
    patch=output/'confirmed-member-attribute-refresh';patch.mkdir()
    (patch/'parent-effective-attributes.json').write_bytes(encoded(prior));(patch/'current-effective-attributes.json').write_bytes(encoded(current))
    audit=dict(mode=MODE,status='qualified_cached_viewer_attribute_templates_refreshed_actual_native_schema_and_fidelity_passed_browser_pending',
        parent=str(parent),template_root=str(templates),input_paths={k:str(Path(v).resolve())for k,v in inputs.items()},comparison_path=str(Path(comparison).resolve()),parent_manifest_sha256=before['public/data/manifest.json'],parent_file_hashes=before,
        original_native_inputs=original_inputs,source_comparison_sha256=sha(comparison),source_preflight=preflight,
        parent_bundle_id=manifest['bundleId'],bundle_id=revised['bundleId'],changes=changes,
        canonical_graph_mutated=False,rendered_graph_mutated=False,component_assignments_mutated=False,
        source_reconstruction_performed=False,source_comparison_replayed=False,original_qualified_artifact_reused=True,
        effective_attribute_hash=current_hash,old_annotations_preserved=True,human_confirmation_inherited=False,
        uniform_group_DN_child_domains=context['child_DN_domains']if context else 0,child_length_allocation_performed=False,member_plan_run_edges=context['member_plan_runs']['axis_edges'],net_pipe_cut_lengths_assigned=0,
        native_schema=validation,actual_native_machine_status=quality['machine_status'],human_accepted=False)
    (output/'confirmed-member-attribute-refresh.json').write_bytes(encoded(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as stream:
        for relative in sorted(inventory(output)):stream.write(output/relative,output.name+'/'+relative)
    with zipfile.ZipFile(archive)as stream:
        if stream.testzip()is not None:raise ValueError('refreshed ZIP failed')
    return audit

def verify(output):
    output=Path(output).resolve();saved=load(output/'confirmed-member-attribute-refresh.json');manifest=load(output/'public/data/manifest.json')
    if saved['mode']!=MODE or manifest['attributeTemplateRefresh']['implementation_sha256']!=sha(__file__):raise ValueError('refresh implementation changed')
    if artifact_inventory(saved['parent'])!=saved['parent_file_hashes']:raise ValueError('qualified parent artifact changed')
    inputs=saved['input_paths']
    with tempfile.TemporaryDirectory(prefix='.attribute-refresh-replay-',dir=output.parent)as name:
        scratch=Path(name).resolve()
        if not scratch.is_relative_to(output.parent):raise ValueError('replay scratch outside its owned directory')
        replay=scratch/'viewer'
        fresh=refresh(saved['parent'],inputs['graph'],inputs['devices'],inputs['main_dxf'],inputs.get('legend_dxf'),saved['comparison_path'],saved['template_root'],replay,manifest['preferredPort'],inputs.get('group_policy'),inputs.get('member_proof'))
        if encoded(fresh)!=(output/'confirmed-member-attribute-refresh.json').read_bytes():raise ValueError('independent attribute refresh audit differs')
        expected={p:h for p,h in artifact_inventory(replay).items()if not p.startswith('annotations/')}
        actual={p:h for p,h in artifact_inventory(output).items()if not p.startswith('annotations/')}
        if expected!=actual:raise ValueError('independent refreshed portable bundle bytes differ')
        for relative,digest in saved['parent_file_hashes'].items():
            if relative.startswith('annotations/')and sha(output/relative)!=digest:raise ValueError('historical annotations changed')
    return dict(status='pending',artifact_replay='passed',canonical_graph_mutated=False,source_reconstruction_performed=False,
        bundle_id=manifest['bundleId'],source_comparison_replayed=False,human_accepted=False,
        pending=['Inspect effective properties/CSV and native CAD in the actual browser; HIL stays separate'])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    names=('parent','graph','devices','source','comparison','templates','output')
    for key in names:p.add_argument('--'+key,type=Path)
    p.add_argument('--member-proof',type=Path);p.add_argument('--legend',type=Path);p.add_argument('--group-policy',type=Path);p.add_argument('--port',type=int);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:
        if any(getattr(a,k)is not None for k in names+('legend','group_policy','port','member_proof')):p.error('verification uses its original bound inputs')
        result=verify(a.verify_output)
    else:
        if any(getattr(a,k)is None for k in names+('port',)):p.error('complete parent, native inputs, templates, output and port required')
        result=refresh(a.parent,a.graph,a.devices,a.source,a.legend,a.comparison,a.templates,a.output,a.port,a.group_policy,a.member_proof)
    print(result['status'])
if __name__=='__main__':main()
