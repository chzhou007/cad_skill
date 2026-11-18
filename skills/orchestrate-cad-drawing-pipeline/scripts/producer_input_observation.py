"""Record producer API outcomes, immutable inputs and owned-file provenance.

This opt-in observer complements the delivered input adapter. It does not
replace CAD owners, native stat values or the original read-only verifier.
Python API coverage is not an operating-system/native-C I/O sandbox.
"""
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
import stat
import threading
import time

# Imported by Runtime.__init__, before its process hooks are installed.
OPEN, STAT, LISTDIR, SCANDIR = open, os.stat, os.listdir, os.scandir


def sha(path):
    with OPEN(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


class Observation:
    def __init__(self, runtime, policy, binding):
        self.runtime, self.policy, self.binding = runtime, policy, binding
        if policy.get('mode') not in ('producer_API_input_discovery_v1', 'producer_API_input_enforcement_v1'):
            raise ValueError('Explicit producer observation mode required')
        self.strict = policy['mode'] == 'producer_API_input_enforcement_v1'
        self.guard = threading.local()
        self.lock = threading.RLock()
        self.events, self.inputs, self.errors, self.unresolved = {}, {}, [], {}
        self.input_changes=[]
        self.subprocesses=[]
        self.generated, self.journal_offsets = {}, {}
        self.seeds = policy.get('owned_seeds', {})
        for relative, expected in self.seeds.items():
            path = (runtime.work / relative).resolve()
            if not path.is_relative_to(runtime.work) or sha(path) != expected:
                raise ValueError('Producer seed changed or escaped work root')
            if expected in runtime.forbidden:
                raise ValueError('Historical final graph cannot be a producer seed')
        self.folder = runtime.work / 'producer-observation'
        self.folder.mkdir(exist_ok=True)
        self.journal = self.folder / f'{os.getpid()}-{runtime.started}.jsonl'
        self.physical = dict(runtime.physical_files)
        for relative in ('relative', 'policy_relative'):
            self.physical[runtime.key(runtime.package / binding[relative])] = binding[relative.replace('relative', 'sha256')]
        self.physical[runtime.key(runtime.adapter_path)] = runtime.index['adapter_sha256']
        index = runtime.package / 'indexes' / (runtime.index_sha256 + '.json')
        if not index.exists():
            index = runtime.package / 'logical-input-index.json'
        self.physical[runtime.key(index)] = runtime.index_sha256

    def quiet(self, function, *args):
        previous = getattr(self.runtime.guard, 'busy', False)
        self.runtime.guard.busy = True
        try:
            return function(*args)
        finally:
            self.runtime.guard.busy = previous

    def target(self, value, writing=False):
        r = self.runtime
        if not isinstance(value, (str, bytes, os.PathLike)):
            return None, 'descriptor_or_nonpath'
        if os.fsdecode(value) == '':
            return '', 'empty_native_probe'
        historical = r.historical_read_path(value) if not writing else None
        key = r.key(historical if historical is not None else value)
        if key == r.key(os.devnull):
            return key, 'platform_null_device'
        if re.fullmatch(r'\\\\\.\\pipe\\pyc-'+str(os.getpid())+r'-[0-9]+-[a-z0-9_]+',os.fsdecode(value),re.I):
            return key, 'current_process_multiprocessing_pipe_probe'
        generated = key if key in r.generated else r.generated_physical.get(key)
        if generated is not None:
            return r.key(r.work / r.generated[generated]['relative']), 'qualified_fresh_parent'
        if key in r.files:
            return r.key(r.package / r.files[key]['relative']), 'delivered_alias'
        if key in r.directories:
            return r.key(r.package / r.directories[key]), 'delivered_directory'
        if r.owned(key):
            if r.inside(key, self.folder):
                return key, 'observation_runtime_output'
            return key, 'owned_output'
        if r.packaged(key):
            return key, 'packaged_input'
        if key in r.negative:
            return key, 'declared_negative'
        return key, 'external_or_runtime_probe'

    def state(self, path, content=False, directory=False):
        if path in (None, ''):
            return dict(kind='nonpath' if path is None else 'empty')
        try:
            s = STAT(path)
        except OSError as e:
            return dict(kind='missing' if isinstance(e, FileNotFoundError) else 'stat_error',
                        errno=e.errno, winerror=getattr(e, 'winerror', None))
        result = dict(kind='directory' if stat.S_ISDIR(s.st_mode) else 'file' if stat.S_ISREG(s.st_mode) else 'special')
        try:
            if result['kind'] == 'file' and content:
                result.update(bytes=s.st_size, sha256=sha(path))
            if result['kind'] == 'directory' and directory:
                result['entries'] = LISTDIR(path)
        except OSError as e:
            return dict(kind='resource_error',errno=e.errno,winerror=getattr(e,'winerror',None))
        return result

    def known_writer(self, path):
        if path in self.generated:
            return self.generated[path]
        for name in LISTDIR(self.folder):
            if not name.endswith('.jsonl'):
                continue
            journal = self.folder / name
            offset = self.journal_offsets.get(name, 0)
            with OPEN(journal, 'rb') as f:
                f.seek(offset)
                while True:
                    line = f.readline()
                    if not line or not line.endswith(b'\n'):
                        break
                    row = json.loads(line)
                    self.generated[row['path']] = row
                    offset = f.tell()
            self.journal_offsets[name] = offset
        return self.generated.get(path)

    def record_write(self, path, operation, source=None):
        if not path or not self.runtime.owned(path):
            return
        row = dict(pid=os.getpid(), started_ns=self.runtime.started, time_ns=time.time_ns(),
                   operation=operation, path=path, source=source,
                   evidence='successful_Python_filesystem_API_return')
        with OPEN(self.journal, 'ab') as f:
            f.write((json.dumps(row, ensure_ascii=False) + '\n').encode('utf8'))
            f.flush()
        self.generated[path] = row

    def screen(self, path, role, state, operation, writing=False):
        if role in ('descriptor_or_nonpath', 'empty_native_probe', 'platform_null_device', 'observation_runtime_output'):
            return None
        if role=='current_process_multiprocessing_pipe_probe' and operation in ('stat','lstat'):
            return dict(role='original_exact_current_process_IPC_stat_probe')
        if role=='qualified_fresh_parent':
            if writing:raise PermissionError('Qualified generated parent input is read-only')
            key=self.runtime.generated_physical.get(path)
            if key is None:raise ValueError('Generated parent lacks its original input role')
            self.runtime.checked_generated(key)
            row=self.runtime.generated[key]
            if state.get('sha256',row['sha256'])!=row['sha256']:
                raise ValueError('Generated parent observed content differs')
            return dict(role='qualified_fresh_parent',sha256=row['sha256'],
                producer_receipt_sha256=row['producer_receipt_sha256'],producer_field=row['producer_field'])
        if role == 'owned_output':
            if state['kind'] == 'missing' or (writing and operation in ('open_truncate', 'mkdir')):
                return None
            if state['kind'] == 'directory':
                return None  # Its actual observed members remain in the event.
            relative = os.path.relpath(path, self.runtime.work).replace('\\', '/')
            writer = self.known_writer(path)
            if writer is not None:
                return dict(role='generated_owned_file', writer=writer)
            if relative in self.seeds:
                if state.get('sha256', self.seeds[relative]) != self.seeds[relative]:
                    raise ValueError('Producer owned seed changed: ' + relative)
                return dict(role='declared_owned_seed', relative=relative)
            reason = 'owned_read_without_seed_or_successful_writer'
        elif state['kind'] == 'file':
            expected = self.physical.get(path, self.policy.get('additional_files', {}).get(path))
            if expected is not None:
                if state.get('sha256', expected) != expected:
                    raise ValueError('Producer input changed: ' + path)
                return dict(role='fixed_file', sha256=expected)
            reason = 'packaged_or_external_file_not_fixed'
        elif state['kind'] == 'directory':
            expected = self.policy.get('directories', {}).get(path)
            if expected is not None and state.get('entries', expected) == expected:
                return dict(role='fixed_directory')
            reason = 'directory_state_not_fixed'
        elif state['kind'] == 'missing':
            if role == 'declared_negative' or path in self.policy.get('negative', []):
                return dict(role='fixed_negative')
            reason = 'missing_probe_not_fixed'
        else:
            reason = 'unqualified_resource_or_error'
        key = operation + ':' + str(path)
        self.unresolved[key] = dict(path=path, role=role, operation=operation, state=state, reason=reason)
        if self.strict:
            raise PermissionError('Unqualified producer input: ' + key + ' (' + reason + ')')
        return dict(role='discovery_unqualified', reason=reason)

    def remember_input(self,path,role,state):
        if not path or role in ('owned_output','observation_runtime_output','descriptor_or_nonpath',
                                'platform_null_device','empty_native_probe','current_process_multiprocessing_pipe_probe'):
            return
        if path not in self.inputs:
            # setdefault(key, expensive_snapshot()) evaluates the snapshot even
            # when key already exists. Pin once; retain per-read validation and
            # final rehash, instead of rehashing the same DXF after every stat.
            complete=(state['kind']=='file'and'sha256'in state)or(state['kind']=='directory'and'entries'in state)or state['kind']not in('file','directory')
            self.inputs[path]=state if complete else self.state(path,True,True)
        else:
            previous=self.inputs[path]
            comparable=('sha256'in state or'entries'in state or state['kind']not in('file','directory'))
            if comparable and previous!=state:
                self.input_changes.append(dict(path=path,before=previous,after=state,detected='later_API_observation'))

    def call(self, operation, function, args, kwargs, writing=False, truncate=False, destination=None):
        if getattr(self.guard, 'busy', False) or getattr(self.runtime.guard, 'busy', False):
            return function(*args, **kwargs)
        self.guard.busy = True
        path, role = self.quiet(self.target, args[0] if args else '.', writing)
        content = operation in ('open', 'io.open', 'os.open', 'open_code') and not truncate
        state = self.quiet(self.state, path, content, operation in ('listdir', 'scandir'))
        record = dict(operation=operation, path=path, role=role, before=state)
        try:
            record['provenance'] = self.quiet(self.screen, path, role, state,
                                              'open_truncate' if truncate else operation, writing)
            result = function(*args, **kwargs)
            record['outcome'] = 'returned'
            if writing:
                target = self.quiet(self.target, destination, True)[0] if destination is not None else path
                self.quiet(self.record_write, target, operation, path if destination is not None else None)
            return result
        except BaseException as e:
            record.update(outcome='raised', exception=type(e).__name__, errno=getattr(e, 'errno', None),
                          winerror=getattr(e, 'winerror', None))
            raise
        finally:
            self.quiet(self.remember_input,path,role,state)
            with self.lock:
                key = json.dumps(record, sort_keys=True, ensure_ascii=False)
                if key not in self.events:
                    self.events[key] = dict(record, count=0)
                self.events[key]['count'] += 1
            self.guard.busy = False

    def copy_file(self, operation, function, source, destination, **kwargs):
        """Observe the real copy return, including Windows CopyFile2 fast paths.

        The original library still copies bytes and metadata. Fixed input
        aliases and output boundaries are checked before its native call;
        a failed copy never grants generated-file identity.
        """
        if getattr(self.guard,'busy',False) or getattr(self.runtime.guard,'busy',False):
            return function(source,destination,**kwargs)
        self.guard.busy=True
        path,role=self.quiet(self.target,source)
        state=self.quiet(self.state,path,True,False)
        record=dict(operation=operation,path=path,role=role,before=state,
                    destination=self.quiet(self.target,destination,True)[0])
        try:
            record['provenance']=self.quiet(self.screen,path,role,state,operation)
            actual_source=self.quiet(self.runtime.translate,source,operation+'_source')
            actual_destination=self.quiet(self.runtime.translate,destination,operation+'_destination',True)
            result=function(actual_source,actual_destination,**kwargs)
            target=self.quiet(self.target,result,True)[0]
            self.quiet(self.record_write,target,operation,path)
            record.update(outcome='returned',actual_destination=target)
            return result
        except BaseException as e:
            record.update(outcome='raised',exception=type(e).__name__,errno=getattr(e,'errno',None),winerror=getattr(e,'winerror',None))
            raise
        finally:
            self.quiet(self.remember_input,path,role,state)
            with self.lock:
                key=json.dumps(record,sort_keys=True,ensure_ascii=False)
                if key not in self.events:self.events[key]=dict(record,count=0)
                self.events[key]['count']+=1
            self.guard.busy=False

    def native_event(self,event,args):
        # Audit events occur before native APIs return. Retain them as attempts,
        # never fabricate a successful return or generated-file ownership.
        if event!='open' or getattr(self.guard,'busy',False):return
        self.guard.busy=True
        try:
            value,mode,flags=args
            writing=(isinstance(mode,str)and any(c in mode for c in 'wax+'))or(mode is None and isinstance(flags,int)and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
            path,role=self.target(value,writing)
            before=self.state(path,not writing,False)
            provenance=self.screen(path,role,before,'native_open_attempt',writing)
            record=dict(operation='native_open_attempt',path=path,role=role,before=before,
                outcome='audit_attempt_only',writing=writing,provenance=provenance,count=1)
            key=json.dumps(record,sort_keys=True,ensure_ascii=False)
            if key in self.events:self.events[key]['count']+=1
            else:self.events[key]=record
            if not writing:self.remember_input(path,role,before)
        finally:self.guard.busy=False

    def install(self):
        import builtins, io, _io, subprocess
        r = self.runtime
        for name, api in [('open', 'open'), ('io_open', 'io.open'), ('os_open', 'os.open'),
                          ('stat', 'stat'), ('lstat', 'lstat'), ('listdir', 'listdir'), ('scandir', 'scandir')]:
            original = getattr(r, name)
            def bound(*args, _fn=original, _api=api, **kwargs):
                mode = args[1] if len(args) > 1 else kwargs.get('mode', 'r')
                writing = (bool(mode & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
                           if _api == 'os.open' else isinstance(mode, str) and any(c in mode for c in 'wax+')) if _api in ('open', 'io.open', 'os.open') else False
                truncate = bool(mode & os.O_TRUNC) if _api == 'os.open' else isinstance(mode, str) and 'w' in mode
                return self.call(_api, _fn, args, kwargs, writing, truncate)
            setattr(r, name, bound)
        builtins.open, io.open, os.open = r.open, r.io_open, r.os_open
        os.stat, os.lstat, os.listdir, os.scandir = r.stat, r.lstat, r.listdir, r.scandir
        original = _io.open_code
        def open_code(path,_fn=original):
            return self.call('open_code', _fn, (path,), {})
        _io.open_code = io.open_code = open_code
        original_copy2=shutil.copy2
        def copy2(src,dst,*,follow_symlinks=True):
            return self.copy_file('shutil.copy2',original_copy2,src,dst,follow_symlinks=follow_symlinks)
        shutil.copy2=copy2
        # copytree captured the old copy2 object as a function default when
        # shutil was imported. Replacing shutil.copy2 alone misses Windows'
        # native CopyFile2 fast path for recursive copies. Preserve custom
        # copy functions and the original recursion/metadata semantics.
        original_copytree=shutil.copytree
        def copytree(src,dst,symlinks=False,ignore=None,copy_function=original_copy2,
                     ignore_dangling_symlinks=False,dirs_exist_ok=False):
            selected=copy2 if copy_function is original_copy2 else copy_function
            return original_copytree(src,dst,symlinks,ignore,selected,
                                     ignore_dangling_symlinks,dirs_exist_ok)
        shutil.copytree=copytree
        for name in ('mkdir', 'remove', 'unlink', 'rmdir', 'rename', 'replace', 'chmod', 'utime'):
            original = getattr(os, name)
            def effect(*args, _fn=original, _name=name, **kwargs):
                destination = args[1] if _name in ('rename', 'replace') else None
                return self.call(_name, _fn, args, kwargs, True, _name=='mkdir', destination)
            setattr(os, name, effect)
        original_popen=subprocess.Popen
        observer=self
        class ObservedQualifiedPopen(original_popen):
            def __init__(self,args,*a,**kwargs):
                # Preserve the original adapter's executable/shape validation
                # and actual child. A launch attempt is not a completed child.
                try:
                    super().__init__(args,*a,**kwargs)
                except BaseException as e:
                    observer.subprocesses.append(dict(outcome='raised',exception=type(e).__name__,errno=getattr(e,'errno',None)))
                    raise
                observer.subprocesses.append(dict(outcome='created',pid=self.pid,parent_pid=os.getpid(),
                    executable_role='qualified_node' if isinstance(args,(list,tuple))and args and Path(str(args[0])).name.lower()in('node','node.exe') else 'qualified_python',
                    command_sha256=hashlib.sha256(repr(args).encode('utf8')).hexdigest()))
        subprocess.Popen=ObservedQualifiedPopen

    def finish(self):
        self.guard.busy = True
        def write():
            changed=list(self.input_changes)
            for path, previous in self.inputs.items():
                current=self.state(path,previous['kind']=='file',previous['kind']=='directory')
                if current!=previous:
                    changed.append(dict(path=path,before=previous,after=current))
            report=dict(mode=self.policy['mode'],pid=os.getpid(),parent_pid=os.getppid(),
                started_ns=self.runtime.started,finished_ns=time.time_ns(),input_index_sha256=self.runtime.index_sha256,
                helper_binding=self.binding,events=list(self.events.values()),immutable_inputs=self.inputs,
                changed_inputs=changed,unresolved=list(self.unresolved.values()),
                owned_successful_effects=list(self.generated.values()),owned_seed_hashes=self.seeds,
                qualified_subprocesses=self.subprocesses,
                strict_API_input_gate_passed=self.strict and not changed and not self.unresolved,
                original_API_return_and_exception_semantics_preserved_in_discovery=True,
                original_stat_metadata_faked=False,OS_security_sandbox=False,
                native_C_IO_coverage='Known original font/resource adapters only; no general native IO closure claimed',
                process_tree_closure_requires_separate_aggregation=True,human_accepted=False)
            path=self.folder/f'{os.getpid()}-{self.runtime.started}.json'
            with OPEN(path,'w',encoding='utf8')as f:json.dump(report,f,ensure_ascii=False,indent=2)
            return dict(path=str(path),sha256=sha(path),unresolved=len(self.unresolved),changed_inputs=len(changed),
                        strict_API_input_gate_passed=report['strict_API_input_gate_passed'])
        return self.quiet(write)
