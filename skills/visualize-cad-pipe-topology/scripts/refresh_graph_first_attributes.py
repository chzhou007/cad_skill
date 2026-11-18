"""Publish newly checked graph-first scopes while preserving every old value."""
import argparse,copy,hashlib,json,shutil,zipfile
from pathlib import Path
import refresh_attribute_templates as base
from graph_first_attribute_context import from_artifacts
MODE='qualified_viewer_graph_first_attribute_extensions_v1'
ALLOWED={'public/edge-attributes.js','public/graph-first-attribute-extensions.js'}
sha,load,encoded=base.sha,base.load,base.encoded

def qualified_parent(parent,graph,devices,source,legend,comparison,qualification,qualification_sha):
    if sha(qualification)!=qualification_sha:raise ValueError('original bridge viewer qualification changed')
    saved=load(qualification);m,_=base.parent_check(parent,graph,devices,source,legend,comparison)
    audit=load(Path(parent)/'alias-member-bridge-refresh.json')
    if saved.get('formal_artifact_replay',{}).get('artifact_replay')!='passed'or saved['formal_artifact_replay']['bundle_id']!=m['bundleId']or saved['result']!=audit:raise ValueError('parent is not independently qualified bridge viewer')
    if any(sha(p)!=h for p,h in audit['original_input_hashes'].items()):raise ValueError('original bridge source input changed')
    if hashlib.sha256(encoded(m['attributeValueContext'])).hexdigest()!=m['reviewContentHashes']['attribute_value_context']or hashlib.sha256(encoded(base.effective_attributes(parent))).hexdigest()!=audit['effective_attribute_hash']:raise ValueError('original bridge effective values changed')
    return m

def delta(prior,current,context):
    old={r['edge_id']:r['values']for r in prior};new={r['edge_id']:r['values']for r in current}
    cycles={r['axis_edge_id']:r for r in context['cycle_records']};vertical={eid:[r for r in context['vertical_records']if r['edge_id']==eid]for eid in {r['edge_id']for r in context['vertical_records']}}
    targets=cycles.keys()|vertical.keys()
    if old.keys()!=new.keys()or len(old)!=len(prior)or len(new)!=len(current):raise ValueError('edge inventory changed')
    for eid,before in old.items():
        after=new[eid]
        if any(k not in after or after[k]!=v for k,v in before.items()):raise ValueError('old effective value changed '+eid)
        extra={k:v for k,v in after.items()if k not in before}
        if eid not in targets:
            if extra:raise ValueError('unrelated edge acquired new value '+eid)
            continue
        if any(not(k.startswith('cycle_gate_')or k.startswith('unbranched_vertical_DN_'))for k in extra):raise ValueError('unexpected new field')
        if eid in cycles:
            r=cycles[eid]
            if after.get('cycle_gate_mapping_id')!=r['mapping_id']or after.get('cycle_gate_plan_edge')!=r['plan_edge_id']or after.get('cycle_gate_complete_centerline_mm')!=r['complete_horizontal_centerline_mm']or json.loads(after.get('cycle_gate_evidence_json','{}'))!=r:raise ValueError('cycle UI/CSV differs from native context')
        if eid in vertical:
            if after.get('unbranched_vertical_DN_segment_count')!=len(vertical[eid])or json.loads(after.get('unbranched_vertical_DN_segments_json','[]'))!=vertical[eid]:raise ValueError('vertical UI/CSV differs from native context')
    return dict(new_cycle_correspondences=len(cycles),new_horizontal_centerlines=len(cycles),new_vertical_DN_domains=len(context['vertical_records']),
        affected_axis_edges=len(targets),unrelated_edges_unchanged=len(old)-len(targets),all_old_effective_values_exact=True,
        all_current_vertical_DN_domains=context['all_current_vertical_domain_count'],new_whole_DN=0,new_installed_lengths=0)

def refresh(parent,output,templates,graph,devices,source,legend,comparison,metric_proof,vertical_proof,qualification,qualification_sha,port=10361):
    parent,output,templates=map(lambda p:Path(p).resolve(),(parent,output,templates));archive=output.with_suffix('.zip')
    if output.exists()or archive.exists()or parent==output or parent in output.parents:raise ValueError('fresh external viewer output required')
    m=qualified_parent(parent,graph,devices,source,legend,comparison,qualification,qualification_sha);before=base.artifact_inventory(parent);context=copy.deepcopy(m['attributeValueContext'])
    if 'graph_first_extensions'in context:raise ValueError('graph-first scopes already composed')
    context['graph_first_extensions']=from_artifacts(graph,parent/'public/data/graph.json',metric_proof,vertical_proof,context)
    paths=dict(graph=graph,devices=devices,source=source,legend=legend,comparison=comparison,metric_proof=metric_proof,vertical_proof=vertical_proof,qualification=qualification)
    inputs={str(Path(p).resolve()):sha(p)for p in paths.values()};changes={n:sha(templates/n)for n in ALLOWED if not(parent/n).exists()or sha(templates/n)!=m['templateHashes'].get(n)}
    if changes.keys()!=ALLOWED:raise ValueError('both declared extension readers must be packaged')
    old=base.effective_attributes(parent);shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for n in changes:shutil.copy2(templates/n,output/n)
    provisional=copy.deepcopy(m);provisional['attributeValueContext']=context;(output/'public/data/manifest.json').write_bytes(encoded(provisional))
    current=base.effective_attributes(output);change=delta(old,current,context['graph_first_extensions']);effective_hash=hashlib.sha256(encoded(current)).hexdigest()
    revised=copy.deepcopy(m);revised['templateHashes'].update(changes);revised['preferredPort']=port;revised['attributeValueContext']=context
    revised['reviewContentHashes'].update(effective_edge_attributes=effective_hash,attribute_value_context=hashlib.sha256(encoded(context)).hexdigest())
    revised['sourceHashes'].update(cycle_gate_metric_proof=sha(metric_proof),unbranched_vertical_DN_proof=sha(vertical_proof))
    revised['attributeTemplateRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],changed_templates=changes,implementation_sha256=sha(__file__),source_reconstruction_performed=False,human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encoded(dict(parent=m['bundleId'],templates=changes,effective=effective_hash,implementation=sha(__file__),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encoded(revised));p=output/'public/index.html';p.write_text(p.read_text(encoding='utf8').replace(m['bundleId'],revised['bundleId']),encoding='utf8')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    doc,readable=read_source(source);schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encoded(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('new source rendering/schema failed')
    for n,h in before.items():
        if n.startswith(('public/data/','annotations/'))and n!='public/data/manifest.json'and sha(output/n)!=h:raise ValueError('old graph/source/components/annotations changed')
    if base.artifact_inventory(parent)!=before or any(sha(p)!=h for p,h in inputs.items()):raise ValueError('parent or input changed during extension')
    evidence=output/'graph-first-refresh';evidence.mkdir();(evidence/'parent-effective.json').write_bytes(encoded(old));(evidence/'current-effective.json').write_bytes(encoded(current))
    shutil.copy2(metric_proof,evidence/'native-cycle-centrelines.json');shutil.copy2(vertical_proof,evidence/'native-vertical-inheritance.json')
    audit=dict(mode=MODE,status='native_schema_fidelity_and_all_old_effective_values_passed_actual_browser_pending',parent=str(parent),template_root=str(templates),source_paths={k:str(Path(v).resolve())for k,v in paths.items()},
        qualification_sha256=qualification_sha,original_input_hashes=inputs,parent_file_hashes=before,parent_bundle_id=m['bundleId'],bundle_id=revised['bundleId'],changes=changes,effective_attribute_hash=effective_hash,
        delta=change,source_preflight=readable,native_schema_status=schema['status'],native_drawing_status=quality['machine_status'],parent_original_qualified_artifact_reused=True,parent_native_replay_performed=False,
        new_metric_and_vertical_sources_independently_replayed=True,canonical_axis_graph_mutated=False,rendered_axis_graph_mutated=False,component_assignments_mutated=False,
        old_annotations_preserved=True,human_confirmation_inherited=False,human_accepted=False)
    audit['output_hashes']={n:h for n,h in base.artifact_inventory(output).items()if n!='graph-first-refresh.json'};(output/'graph-first-refresh.json').write_bytes(encoded(audit))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
        for n in sorted(base.inventory(output)):z.write(output/n,output.name+'/'+n)
    with zipfile.ZipFile(archive)as z:
        if z.testzip()is not None:raise ValueError('new viewer ZIP failed')
    return audit

def verify(output):
    output=Path(output);a=load(output/'graph-first-refresh.json');m=load(output/'public/data/manifest.json');parent=Path(a['parent']);p=a['source_paths']
    if a['mode']!=MODE or a['bundle_id']!=m['bundleId']or m['attributeTemplateRefresh']['implementation_sha256']!=sha(__file__)or base.artifact_inventory(parent)!=a['parent_file_hashes']:raise ValueError('graph-first viewer identity changed')
    qualified_parent(parent,p['graph'],p['devices'],p['source'],p['legend'],p['comparison'],p['qualification'],a['qualification_sha256'])
    if any(sha(p)!=h for p,h in a['original_input_hashes'].items())or {n:h for n,h in base.artifact_inventory(output).items()if n!='graph-first-refresh.json'}!=a['output_hashes']:raise ValueError('graph-first viewer/input bytes changed')
    prior=load(parent/'public/data/manifest.json')['attributeValueContext'];expected=copy.deepcopy(prior)
    expected['graph_first_extensions']=from_artifacts(p['graph'],output/'public/data/graph.json',p['metric_proof'],p['vertical_proof'],prior)
    if m['attributeValueContext']!=expected:raise ValueError('graph-first context differs from fresh source replay')
    actual=base.effective_attributes(output)
    if hashlib.sha256(encoded(actual)).hexdigest()!=a['effective_attribute_hash']or delta(base.effective_attributes(parent),actual,expected['graph_first_extensions'])!=a['delta']:raise ValueError('graph-first effective values changed')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],counts=a['delta'],human_accepted=False)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',type=Path)
    for n in('parent','output','templates','graph','devices','source','legend','comparison','metric-proof','vertical-proof','qualification'):parser.add_argument('--'+n,type=Path)
    parser.add_argument('--qualification-sha256');parser.add_argument('--port',type=int,default=10361);a=parser.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify:r=verify(a.verify)
        else:
            names=('parent','output','templates','graph','devices','source','legend','comparison','metric_proof','vertical_proof','qualification')
            if any(getattr(a,n)is None for n in names)or not a.qualification_sha256:parser.error('complete pinned native inputs required')
            r=refresh(**{n:getattr(a,n)for n in names},qualification_sha=a.qualification_sha256,port=a.port)
    print(json.dumps(dict(status=r['status'],bundle_id=r['bundle_id']),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
