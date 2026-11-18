"""Apply the unchanged complete-artifact cache to the current provider owner.

This adapter extends one explicit owner whitelist in a private namespace.
It never changes the original cache or native owner globals. Use the immutable
parent's complete skills root when later child rules should not invalidate it.
"""
import argparse,contextlib,os,sys,types
from pathlib import Path
import reuse_verified_native_artifact as original
import reuse_attribute_native_artifact as attribute_adapter
from checked_bounded_parent_observer_runtime import bounded_parent_runtime
from observed_vertical_DN_workers import observe_vertical_workers
OWNER='riser_header_provider_inventory'
PROOF='provider-inventory.json'

def reader():
    # Reuse the shipped preloading, observed Node reader and import-dependency
    # capture adapter as well as the complete-artifact engine. NumPy setup and
    # import-time sys.path changes must precede its before/after byte binding.
    preload_globals=dict(attribute_adapter.preload.__globals__,OWNER=OWNER)
    preload=types.FunctionType(attribute_adapter.preload.__code__,preload_globals,attribute_adapter.preload.__name__,attribute_adapter.preload.__defaults__,attribute_adapter.preload.__closure__)
    proxy=types.SimpleNamespace(**original.__dict__)
    @contextlib.contextmanager
    def observed_capture(observer):
        with original.capture(observer)as reads:
            Path(__file__).read_bytes()
            (Path(__file__).resolve().parents[1]/'assets/riser-provider-worker-environment.json').read_bytes()
            previous=observer._Reads.observe
            def observe(current,event,args):
                before=current.cacheable;value=previous(current,event,args)
                if before and not current.cacheable and event=='open':
                    examples=reads.capture_statistics.setdefault('untracked_open_examples',[])
                    item=dict(name=str(args[0])[:600],mode=args[1],flags=args[2])
                    if item not in examples and len(examples)<32:examples.append(item)
                return value
            observer._Reads.observe=observe
            try:
                with bounded_parent_runtime(root_for_capture[0],observer)as bridge:
                    with observe_vertical_workers(root_for_capture[0],observer)as vertical:
                        yield reads
                        reads.capture_statistics['observed_original_vertical_workers']=dict(vertical)
                    reads.capture_statistics['checked_bounded_parent_bridge']=dict(bridge.stats)
            finally:observer._Reads.observe=previous
    proxy.capture=observed_capture
    root_for_capture=[None]
    def configured_preload(root,observer):
        root_for_capture[0]=Path(root).resolve()
        return preload(root,observer)
    configured_preload._private_preload=preload
    namespace=dict(attribute_adapter.run.__globals__,OWNER=OWNER,PROOF=PROOF,preload=configured_preload,original=proxy)
    result=types.FunctionType(attribute_adapter.run.__code__,namespace,attribute_adapter.run.__name__,attribute_adapter.run.__defaults__,attribute_adapter.run.__closure__)
    result.__kwdefaults__=attribute_adapter.run.__kwdefaults__
    return result

def run(root,directory,cache_root,output,*,force_native=False,workers=16):
    # The shipped v2 runtime also attaches already imported verifier aliases.
    # Its original dependency checks remain active; v1 misses these aliases
    # after the required import preloading above.
    before={k:os.environ.get(k)for k in('CAD_NATIVE_OWNER_BATCH_VERSION','CODEX_TOOL_CALL_ID')}
    policy_path=Path(__file__).resolve().parents[1]/'assets/riser-provider-worker-environment.json'
    policy=original.load(policy_path)
    if policy.get('scope')!='isolated_pure_native_worker_only'or not isinstance(policy.get('stable_transport_context'),str)or not policy['stable_transport_context']:raise ValueError('fixed isolated worker environment policy required')
    os.environ.setdefault('CAD_NATIVE_OWNER_BATCH_VERSION','2');os.environ['CODEX_TOOL_CALL_ID']=policy['stable_transport_context']
    root=Path(root).resolve()
    for name in reversed(original.SKILLS):
        path=str(root/name/'scripts')
        if path not in sys.path:sys.path.insert(0,path)
    try:return reader()(root,directory,cache_root,output,force_native=force_native,workers=workers)
    finally:
        for k,v in before.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('skills-root','native-run','cache-root','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--force-native',action='store_true');p.add_argument('--workers',type=int,default=16);a=p.parse_args()
    r=run(a.skills_root,a.native_run,a.cache_root,a.output,force_native=a.force_native,workers=a.workers)
    print(original.encode(r).decode('utf8'),flush=True)
if __name__=='__main__':main()
