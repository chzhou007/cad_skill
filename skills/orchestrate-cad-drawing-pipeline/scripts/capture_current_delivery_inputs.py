"""Capture real current-viewer verifier inputs before claiming reproducibility.

Untracked process boundaries remain explicit; observed inputs alone are not a
self-contained reconstruction bundle. Reuses the original native observer and
the exact actual application verifier, without suppressing audit events.
"""
import argparse,copy,hashlib,json,os,sys,time
from pathlib import Path
import reuse_verified_native_artifact as original

MODE='current_axis_delivery_observed_input_capture_v1'

def process_event_metadata(executable,argv,cwd):
    original_arguments=list(argv)if isinstance(argv,(list,tuple))else[str(argv)]
    decoded=False;tokens=original_arguments
    if isinstance(argv,str)and os.name=='nt':
        import ctypes
        count=ctypes.c_int();parse=ctypes.windll.shell32.CommandLineToArgvW;parse.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_int)];parse.restype=ctypes.POINTER(ctypes.c_wchar_p)
        pointer=parse(argv,ctypes.byref(count))
        if pointer:
            try:tokens=[pointer[i]for i in range(count.value)];decoded=True
            finally:
                free=ctypes.windll.kernel32.LocalFree;free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_void_p;free(ctypes.cast(pointer,ctypes.c_void_p))
    command=next((x for x in tokens if x in ['reuse-native-artifact','reuse-bounded-attribute-artifact','reuse-riser-provider-artifact']),None)
    return dict(kind='subprocess',executable=str(executable)if executable is not None else(tokens[0]if tokens else None),executable_is_command_token=executable is None,cwd=str(cwd)if cwd else None,argument_fingerprint=hashlib.sha256(original.encode(original_arguments)).hexdigest(),windows_command_line_decoded=decoded,recognized_native_parent_command=command,node_inline_reader='--input-type=module'in tokens)

def compare_bindings(before,after):
    fields=sorted(k for k in before.keys()|after.keys()if before.get(k)!=after.get(k))
    return dict(changed_fields=fields,runtime_bindings_exact=not fields,resolver_path_changed='sys_path'in fields,
                immutable_runtime_code_and_context_exact=all(k=='sys_path'for k in fields),
                reusable_binding_proven=False)

def observed_input_states(closure,observer):
    changed=[];positive={};negative=[]
    for name,expected in closure['files'].items():
        actual=original.norm(observer._file_state(name))
        if actual!=expected:changed.append(dict(path=name,expected=expected,current=actual))
        elif expected[0]=='file':positive[name]=expected[-1]
        else:negative.append(dict(path=name,state=expected))
    for name,expected in closure['directories'].items():
        actual=original.norm(observer._dir_state(name))
        if actual!=expected:changed.append(dict(path=name,kind='directory',expected=expected,current=actual))
    for name,follow,expected in closure['probes']:
        actual=original.norm(observer._probe_state(name,follow))
        if actual!=expected:changed.append(dict(path=name,kind='probe',expected=expected,current=actual))
    return dict(status='observed_states_exact'if not changed else'observed_states_changed',positive_files=positive,negative_file_states=negative,changed=changed,process_inputs_proven_complete=False)

def capture(root,viewer,output,workers):
    root,viewer,output=[Path(p).resolve()for p in [root,viewer,output]]
    if output.exists():raise FileExistsError(output)
    for name in ['build-cad-pipe-topology','visualize-cad-pipe-topology']:
        sys.path.insert(0,str(root/name/'scripts'))
    from reuse_attribute_native_artifact import initialize_numerical_runtime
    initialize_numerical_runtime()
    import native_replay_session as observer
    from native_projection_runtime_v1 import default_native_runtime
    import refresh_effective_provider as owner
    if Path(owner.__file__).resolve()!=root/'visualize-cad-pipe-topology/scripts/refresh_effective_provider.py':raise ValueError('actual owner resolved outside supplied immutable skills')
    started=time.perf_counter();bound,key=original.binding(root,'refresh_effective_provider',viewer,workers);events=[];active=False
    def audit(event,args):
        if not active:return
        if event=='subprocess.Popen'and observer._trace.get()is not None:
            executable,argv,cwd,_=args;events.append(process_event_metadata(executable,argv,cwd))
    sys.addaudithook(audit)
    with default_native_runtime(root):
        with original.capture(observer)as reads:
            active=True
            try:result=owner.verify(viewer)
            finally:active=False
    if result.get('artifact_replay')!='passed'or result.get('human_accepted')is not False:raise ValueError('complete original current-viewer native gate did not pass')
    closure=original.closure_payload(reads);states=observed_input_states(closure,observer);after,after_key=original.binding(root,'refresh_effective_provider',viewer,workers)
    difference=compare_bindings(bound,after)
    output.mkdir(parents=True);(output/'observed-closure.json').write_bytes(original.encode(closure));(output/'observed-input-states.json').write_bytes(original.encode(states));(output/'runtime-and-skill-binding.json').write_bytes(original.encode(bound));(output/'runtime-and-skill-binding-after.json').write_bytes(original.encode(after));(output/'binding-difference.json').write_bytes(original.encode(difference))
    status='observed_inputs_captured_process_closure_unproven'if difference['runtime_bindings_exact']else'observed_inputs_captured_resolver_binding_and_process_closure_unproven'
    if states['changed']or not difference['immutable_runtime_code_and_context_exact']:status='dependency_or_immutable_runtime_binding_changed'
    report=dict(mode=MODE,status=status,viewer=str(viewer),skills_root=str(root),bundle_id=result['bundle_id'],native_verifier_result=result,source_binding_sha256=key,source_binding_after_sha256=after_key,binding_comparison=difference,observed_positive_files=len(states['positive_files']),observed_negative_file_states=len(states['negative_file_states']),observed_directories=len(closure['directories']),observed_probes=len(closure['probes']),original_observer_cacheable=closure['cacheable'],untracked_subprocesses=events,untracked_subprocess_count=len(events),original_observer_and_verifier_used=True,audit_events_suppressed=False,process_closure_complete=False,full_fixed_input_delivery_complete=False,new_pipe_values=0,new_HIL_questions=[],elapsed_seconds=time.perf_counter()-started,human_accepted=False,whole_goal_complete=False)
    (output/'verification.json').write_bytes(original.encode(report))
    if status=='dependency_or_immutable_runtime_binding_changed':raise ValueError('observed dependencies or immutable runtime bytes changed; complete diagnostics retained')
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--skills-root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--viewer',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=16);a=p.parse_args();r=capture(a.skills_root,a.viewer,a.output,a.workers);print({k:v for k,v in r.items()if k not in ['native_verifier_result','untracked_subprocesses']},flush=True)
if __name__=='__main__':main()
