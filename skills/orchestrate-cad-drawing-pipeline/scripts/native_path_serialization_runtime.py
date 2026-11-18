"""Reuse exact JSON subtrees in the inherited batch path projection entry.

Every value and key order is freshly tokenized. No geometry witness, accepted
result or file hash is cached. Unsupported graph shapes keep the original JSON
encoder; original source-reader modules and their receipts remain unchanged.
"""
import contextlib,importlib.abc,importlib.machinery,os,sys
from pathlib import Path
from native_projection_value_runtime_v1 import _canonical_envelope,clear_projection_serializations


class Runtime:
    def __init__(self,root):
        from hashlib import sha256
        self.root=Path(root);self.sha=lambda p:sha256(Path(p).read_bytes()).hexdigest()
        self.reader=self.sha(self.root/'build-cad-pipe-topology/scripts/batch_native_path_coverage.py')
        self.encoder=self.sha(self.root/'build-cad-pipe-topology/scripts/confirm_crossview_paths.py')
        self.patched=[];self.stats=dict(exact_graph_encodings=0,original_fallbacks=0)

    def attach(self,module):
        original=getattr(module,'encode',None);path=getattr(module,'__file__',None)
        if not path or self.sha(path)!=self.reader or not callable(original):return
        code=getattr(original,'__code__',None)
        if code is None or Path(code.co_filename).name!='confirm_crossview_paths.py':return
        if self.sha(code.co_filename)!=self.encoder:return
        if getattr(original,'_native_path_serialization',False):return
        def encode(value):
            try:
                if (type(value)is not dict or type(value.get('edges'))is not list or not value['edges']
                    or any(type(e)is not dict or type(e.get('edge_id'))is not str for e in value['edges'])
                    or len({e['edge_id']for e in value['edges']})!=len(value['edges'])):
                    raise ValueError('unsupported graph envelope')
                raw,_=_canonical_envelope(value,original)
                self.stats['exact_graph_encodings']+=1
                return raw
            except (ValueError,TypeError,KeyError,RecursionError,OverflowError):
                self.stats['original_fallbacks']+=1
                return original(value)
        encode._native_path_serialization=True;module.encode=encode;self.patched.append((module,original,encode))

    def close(self):
        for module,original,wrapper in reversed(self.patched):
            if module.encode is wrapper:module.encode=original
        clear_projection_serializations()


class Finder(importlib.abc.MetaPathFinder):
    def __init__(self,runtime):self.runtime=runtime
    def find_spec(self,fullname,path=None,target=None):
        if fullname!='batch_native_path_coverage':return None
        spec=importlib.machinery.PathFinder.find_spec(fullname,path,target)
        if spec is None:return None
        original=spec.loader;runtime=self.runtime
        class Loader(importlib.abc.Loader):
            def create_module(self,spec):return original.create_module(spec)if hasattr(original,'create_module')else None
            def exec_module(self,module):original.exec_module(module);runtime.attach(module)
        spec.loader=Loader();return spec


@contextlib.contextmanager
def path_serialization_runtime(root):
    if (os.environ.get('CAD_NATIVE_PATH_SERIALIZATION','1')=='0'
        or os.environ.get('CAD_NATIVE_SERIALIZATION_REUSE','1')=='0'):yield {};return
    runtime=Runtime(root);finder=Finder(runtime);sys.meta_path.insert(0,finder)
    try:
        module=sys.modules.get('batch_native_path_coverage')
        if module is not None:runtime.attach(module)
        yield runtime.stats
    finally:
        sys.meta_path.remove(finder);runtime.close()
