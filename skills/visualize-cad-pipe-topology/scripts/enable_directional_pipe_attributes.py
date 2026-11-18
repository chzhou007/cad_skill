"""Publish a source-bound horizontal/vertical attribute contract without changing CAD."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ASSETS=Path(__file__).resolve().parents[1]/'assets/viewer'
sys.path.insert(0,str(ASSETS))
from hil_server import identity
from refresh_reviewed_ring_partition_DN import effective

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf8'))
def dump(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def enable(parent,output,routing,port):
    parent,output,routing=map(lambda p:Path(p).resolve(),(parent,output,routing))
    if output.exists():raise FileExistsError(output)
    graph=load(parent/'public/data/graph.json');manifest=load(parent/'public/data/manifest.json')
    route=load(routing)
    if route.get('mode')!='axis_segment_attribute_source_routing_v1':raise ValueError('Qualified source direction routing required')
    receipt=load(routing.parent/'receipt.json')
    if receipt['output_sha256']!=sha(routing) or any(sha(item['path'])!=item['sha256']for item in receipt['inputs'].values()):raise ValueError('Native routing receipt or input changed')
    before=effective(parent)
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc','startup-logs'))
    module=output/'public/directional-pipe-attributes.js'
    shutil.copy2(ASSETS/'public/directional-pipe-attributes.js',module)
    folder=output/'directional-attribute-refresh';folder.mkdir()
    shutil.copy2(routing,folder/'source-direction-routing.json');dump(folder/'original-effective.json',before)
    script="""import fs from'node:fs';import{pathToFileURL}from'node:url';
const p=process.argv[1],a=await import(pathToFileURL(p+'/public/directional-pipe-attributes.js')),
g=JSON.parse(fs.readFileSync(p+'/public/data/graph.json')),r=JSON.parse(fs.readFileSync(p+'/directional-attribute-refresh/source-direction-routing.json')),
values=new Map(JSON.parse(fs.readFileSync(p+'/directional-attribute-refresh/original-effective.json')).map(x=>[x.edge_id,x.values]));
console.log(JSON.stringify(g.edges.map(e=>({edge_id:e.edge_id,system:e.system,pipe_attributes:a.directionalPipeAttributes(e,values.get(e.edge_id),r.records)}))));"""
    run=subprocess.run(['node','--input-type=module','-e',script,str(output)],capture_output=True,text=True,encoding='utf8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if run.returncode:raise ValueError(run.stderr)
    records=json.loads(run.stdout)
    bindings={name:dict(path=str(path),sha256=sha(path)) for name,path in {
        'published_graph':parent/'public/data/graph.json','published_manifest':parent/'public/data/manifest.json',
        'source_direction_routing':routing,'effective_values':folder/'original-effective.json'}.items()}
    doc=dict(schema='directional_pipe_topology_attributes_v1',source_bindings=bindings,records=records,
             source_values_changed=False,unresolved_values_preserved=True,human_accepted=False)
    target=output/'public/data/directional-pipe-attributes.json';dump(target,doc)
    enriched=copy.deepcopy(graph);by={r['edge_id']:r['pipe_attributes']for r in records}
    for e in enriched['edges']:e['pipe_attributes']=by[e['edge_id']]
    enriched['directionalAttributeContract']=dict(schema=doc['schema'],source_bindings=bindings,human_accepted=False)
    dump(output/'public/data/graph-with-directional-attributes.json',enriched)
    app=output/'public/app.js';text=app.read_text(encoding='utf8')
    if 'directionalCsvFields' in text:raise ValueError('Already enabled')
    text="import {directionalCsvFields,directionalCsvValues,initDirectionalAttributes} from './directional-pipe-attributes.js';\n"+text
    needle="...reviewCsvValues(e,crossViewAttributeCsvValues(e,data.attribute_value_context)),source_dimensioned_segments_json"
    if text.count(needle)!=1:raise ValueError('Actual export reader not recognized')
    text=text.replace(needle,"...reviewCsvValues(e,crossViewAttributeCsvValues(e,data.attribute_value_context)),...directionalCsvValues(data.directional_pipe_attributes.records.find(r=>r.edge_id===e.edge_id).pipe_attributes,reviewCsvValues(e,crossViewAttributeCsvValues(e,data.attribute_value_context))),source_dimensioned_segments_json")
    needle='...reviewCsvFields,...planMemberContactCsvFields]'
    if text.count(needle)!=1:raise ValueError('Complete existing export prefix required')
    text=text.replace(needle,'...reviewCsvFields,...planMemberContactCsvFields,...directionalCsvFields]')
    needle="await (await import('./edge-review.js')).initEdgeReview(window.cadViewer);"
    if text.count(needle)!=1:raise ValueError('Existing review initialization required')
    text=text.replace(needle,needle+"\n    await initDirectionalAttributes({...window.cadViewer,reviewValues:e=>reviewCsvValues(e,crossViewAttributeCsvValues(e,data.attribute_value_context))});")
    app.write_text(text,encoding='utf8')
    # This is an additive projection of the same source semantics: keep review identity/history.
    old_bundle=manifest['bundleId'];old_identity=identity(manifest)
    hashes={str(p.relative_to(output)).replace('\\','/'):sha(p)for p in [module,app,target,output/'public/data/graph-with-directional-attributes.json']}
    manifest['directionalPipeAttributes']=dict(path='data/directional-pipe-attributes.json',sha256=sha(target),
        schema=doc['schema'],original_graph_preserved=True,prior_semantics_and_review_identity_preserved=True,assets=hashes)
    manifest['templateHashes'].update({k:v for k,v in hashes.items()if not k.startswith('public/data/')})
    manifest['bundleId']=hashlib.sha256(json.dumps([old_bundle,hashes],sort_keys=True).encode()).hexdigest()[:20]
    manifest['preferredPort']=port
    if identity(manifest)!=old_identity:raise ValueError('Additive display changed review identity')
    dump(output/'public/data/manifest.json',manifest)
    index=output/'public/index.html';index.write_text(index.read_text(encoding='utf8').replace(old_bundle,manifest['bundleId']),encoding='utf8')
    if effective(output)!=before:raise ValueError('Existing effective attributes changed')
    for name in ['graph.json','edge-review-queue.json']:
        if sha(output/'public/data'/name)!=sha(parent/'public/data'/name):raise ValueError('Original graph or review queue changed')
    report=dict(status='unified_directional_attributes_published',parent=str(parent),viewer=str(output),
        bundleId=manifest['bundleId'],datasetId=old_identity,edges=len(records),review_labels=len(load(output/'public/data/edge-review-queue.json')['items']),
        original_graph_unchanged=True,all_old_effective_attributes_exact=True,annotations_copied=True,
        horizontal_length_known=sum(r['pipe_attributes']['horizontal']['length']['status']=='known'for r in records),
        vertical_length_known=sum(r['pipe_attributes']['vertical']['length']['status']=='known'for r in records),
        unified_attributes_sha256=sha(target),human_accepted=False,whole_goal_complete=False)
    dump(folder/'verification.json',report)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['parent','output','routing']:p.add_argument('--'+name,required=True)
    p.add_argument('--port',type=int,default=10564)
    a=p.parse_args();print(json.dumps(enable(a.parent,a.output,a.routing,a.port),ensure_ascii=False))
