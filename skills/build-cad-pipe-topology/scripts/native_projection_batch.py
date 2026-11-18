"""Read native edge path projections in isolated processes with exact proofs."""
import argparse, concurrent.futures, os, platform, sys
from pathlib import Path
_pipeline=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(_pipeline)not in sys.path:sys.path.insert(0,str(_pipeline))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from reconstruct_native_block_branches import projected_coverage
from native_json_graph_copy_acceleration import accelerated_graph_copy

MODE='parallel_native_path_projection_batch_v1'
_doc=None;_graph=None;_source_hash=None

def selections(graph,manifest):
    by={e['edge_id']:e for e in graph['edges']}
    if len(by)!=len(graph['edges']):raise ValueError('duplicate graph edge identities')
    family=manifest['family']
    if family=='restored_native_block_branches':ids=[e['edge_id']for e in graph['edges']if e.get('source_native_block_branch')]
    elif family=='explicit_edge_scope':ids=manifest['edge_ids']
    else:raise ValueError('explicit native projection family required')
    if not ids or len(set(ids))!=len(ids)or not set(ids)<=set(by):raise ValueError('invalid or empty projection scope')
    return ids

def initialize(source,graph,sh,gh):
    global _doc,_graph,_source_hash
    if sha(source)!=sh or sha(graph)!=gh:raise ValueError('native worker input changed')
    _doc=read_source(source)[0];_graph=load(graph);_source_hash=sh

def work(edge_id):
    with accelerated_graph_copy():proof=projected_coverage(_doc,_graph,edge_id,_source_hash)
    return dict(edge_id=edge_id,projections=proof)

def implementation_hashes():
    return {str(p.relative_to(Path(__file__).resolve().parents[2])).replace('\\','/'):sha(p)for p in (
        Path(__file__),Path(__file__).with_name('reconstruct_native_block_branches.py'),Path(__file__).with_name('native_path_coverage_audit.py'),
        Path(__file__).with_name('native_line_path_evidence.py'),Path(__file__).with_name('source_readability.py'),_pipeline/'native_json_graph_copy_acceleration.py')}

def compute(manifest,workers=None):
    for key in ('source','graph'):
        if sha(manifest[key]['path'])!=manifest[key]['sha256']:raise ValueError('native projection input changed '+key)
    source=manifest['source'];graph=manifest['graph'];ids=selections(load(graph['path']),manifest)
    workers=int(os.environ.get('CAD_NATIVE_WORKERS',min(22,max(1,(os.cpu_count() or 2)-2))))if workers is None else workers
    if type(workers)is not int or workers<1 or workers>32:raise ValueError('native workers must be1..32')
    init=(source['path'],graph['path'],source['sha256'],graph['sha256'])
    if workers==1:
        initialize(*init);rows=[work(eid)for eid in ids]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=min(workers,len(ids)),initializer=initialize,initargs=init)as pool:rows=list(pool.map(work,ids,chunksize=3))
    if [r['edge_id']for r in rows]!=ids:raise ValueError('native projection outcome partition changed')
    if any(sha(manifest[k]['path'])!=manifest[k]['sha256']for k in ('source','graph')):raise ValueError('native inputs changed during worker batch')
    return dict(mode=MODE,source_sha256=source['sha256'],graph_sha256=graph['sha256'],family=manifest['family'],records=rows,edges=len(rows),
        geometry_kernels_unchanged=True,source_graph_mutated=False,topology_connections_assigned=0,physical_values_assigned=0,human_accepted=False)

def produce(manifest_path,output,workers=None):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest_path),workers);output.mkdir(parents=True);target=output/'native-projections.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=implementation_hashes(),
        runtime=dict(python=platform.python_version(),cache_tag=sys.implementation.cache_tag),output_sha256=sha(target),human_accepted=False)))
    return result

def verify_output(output,workers=None):
    output=Path(output);r=load(output/'receipt.json');m=r['manifest'];target=output/'native-projections.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=r['output_sha256']or r['runtime']!=dict(python=platform.python_version(),cache_tag=sys.implementation.cache_tag):raise ValueError('native projection binding changed')
    result=compute(load(m['path']),workers)
    if encode(result)!=target.read_bytes():raise ValueError('parallel native projection replay differs')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);p.add_argument('--workers',type=int);a=p.parse_args()
    if a.verify_output:
        if a.manifest or a.output:p.error('verification uses original manifest')
        r=verify_output(a.verify_output,a.workers)
    else:
        if not(a.manifest and a.output):p.error('manifest and new output required')
        r=produce(a.manifest,a.output,a.workers)
    print(dict(edges=r['edges'],physical_values_assigned=0),flush=True)
if __name__=='__main__':main()
