"""Process-local, content-checked historical input aliases for CAD replay.

No source JSON is rewritten. Input stat values are the actual delivered-file
stat values; original cache/proof guards may invalidate and replay normally.
This is an API-level resource adapter, not an OS security sandbox.
"""
from pathlib import Path
import atexit
import builtins
import contextlib
import errno
import hashlib
import io
import _io
import importlib.machinery
import importlib.util
import importlib._bootstrap_external as import_backend
import json
import os
import runpy
import re
import subprocess
import sys
import threading
import time

NATIVE_OPEN=builtins.open
NATIVE_IO_OPEN=io.open
NATIVE_OPEN_CODE=_io.open_code
NATIVE_OS_OPEN=os.open
NATIVE_STAT=os.stat
NATIVE_LSTAT=os.lstat
NATIVE_LISTDIR=os.listdir
NATIVE_SCANDIR=os.scandir
NATIVE_REALPATH=os.path.realpath
NATIVE_POPEN=subprocess.Popen
NATIVE_ADD_DLL_DIRECTORY=getattr(os,'add_dll_directory',None)


class MissingDeliveredInput(OSError):
    pass


def digest(path):
    with NATIVE_OPEN(path,'rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()


class Runtime:
    def __init__(self,package,work,index_sha256):
        self.package=Path(package).resolve();self.work=Path(work).resolve()
        self.adapter_path=Path(__file__).resolve()
        if self.package.is_relative_to(self.work)or self.work.is_relative_to(self.package):raise ValueError('Input package and writable output roots must be disjoint')
        index_path=self.package/'indexes'/(index_sha256+'.json')
        if not index_path.exists():index_path=self.package/'logical-input-index.json'
        if digest(index_path)!=index_sha256:raise ValueError('Logical input index changed')
        self.index_sha256=index_sha256
        self.index=json.loads(index_path.read_text('utf8'))
        if self.index.get('adapter_sha256')!=digest(self.adapter_path):raise ValueError('Input execution adapter changed')
        self.files=self.index['files'];self.directories=self.index['directories'];self.negative=set(self.index['negative'])
        self.derived_cache_roots={}
        for logical,row in self.index.get('derived_cache_roots',{}).items():
            if not os.path.isabs(logical)or row.get('mode')!='derived_cache_from_fixed_parent_application_v1':
                raise ValueError('Derived cache requires an explicit fixed parent role')
            target=(self.work/row['relative']).resolve()
            if not target.is_relative_to(self.work)or target==self.work:
                raise ValueError('Derived cache escaped owned work root')
            declaration=self.files.get(self.key(row['manifest']))
            if not declaration or declaration['sha256']!=row['manifest_sha256']:
                raise ValueError('Derived cache manifest is not a fixed delivered input')
            manifest=(self.package/declaration['relative']).resolve()
            if not manifest.is_relative_to(self.package)or digest(manifest)!=row['manifest_sha256']:
                raise ValueError('Derived cache manifest changed')
            value=json.loads(manifest.read_text('utf8'))['parent_application']['cache_root']
            if self.key(value)!=self.key(logical):raise ValueError('Derived cache differs from fixed parent role')
            if not target.is_dir():raise ValueError('Derived cache must be materialized in owned work root')
            self.derived_cache_roots[self.key(logical)]=str(target)
        self.forbidden=set(self.index['forbidden_historical_final_graph_hashes'])
        self.guard=threading.local();self.lock=threading.RLock();self.events=[];self.misses=[]
        self.started=time.time_ns();self.resource_wrappers=[];self.import_negative_probes=[]
        self.runtime_probes=[];self.spawn_requests=[];self.spawn_token=None
        self.qualified_node_calls=[];self.node_bridge=None
        self.read_cwd=self.index.get('historical_read_cwd')
        self.generated=self.index.get('generated_local_parents',{});self.generated_physical={}
        for key,row in self.generated.items():
            target=(self.work/row['relative']).resolve();receipt=(self.work/row['producer_receipt_relative']).resolve()
            if not target.is_relative_to(self.work)or not receipt.is_relative_to(self.work):raise ValueError('Generated parent escaped owned work root')
            if digest(receipt)!=row['producer_receipt_sha256']:raise ValueError('Generated parent producer receipt changed')
            proof=json.loads(receipt.read_text('utf8'))
            pointer=row['producer_field']
            if (proof.get('mode')!='raw_CAD_to_current_local_topology_delivered_API_input_replay_v1'or
                len(pointer)!=3 or pointer[0]!='local_topologies'or type(pointer[1])is not int or pointer[1]<0 or pointer[2]not in('graph','components')):
                raise ValueError('Generated parent requires actual output role, not a historical reference')
            record=proof['local_topologies'][pointer[1]]
            if record.get('graph_and_component_bytes_exact')is not True or record[pointer[2]]['sha256']!=row['sha256']:
                raise ValueError('Generated parent differs from qualified producer output')
            if digest(target)!=row['sha256']:raise ValueError('Generated parent bytes changed')
            self.generated_physical[self.key(target)]=key
        self.physical_files={}
        for row in self.files.values():
            target=(self.package/row['relative']).resolve()
            if not target.is_relative_to(self.package):raise ValueError('Input alias escaped delivered package')
            self.physical_files[self.key(target)]=row['sha256']
        if self.index.get('packaged_runtime_role'):
            role=self.index['packaged_runtime_role'];path=(self.package/role['relative']).resolve()
            if not path.is_relative_to(self.package)or digest(path)!=role['sha256']:raise ValueError('Packaged runtime role changed')
            manifest=json.loads(path.read_text('utf8'))
            if manifest.get('mode')!='delivered_standard_python_library_role_v1'or self.key(self.package/manifest['executable'])!=self.key(sys.executable):raise ValueError('Packaged interpreter does not match execution role')
            for relative,expected in manifest['files'].items():
                target=(self.package/relative).resolve()
                if not target.is_relative_to(self.package):raise ValueError('Packaged runtime role escaped package')
                self.physical_files[self.key(target)]=expected
        self.children={key:{}for key in self.directories}
        spellings=self.index.get('entry_spellings',{})
        for key,name in spellings.items():
            if os.path.basename(name)!=name or name.lower()!=os.path.basename(key).lower():raise ValueError('Entry spelling changes logical identity')
        for key,row in self.files.items():
            parent=self.key(os.path.dirname(key))
            if parent in self.children:self.children[parent][os.path.basename(key)]=dict(name=spellings.get(key,Path(row['relative']).name),directory=False,key=key)
        for key,relative in self.directories.items():
            parent=self.key(os.path.dirname(key));name=os.path.basename(key)
            if parent in self.children:
                # Assembly directory stubs retain recorded native case.
                physical_parent=self.package/self.directories[parent]
                candidates=[v for v in NATIVE_LISTDIR(physical_parent)if v.lower()==name.lower()]
                self.children[parent][name]=dict(name=spellings.get(key,candidates[0]if candidates else name),directory=True,key=key)
        self.producer_observer=None
        if self.index.get('producer_observation'):
            binding=self.index['producer_observation']
            for path_key,hash_key in [('relative','sha256'),('policy_relative','policy_sha256')]:
                path=(self.package/binding[path_key]).resolve()
                if not path.is_relative_to(self.package)or digest(path)!=binding[hash_key]:
                    raise ValueError('Producer observation helper/policy changed')
            path=self.package/binding['relative']
            spec=importlib.util.spec_from_file_location('delivered_producer_observation',path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            policy=json.loads((self.package/binding['policy_relative']).read_text('utf8'))
            self.producer_observer=module.Observation(self,policy,binding)
    def key(self,path):return os.path.normcase(os.path.abspath(os.fsdecode(path)))
    def inside(self,path,root):
        key=self.key(path);base=self.key(root)
        return key==base or key.startswith(base+os.sep)
    def owned(self,path):return self.inside(path,self.work)
    def packaged(self,path):return self.inside(path,self.package)
    def historical_read_path(self,path):
        if not self.read_cwd or not isinstance(path,(str,bytes,os.PathLike)):return None
        value=os.fsdecode(path)
        if not os.path.isabs(value):relative=value
        elif self.owned(value):relative=os.path.relpath(value,self.work)
        else:return None
        candidate=os.path.abspath(os.path.join(self.read_cwd,relative));key=self.key(candidate)
        if key in self.files or key in self.generated or key in self.directories or key in self.negative:return candidate
        return None
    def fail(self,path,operation):
        key=self.key(path);self.misses.append(dict(path=key,operation=operation))
        raise MissingDeliveredInput('Unrecorded external input: '+operation+' '+key)
    def checked_file(self,key):
        row=self.files[key];target=self.package/row['relative']
        actual=digest(target)
        if actual!=row['sha256']:raise ValueError('Delivered input bytes changed: '+key)
        if actual in self.forbidden:raise ValueError('Historical final graph cannot be a production input: '+key)
        self.events.append(dict(path=key,sha256=actual,physical=str(target)))
        return str(target)
    def checked_generated(self,key):
        row=self.generated[key];target=self.work/row['relative']
        if digest(target)!=row['sha256']:raise ValueError('Generated parent bytes changed: '+key)
        receipt=self.work/row['producer_receipt_relative']
        if digest(receipt)!=row['producer_receipt_sha256']:raise ValueError('Generated parent producer receipt changed')
        self.events.append(dict(path=key,sha256=row['sha256'],physical=str(target),input_role='fresh_generated_local_parent',
            producer_receipt_sha256=row['producer_receipt_sha256']))
        return str(target)
    def translate(self,path,operation='read',write=False):
        if not isinstance(path,(str,bytes,os.PathLike)):return path
        if os.fsdecode(path)=='':return path # Original ezdxf empty-read rejection.
        if self.key(path)==self.key(os.devnull):return os.devnull
        if operation=='stat'and re.fullmatch(r'\\\\\.\\pipe\\pyc-'+str(os.getpid())+r'-[0-9]+-[a-z0-9_]+',os.fsdecode(path),re.I):
            self.runtime_probes.append(dict(path=os.fsdecode(path),role='current_process_multiprocessing_pipe_address_probe'))
            return path
        if not write:
            historical=self.historical_read_path(path)
            if historical is not None:path=historical
        if 'font' in operation.lower()and not os.path.isabs(path)and not os.path.dirname(path):
            matches=[key for key in self.files if os.path.basename(key)==os.fsdecode(path).lower()]
            if len({self.files[key]['sha256']for key in matches})==1 and matches:return self.checked_file(matches[0])
        key=self.key(path)
        generated_key=key if key in self.generated else self.generated_physical.get(key)
        if generated_key is not None:
            if write:raise PermissionError('Generated parent input is read-only: '+key)
            return self.checked_generated(generated_key)
        if self.owned(key):return path
        if write:raise PermissionError('Write outside fresh output root: '+key)
        if self.packaged(key):
            if key in self.physical_files:
                expected=self.physical_files[key]
                if digest(path)!=expected:raise ValueError('Physical delivered input changed: '+key)
                if expected in self.forbidden:raise ValueError('Historical final graph cannot be a production input: '+key)
            return path
        if key in self.files:return self.checked_file(key)
        if key in self.negative:raise FileNotFoundError(errno.ENOENT,'Recorded absent input',key)
        if key in self.directories:return str(self.package/self.directories[key])
        if operation=='stat'and getattr(self.guard,'import_probe',False):
            self.import_negative_probes.append(key);raise FileNotFoundError(errno.ENOENT,'Absent import candidate',key)
        return self.fail(path,operation)
    def open(self,path,mode='r',*args,**kwargs):
        writing=isinstance(mode,str)and any(c in mode for c in 'wax+')
        return NATIVE_OPEN(self.translate(path,'open',writing),mode,*args,**kwargs)
    def io_open(self,path,mode='r',*args,**kwargs):
        writing=isinstance(mode,str)and any(c in mode for c in 'wax+')
        return NATIVE_IO_OPEN(self.translate(path,'io.open',writing),mode,*args,**kwargs)
    def os_open(self,path,flags,*args,**kwargs):
        writing=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        return NATIVE_OS_OPEN(self.translate(path,'os.open',writing),flags,*args,**kwargs)
    def stat(self,path,*,dir_fd=None,follow_symlinks=True):
        if isinstance(path,int):return NATIVE_STAT(path,dir_fd=dir_fd,follow_symlinks=follow_symlinks)
        physical=self.translate(path,'stat')
        return NATIVE_STAT(physical,dir_fd=dir_fd,follow_symlinks=follow_symlinks)
    def lstat(self,path,*,dir_fd=None):return self.stat(path,dir_fd=dir_fd,follow_symlinks=False)
    def realpath(self,path,*,strict=False):
        if not isinstance(path,(str,bytes,os.PathLike)):return NATIVE_REALPATH(path,strict=strict)
        historical=self.historical_read_path(path)
        if historical is not None:path=historical
        key=self.key(path)
        if key in self.derived_cache_roots:
            # Original cache owners resolve the cache root before forming any
            # lookup/temp/rename path. Only that declared execution resource
            # moves; source/proof paths and their containment checks stay.
            return NATIVE_REALPATH(self.derived_cache_roots[key],strict=strict)
        if self.owned(key)or self.packaged(key):return NATIVE_REALPATH(path,strict=strict)
        if key in self.files or key in self.directories:return os.path.abspath(os.fsdecode(path))
        if key in self.negative:
            if strict:raise FileNotFoundError(errno.ENOENT,'Recorded absent input',key)
            return os.path.abspath(os.fsdecode(path))
        # Computing an unshown path is allowed; accessing it still fails closed.
        return os.path.abspath(os.fsdecode(path))
    def listdir(self,path='.'):
        historical=self.historical_read_path(path)
        if historical is not None:path=historical
        key=self.key(path)
        if not(self.owned(key)or self.packaged(key))and key in self.children:return [v['name']for v in self.children[key].values()]
        physical=self.translate(path,'listdir')
        return NATIVE_LISTDIR(physical)
    def scandir(self,path='.'):
        historical=self.historical_read_path(path)
        if historical is not None:path=historical
        key=self.key(path)
        if not(self.owned(key)or self.packaged(key))and key in self.children:
            runtime=self;logical=os.fsdecode(path)
            class VirtualEntry:
                def __init__(self,value):self.value=value;self.name=value['name'];self.path=os.path.join(logical,self.name)
                def __fspath__(self):return self.path
                def is_dir(self,*,follow_symlinks=True):return self.value['directory']
                def is_file(self,*,follow_symlinks=True):return not self.value['directory']
                def is_symlink(self):return False
                def is_junction(self):return False
                def stat(self,*,follow_symlinks=True):return runtime.stat(self.path,follow_symlinks=follow_symlinks)
                def inode(self):return self.stat().st_ino
            class VirtualIterator:
                def __init__(self):self.values=iter(runtime.children[key].values())
                def __iter__(self):return self
                def __next__(self):return VirtualEntry(next(self.values))
                def close(self):pass
                def __enter__(self):return self
                def __exit__(self,*args):pass
            return VirtualIterator()
        physical=self.translate(path,'scandir')
        native=NATIVE_SCANDIR(physical)
        runtime=self
        logical=os.fsdecode(path)
        class Entry:
            def __init__(self,value):self.value=value;self.name=value.name;self.path=os.path.join(logical,value.name)
            def __fspath__(self):return self.path
            def is_dir(self,*,follow_symlinks=True):return self.value.is_dir(follow_symlinks=follow_symlinks)
            def is_file(self,*,follow_symlinks=True):return self.value.is_file(follow_symlinks=follow_symlinks)
            def is_symlink(self):return self.value.is_symlink()
            def is_junction(self):return self.value.is_junction()
            def stat(self,*,follow_symlinks=True):return runtime.stat(self.path,follow_symlinks=follow_symlinks)
            def inode(self):return runtime.stat(self.path).st_ino
        class Iterator:
            def __iter__(self):return self
            def __next__(self):return Entry(next(native))
            def close(self):native.close()
            def __enter__(self):return self
            def __exit__(self,*args):native.close()
        return Iterator()
    def audit(self,event,args):
        if getattr(self.guard,'busy',False):return
        self.guard.busy=True
        try:
            if self.producer_observer is not None:self.producer_observer.native_event(event,args)
            if event=='open':
                name,mode,flags=args
                if not isinstance(name,(str,bytes,os.PathLike))or os.fsdecode(name)=='':return
                if self.key(name)==self.key(os.devnull):return
                writing=(isinstance(mode,str)and any(c in mode for c in 'wax+'))or(mode is None and isinstance(flags,int)and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
                if writing and not self.owned(name):raise PermissionError('Unowned file write: '+self.key(name))
                if not writing and not(self.owned(name)or self.packaged(name)):
                    self.fail(name,'untranslated native open')
            elif event in ('os.mkdir','os.remove','os.rmdir','os.rename','os.replace','os.unlink','os.chmod','os.utime','os.link','os.symlink'):
                values=args[:2]if event in('os.rename','os.replace','os.link','os.symlink')else args[:1]
                for name in values:
                    if isinstance(name,(str,bytes,os.PathLike))and(self.key(name)in self.generated or self.key(name)in self.generated_physical):raise PermissionError('Generated parent input is read-only')
                    if isinstance(name,(str,bytes,os.PathLike))and not self.owned(name):raise PermissionError('Unowned filesystem effect: '+event+' '+self.key(name))
            elif event=='import'and len(args)>1 and isinstance(args[1],str)and os.path.isabs(args[1]):
                if args[1].lower().endswith(('.pyd','.dll','.so'))and not(self.packaged(args[1])or self.owned(args[1])):
                    self.fail(args[1],'untranslated native module import')
        finally:self.guard.busy=False
    def install_native_fonts(self):
        # Explicitly bind known native font constructors; do not pretend that
        # C extensions' fopen calls are observed by Python's open audit alone.
        import PIL.ImageFont as pil
        original=pil.truetype
        runtime=self
        def bound_truetype(font,*args,**kwargs):
            if isinstance(font,(str,bytes,os.PathLike)):font=runtime.translate(font,'Pillow.truetype')
            return original(font,*args,**kwargs)
        pil.truetype=bound_truetype
        self.resource_wrappers.append(dict(module='PIL.ImageFont',original_source_sha256=digest(pil.__file__)))
        import matplotlib.font_manager as fm
        original_get=fm._get_font;original_add=fm.FontManager.addfont
        def bound_get(paths,*args,**kwargs):
            paths=tuple((runtime.translate(path,'matplotlib font resource'),index)for path,index in paths)
            return original_get(paths,*args,**kwargs)
        bound_get.cache_clear=original_get.cache_clear
        bound_get.cache_info=original_get.cache_info
        def bound_add(manager,path):return original_add(manager,runtime.translate(path,'matplotlib addfont'))
        fm._get_font=bound_get;fm.FontManager.addfont=bound_add
        self.resource_wrappers.append(dict(module='matplotlib.font_manager',original_source_sha256=digest(fm.__file__)))
    def install_multiprocessing(self):
        import multiprocessing.spawn as spawn
        runtime=self
        def bound_command(**kwargs):
            if runtime.key(spawn.get_executable())!=runtime.key(sys.executable):raise PermissionError('Unqualified multiprocessing interpreter')
            if set(kwargs)-{'pipe_handle','parent_pid','tracker_fd'}or any(v is not None and type(v)is not int for v in kwargs.values()):
                raise ValueError('Unsupported native multiprocessing child shape')
            if kwargs.get('parent_pid',os.getpid())!=os.getpid():raise ValueError('Multiprocessing parent differs')
            token=hashlib.sha256(f'{os.getpid()}:{runtime.started}:{len(runtime.spawn_requests)}'.encode()).hexdigest()
            # Windows' native spawn quotes every argument itself. Hex avoids
            # introducing nested JSON quotes into that original command builder.
            descriptor=json.dumps(dict(kwargs=kwargs,spawn_token=token),separators=(',',':')).encode('utf8').hex()
            command=[sys.executable,'-I','-X','utf8','-B',str(runtime.adapter_path),str(runtime.package),str(runtime.work),runtime.index_sha256,'--multiprocessing-spawn-child',descriptor]
            runtime.spawn_requests.append(dict(spawn_token=token,parent_pid=os.getpid(),command_sha256=hashlib.sha256(json.dumps(command).encode()).hexdigest()))
            return command
        spawn.get_command_line=bound_command
        self.resource_wrappers.append(dict(module='multiprocessing.spawn',original_source_sha256=digest(spawn.__file__)))
    def finish(self):
        report=dict(mode='content_checked_sealed_source_alias_execution_v1',pid=os.getpid(),parent_pid=os.getppid(),
            started_ns=self.started,finished_ns=time.time_ns(),executable=sys.executable,script=sys.argv[0],
            external_reads=self.events,unrecorded_reads=self.misses,native_resource_wrappers=self.resource_wrappers,
            runtime_resource_probes=self.runtime_probes,multiprocessing_spawn_requests=self.spawn_requests,multiprocessing_spawn_token=self.spawn_token,
            qualified_node_calls=self.qualified_node_calls,
            import_resolution_negative_candidates=sorted(set(self.import_negative_probes)),input_index_sha256=self.index_sha256,
            original_input_JSON_rewritten=False,original_cache_stat_metadata_faked=False,
            OS_security_sandbox=False,human_accepted=False)
        report['permitted_non_file_resources']=['platform null device: '+os.devnull]
        if self.producer_observer is not None:report['producer_observation']=self.producer_observer.finish()
        folder=self.work/'access-receipts';folder.mkdir(exist_ok=True)
        with NATIVE_OPEN(folder/f'{os.getpid()}-{self.started}.json','w',encoding='utf8')as f:json.dump(report,f,ensure_ascii=False,indent=2)
    def execute(self,arguments):
        target=arguments[0]
        for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
            sys.path.insert(0,str(self.package/'skills'/name/'scripts'))
        sys.path.insert(0,str(Path(target).parent));sys.argv=[target,*arguments[1:]]
        builtins.open=self.open;io.open=self.io_open
        def delivered_open_code(name):return NATIVE_OPEN(self.translate(name,'open_code'),'rb')
        _io.open_code=delivered_open_code;io.open_code=delivered_open_code
        os.open=self.os_open;os.stat=self.stat;os.lstat=self.lstat;os.listdir=self.listdir;os.scandir=self.scandir;os.path.realpath=self.realpath
        runtime=self;bootstrap=str(self.adapter_path)
        if NATIVE_ADD_DLL_DIRECTORY is not None:
            os.add_dll_directory=lambda name:NATIVE_ADD_DLL_DIRECTORY(runtime.translate(name,'native DLL directory'))
        original_path_stat=import_backend._path_stat
        def import_path_stat(path):
            previous=getattr(runtime.guard,'import_probe',False);runtime.guard.import_probe=True
            try:return original_path_stat(path)
            finally:runtime.guard.import_probe=previous
        import_backend._path_stat=import_path_stat
        original_get_code=importlib.machinery.SourceFileLoader.get_code
        def delivered_source_code(loader,fullname):
            key=runtime.key(loader.path)
            if key in runtime.files and loader.path.endswith('.py'):
                physical=runtime.checked_file(key)
                with NATIVE_OPEN(physical,'rb')as stream:data=stream.read()
                return loader.source_to_code(data,loader.path)
            return original_get_code(loader,fullname)
        importlib.machinery.SourceFileLoader.get_code=delivered_source_code
        class DeliveredSourceFinder:
            def find_spec(self,fullname,path=None,target=None):
                leaf=fullname.rsplit('.',1)[-1]
                for directory in path if path is not None else sys.path:
                    if not isinstance(directory,str)or runtime.owned(directory):continue
                    for candidate,package in [(os.path.join(directory,leaf,'__init__.py'),True),(os.path.join(directory,leaf+'.py'),False)]:
                        if runtime.key(candidate)in runtime.files or runtime.key(candidate)in runtime.physical_files:
                            return importlib.util.spec_from_file_location(fullname,candidate,
                                loader=importlib.machinery.SourceFileLoader(fullname,candidate),
                                submodule_search_locations=[os.path.dirname(candidate)]if package else None)
                    for suffix in importlib.machinery.EXTENSION_SUFFIXES:
                        candidate=os.path.join(directory,leaf+suffix)
                        if runtime.key(candidate)in runtime.files or runtime.key(candidate)in runtime.physical_files:
                            physical=runtime.translate(candidate,'qualified native extension')
                            return importlib.util.spec_from_file_location(fullname,physical,
                                loader=importlib.machinery.ExtensionFileLoader(fullname,physical))
                return None
        sys.meta_path.insert(0,DeliveredSourceFinder())
        class BoundPopen(NATIVE_POPEN):
            def __init__(self,args,*a,**kwargs):
                if runtime.node_bridge is not None and isinstance(args,(list,tuple))and args and Path(str(args[0])).name.lower()in('node','node.exe'):
                    actual,proof=runtime.node_bridge.locate(runtime,args,kwargs)
                    super().__init__(actual,*a,**kwargs);runtime.qualified_node_calls.append(dict(pid=self.pid,**proof));return
                if not isinstance(args,(list,tuple))or not args or runtime.key(args[0])!=runtime.key(sys.executable):
                    raise PermissionError('Unqualified native subprocess')
                remaining=list(args[1:])
                while remaining:
                    if remaining[:2]in (['-X','utf8'],['-X','utf-8']):remaining=remaining[2:]
                    elif remaining[0]in('-I','-B','-u'):remaining=remaining[1:]
                    else:break
                if not remaining or not remaining[0].endswith('.py'):raise PermissionError('Unqualified Python child shape')
                runtime.translate(remaining[0],'child source')
                actual=[sys.executable,'-I','-X','utf8','-B',bootstrap,str(runtime.package),str(runtime.work),runtime.index_sha256,*remaining]
                super().__init__(actual,*a,**kwargs)
        subprocess.Popen=BoundPopen
        sys.addaudithook(self.audit);atexit.register(self.finish)
        if self.producer_observer is not None:self.producer_observer.install()
        if self.index.get('qualified_node_reader_bridge'):
            binding=self.index['qualified_node_reader_bridge'];path=(self.package/binding['relative']).resolve()
            if not path.is_relative_to(self.package)or digest(path)!=binding['sha256']:raise ValueError('Qualified Node bridge changed')
            spec=importlib.util.spec_from_file_location('delivered_node_read_bridge',path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);self.node_bridge=module;module.install(self)
        self.install_native_fonts()
        self.install_multiprocessing()
        if target=='--multiprocessing-spawn-child':
            descriptor=json.loads(bytes.fromhex(arguments[1]).decode('utf8'));self.spawn_token=descriptor['spawn_token']
            sys.argv=[str(self.adapter_path),'--multiprocessing-fork']
            from multiprocessing.spawn import spawn_main
            spawn_main(**descriptor['kwargs'])
        else:runpy.run_path(target,run_name='__main__')


if __name__=='__main__':
    runtime=Runtime(sys.argv[1],sys.argv[2],sys.argv[3]);runtime.execute(sys.argv[4:])
