"""Owned persistent projection workers; line JSON protocol only on stdout."""
import argparse,concurrent.futures,contextlib,hashlib,io,json,os,sys,time
from collections import OrderedDict
from pathlib import Path
_data=OrderedDict();_root=None

def kernel(root):
    global _root
    if _root==root:return
    root=Path(root)
    # Only these unchanged source geometry kernels are needed by projections.
    for name in ('reconstruct_native_block_branches','native_path_coverage_audit','native_line_path_evidence','source_readability','confirm_crossview_paths'):
        sys.modules.pop(name,None)
    sys.path[:0]=[str(root/x/'scripts')for x in ('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline')]
    _root=str(root)

def work(task):
    root,source,graph,sh,gh,eid=task;kernel(root)
    from confirm_crossview_paths import load,sha
    from source_readability import read_source
    from native_source_snapshot_runtime import native_allocation_window
    import reconstruct_native_block_branches as geometry_kernel
    from native_projection_value_runtime_v1 import projected
    key=(source,graph,sh,gh)
    if key not in _data:
        if sha(source)!=sh or sha(graph)!=gh:raise ValueError('projection worker input changed')
        with contextlib.redirect_stdout(io.StringIO()),native_allocation_window():doc=read_source(source)[0]
        _data[key]=(doc,load(graph))
        while len(_data)>4:_data.popitem(last=False)
    else:_data.move_to_end(key)
    doc,g=_data[key]
    try:
        with contextlib.redirect_stdout(io.StringIO()):result=projected(geometry_kernel,doc,g,eid,sh)
        return eid,dict(status='ok',proof=result)
    except (ValueError,KeyError,TypeError)as exc:return eid,dict(status='failed',error_type=type(exc).__name__,error=str(exc))

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,required=True);a=p.parse_args()
    if not 1<=a.workers<=32:raise ValueError('workers1..32 required')
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers)as pool:
        for line in sys.stdin:
            request=json.loads(line)
            if request.get('command')=='close':break
            started=time.monotonic()
            try:
                tasks=[(request['root'],request['source'],request['graph'],request['source_sha256'],request['graph_sha256'],eid)for eid in request['edge_ids']]
                rows=dict(pool.map(work,tasks,chunksize=2))
                response=dict(status='ok',records=rows,elapsed_seconds=time.monotonic()-started)
            except BaseException as exc:response=dict(status='failed',error_type=type(exc).__name__,error=str(exc))
            print(json.dumps(response,ensure_ascii=False,separators=(',',':')),flush=True)
if __name__=='__main__':main()
