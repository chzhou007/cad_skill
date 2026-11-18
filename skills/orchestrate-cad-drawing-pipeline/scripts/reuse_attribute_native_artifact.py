"""Versioned application entry for the current bounded attribute artifact.

Reuse the unchanged complete capsule/closure engine, with one explicit owner
adapter and a fingerprinted read-only Node bridge. Original validate-* entries
and the original supported-owner table remain untouched.
"""
import argparse,contextlib,importlib,json,sys,sysconfig,types
from pathlib import Path
import reuse_verified_native_artifact as original
from native_attribute_read_runtime import attribute_read_runtime
OWNER='rebuild_bounded_main_complete_extents'
PROOF='bounded-main-extents.json'


def initialize_numerical_runtime():
    """Initialize NumPy before dependency observation, as runtime setup.

    Its reviewed package initialization temporarily sets/unsets an OpenBLAS
    environment variable. This must not happen inside a cacheable native read.
    The original engine subsequently binds the complete installed Python
    library trees, loaded interpreter bytes and the final environment, before
    and after native execution. No source/verifier operation is exempted.
    """
    module=importlib.import_module('numpy')
    location=Path(module.__file__).resolve()
    roots=[Path(sysconfig.get_path(key)).resolve()for key in('purelib','platlib')]
    if not any(location.is_relative_to(path)for path in roots):
        raise ValueError('numerical runtime must resolve inside bound installed libraries')


def preload(root,observer):
    """Stabilize actual imports before the original complete runtime binding.

    Import-time file/negative/configuration dependencies are merged into the
    native capture, rather than omitted just because imports happen first.
    """
    from native_owner_batch_runtime_v2 import OWNERS
    names=[OWNER,'qualified_crossview_provider_inventory','rebuild_ordered_owner_crossview',
        'rebuild_qualified_plan_scope_extension','native_exploded_caption_identity',
        'rebuild_ordered_sideview_owners','axis_attribute_source_routing',*OWNERS]
    with original.capture(observer)as reads:
        for name in dict.fromkeys(names):
            path=root/'build-cad-pipe-topology/scripts'/(name+'.py')
            if not path.is_file():continue
            module=importlib.import_module(name)
            if Path(module.__file__).resolve()!=path:raise ValueError('preloaded native owner outside supplied skills')
            fingerprint=getattr(module,'implementation_hashes',None)
            if callable(fingerprint):fingerprint()
        path=root/'visualize-cad-pipe-topology/scripts/refresh_qualified_plan_scope_attributes.py'
        if path.is_file():importlib.import_module('refresh_qualified_plan_scope_attributes')
    return reads


def run(root,directory,cache_root,output,*,force_native=False,workers=16):
    root=Path(root).resolve()
    for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
        p=str(root/name/'scripts')
        if p not in sys.path:sys.path.insert(0,p)
    initialize_numerical_runtime()
    with attribute_read_runtime(root)as runtime:
        import native_replay_session as observer
        initial=preload(root,observer)
        @contextlib.contextmanager
        def capture(obs):
            from native_owner_batch_runtime import merge_reads
            with original.capture(obs)as reads:
                merge_reads(reads,initial);reads.empty_read_probes.update(initial.empty_read_probes)
                previous=obs._Reads.observe
                def observed(current,event,args):
                    before=current.cacheable;value=previous(current,event,args)
                    if before and not current.cacheable:
                        counts=reads.capture_statistics.setdefault('uncacheable_event_types',{})
                        counts[event]=counts.get(event,0)+1
                    return value
                obs._Reads.observe=observed
                try:yield reads
                finally:obs._Reads.observe=previous
        namespace=dict(original.run.__globals__,OWNERS={OWNER:PROOF},capture=capture)
        entry=types.FunctionType(original.run.__code__,namespace,original.run.__name__,original.run.__defaults__,original.run.__closure__)
        entry.__kwdefaults__=original.run.__kwdefaults__
        result=entry(root,OWNER,directory,cache_root,output,force_native=force_native,workers=workers)
        result['attribute_reader_runtime']=dict(runtime.stats)if runtime else dict(enabled=False)
    result['application_entry']='bounded_attribute_artifact_with_shipped_readonly_reader_v1'
    (Path(output)/'execution.json').write_bytes(original.encode(result))
    return result


def main():
    p=argparse.ArgumentParser()
    for name in('native-run','cache-root','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--skills-root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--hash-workers',type=int,default=16);p.add_argument('--force-native',action='store_true');a=p.parse_args()
    r=run(a.skills_root,a.native_run,a.cache_root,a.output,force_native=a.force_native,workers=a.hash_workers)
    print(json.dumps({k:v for k,v in r.items()if k!='statistics'},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
