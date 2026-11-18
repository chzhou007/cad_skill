"""Compose the original current verifier with exact pure Node input tracking.

This is a separate entry. Original verifiers, trace rules, capture and previous
receipts are unmodified. Unrecognized effects retain their uncacheable path.
"""
import argparse,importlib,json,sys,os,sysconfig
from pathlib import Path
import capture_current_delivery_inputs as previous
from current_attribute_read_runtime import current_attribute_read_runtime
from native_attribute_read_runtime import sha

def reobserve_initialized_inputs(initial,observer):
    """Re-read setup inputs after setup effects, retaining the original trace."""
    import reuse_verified_native_artifact as original
    closure=original.closure_payload(initial)
    if previous.observed_input_states(closure,observer)['changed']:raise ValueError('runtime initialization changed a read input; initialize its cache before capture')
    with original.capture(observer)as reads:
        for p in closure['files']:
            try:
                with open(p,'rb')as stream:
                    while stream.read(1024*1024):pass
            except FileNotFoundError:pass
        for p in closure['directories']:
            try:os.listdir(p)
            except FileNotFoundError:pass
        for p,follow,_ in closure['probes']:
            try:os.stat(p,follow_symlinks=follow)
            except FileNotFoundError:pass
    if previous.observed_input_states(closure,observer)['changed']:raise ValueError('runtime setup inputs changed during reobservation')
    return reads

def initialize_plotting_runtime(observer):
    import reuse_verified_native_artifact as original
    active=False;effects=[]
    def audit(event,args):
        if not active or observer._trace.get()is None:return
        if event in ('os.mkdir','os.remove','os.rename','os.putenv','os.unsetenv','subprocess.Popen','socket.connect'):
            effects.append(dict(event=event,path=os.fsdecode(args[0])if args and isinstance(args[0],(str,bytes,os.PathLike))else None))
        elif event=='open'and len(args)==3:
            name,mode,flags=args
            if isinstance(mode,str)and any(c in mode for c in 'wax+')or isinstance(flags,int)and flags&(os.O_WRONLY|os.O_RDWR):effects.append(dict(event='write_open',path=str(name)))
    sys.addaudithook(audit)
    with original.capture(observer)as initial:
        active=True
        try:module=importlib.import_module('matplotlib.pyplot')
        finally:active=False
    location=Path(module.__file__).resolve();roots=[Path(sysconfig.get_path(k)).resolve()for k in ('purelib','platlib')]
    if not any(location.is_relative_to(p)for p in roots):raise ValueError('plotting runtime outside bound installed libraries')
    mpl=importlib.import_module('matplotlib');cache_roots=[Path(mpl.get_cachedir()).resolve(),Path(mpl.get_configdir()).resolve()]
    if any(e['event']!='os.mkdir'or e['path']is None or not any(Path(e['path']).resolve().is_relative_to(p)for p in cache_roots)for e in effects):raise ValueError('unsupported plotting initialization effect; native observation not exempted')
    reads=reobserve_initialized_inputs(initial,observer)
    return reads,dict(mode='owned_plotting_initialization_before_native_binding_v1',original_setup_trace=original.closure_payload(initial),original_setup_cacheable=initial.cacheable,setup_effects=effects,input_reads_reobserved_with_original_observer=True,original_flags_reset=False)

def combine_observed_closure(captured,imports,observer):
    from checked_bounded_parent_observer_runtime import _tuple
    from native_owner_batch_runtime import merge_reads
    reads=observer._Reads(allow_owned_scratch=True)
    reads.files={k:_tuple(v)for k,v in captured['files'].items()};reads.directories={k:_tuple(v)for k,v in captured['directories'].items()};reads.probes={(p,follow):_tuple(v)for p,follow,v in captured['probes']};reads.scratch_roots=set(captured['scratch_roots']);reads.cacheable=captured['cacheable'];reads.empty_read_probes=set(map(tuple,captured['empty_read_probes']))
    merge_reads(reads,imports);reads.empty_read_probes.update(imports.empty_read_probes)
    return reads

def capture(root,viewer,output,policy,workers=16):
    root,viewer,output,policy=[Path(p).resolve()for p in [root,viewer,output,policy]]
    for name in ['build-cad-pipe-topology','visualize-cad-pipe-topology']:
        path=str(root/name/'scripts')
        if path not in sys.path:sys.path.insert(0,path)
    from reuse_attribute_native_artifact import initialize_numerical_runtime,preload
    initialize_numerical_runtime()
    import native_replay_session as observer
    import reuse_verified_native_artifact as original
    from checked_bounded_parent_observer_runtime import bounded_parent_runtime
    policy_hash=sha(policy)
    plotting_reads,plotting_setup=initialize_plotting_runtime(observer)
    # Import initialization is a separately retained dependency trace, not a
    # silent change to sys.path after the original before-binding snapshot.
    with original.capture(observer)as imports:
        from native_owner_batch_runtime import merge_reads
        merge_reads(imports,plotting_reads);imports.empty_read_probes.update(plotting_reads.empty_read_probes)
        runtime_context=current_attribute_read_runtime(root,policy)
        runtime=runtime_context.__enter__()
        importlib.import_module('refresh_effective_provider')
        for name,skill in [('refresh_fragment_component_index','visualize-cad-pipe-topology'),('rebuild_compound_member_bridges','build-cad-pipe-topology')]:
            module=importlib.import_module(name)
            if Path(module.__file__).resolve()!=root/skill/'scripts'/(name+'.py'):raise ValueError('native initialization owner outside supplied skills')
        initial=preload(root,observer)
        from native_owner_batch_runtime import merge_reads
        merge_reads(imports,initial);imports.empty_read_probes.update(initial.empty_read_probes)
        parent_context=bounded_parent_runtime(root,observer)
        parent_runtime=parent_context.__enter__()
    try:
        events=[];active=True
        def audit(event,args):
            if event!='subprocess.Popen'or not active or observer._trace.get()is None:return
            frames=[];frame=sys._getframe(1)
            while frame:
                filename=frame.f_code.co_filename
                try:inside=Path(filename).is_relative_to(root)
                except ValueError:inside=False
                if inside:frames.append(dict(file=filename,function=frame.f_code.co_name,line=frame.f_lineno))
                frame=frame.f_back
            events.append(dict(process=previous.process_event_metadata(args[0],args[1],args[2]),owned_call_stack=frames[:12]))
        sys.addaudithook(audit)
        result=previous.capture(root,viewer,output,workers)
        active=False
        if sha(policy)!=policy_hash:raise ValueError('current reader policy changed during complete verifier')
        from native_owner_batch_runtime import merge_reads
        # Retain import evidence explicitly. Existing native capture files keep
        # their exact bytes; the combined closure is a new separate artifact.
        captured=original.load(output/'observed-closure.json');reads=combine_observed_closure(captured,imports,observer)
        combined=original.closure_payload(reads);states=previous.observed_input_states(combined,observer)
        (output/'combined-observed-closure.json').write_bytes(original.encode(combined));(output/'combined-input-states.json').write_bytes(original.encode(states))
        strict=original.check_closure(combined,observer,workers)
        report=dict(mode='current_readonly_attribute_complete_input_observation_v1',original_capture=result,reader_runtime=runtime.stats if runtime else dict(enabled=False),reader_policy=dict(path=str(policy),sha256=policy_hash),original_capture_source_sha256=sha(Path(previous.__file__)),combined_observer_cacheable=combined['cacheable'],combined_closure_check_passed=strict,input_states_exact=not states['changed'],runtime_bindings_exact=result['binding_comparison']['runtime_bindings_exact'],untracked_subprocess_count=result['untracked_subprocess_count'],process_closure_complete=strict and result['untracked_subprocess_count']==0 and result['binding_comparison']['runtime_bindings_exact'],full_fixed_input_delivery_complete=False,human_accepted=False,whole_goal_complete=False)
        report['untracked_process_call_stacks']=events
        report['original_checked_bounded_parent_bridge']=dict(parent_runtime.stats)
        (output/'plotting-runtime-initialization.json').write_bytes(original.encode(plotting_setup))
        report['plotting_initialization']=dict(original_setup_cacheable=plotting_setup['original_setup_cacheable'],setup_effects=plotting_setup['setup_effects'],input_reads_reobserved_with_original_observer=True,original_flags_reset=False)
        (output/'readonly-verification.json').write_bytes(original.encode(report));return report
    finally:
        active=False
        parent_context.__exit__(None,None,None)
        runtime_context.__exit__(None,None,None)

def main():
    p=argparse.ArgumentParser();p.add_argument('--skills-root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--viewer',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--reader-policy',type=Path);p.add_argument('--workers',type=int,default=16);a=p.parse_args();policy=a.reader_policy or a.skills_root/'orchestrate-cad-drawing-pipeline/assets/current-attribute-reader-policy.json';r=capture(a.skills_root,a.viewer,a.output,policy,a.workers);print({k:v for k,v in r.items()if k!='original_capture'},flush=True)
if __name__=='__main__':main()
