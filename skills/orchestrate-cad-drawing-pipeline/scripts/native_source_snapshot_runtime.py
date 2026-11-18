"""Job-local DXF parse snapshots; each read gets a fresh independent Drawing.

Only the unchanged strict native-text reader qualifies. It still runs for every
call, including its Chinese scan. Snapshots are generated internally from this
job's original parser, never loaded from disk or historical pass flags.
"""
import contextlib
import gc
import hashlib
import inspect
import os
import pickle
from collections import OrderedDict
from pathlib import Path

READER_SHA256='50127d89bb56c433bf86bbfa30db77a2507d8e3d3d9e26638482eb39a26b369a'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

@contextlib.contextmanager
def native_allocation_window():
    """Avoid rescanning live DXF cycles during a bounded parser/clone operation.

    Refcounting stays active. Restore the caller's collector state, including on
    failure; normal collection resumes outside this allocation window. No GC
    thresholds, source readers or entity states are changed.
    """
    enabled=gc.isenabled()
    pause=enabled and os.environ.get('CAD_NATIVE_ALLOCATION_GC','1')!='0'
    if pause:gc.disable()
    try:yield
    finally:
        if enabled and not gc.isenabled():gc.enable()
        elif not enabled and gc.isenabled():gc.disable()

@contextlib.contextmanager
def source_snapshot_runtime(max_bytes=512*1024*1024):
    import ezdxf
    original=ezdxf.readfile;cache=OrderedDict();size=0
    stats=dict(original_parses=0,fresh_snapshot_clones=0,unsupported_fallbacks=0,
               invalidations=0,peak_snapshot_bytes=0,persisted_snapshots_used=False)
    def readfile(filename,*args,**kwargs):
        nonlocal size
        caller=inspect.currentframe().f_back
        reader=Path(caller.f_code.co_filename)
        qualified=(caller.f_code.co_name=='read_source' and reader.name=='source_readability.py'
                   and not args and kwargs=={'errors':'strict'}
                   and reader.is_file() and digest(reader)==READER_SHA256)
        if not qualified:
            stats['unsupported_fallbacks']+=1
            return original(filename,*args,**kwargs)
        path=Path(filename).resolve();sh=digest(path);key=(str(path),sh)
        # Changed bytes cannot reuse a previous parse, even at the same path.
        for old in list(cache):
            if old[0]==str(path) and old!=key:
                size-=len(cache.pop(old));stats['invalidations']+=1
        if key in cache:
            payload=cache[key];cache.move_to_end(key)
            with native_allocation_window():result=pickle.loads(payload)
            if digest(path)!=sh:raise RuntimeError('native source changed while cloning parsed snapshot')
            stats['fresh_snapshot_clones']+=1
            return result
        with native_allocation_window():result=original(filename,*args,**kwargs)
        stats['original_parses']+=1
        if digest(path)!=sh:raise RuntimeError('native source changed while parsing')
        try:
            with native_allocation_window():payload=pickle.dumps(result,protocol=5)
        except (pickle.PickleError,TypeError,AttributeError,RecursionError):
            stats['unsupported_fallbacks']+=1
            return result
        if len(payload)<=max_bytes:
            while cache and size+len(payload)>max_bytes:
                _,removed=cache.popitem(last=False);size-=len(removed)
            cache[key]=payload;size+=len(payload)
            stats['peak_snapshot_bytes']=max(stats['peak_snapshot_bytes'],size)
        return result
    if os.environ.get('CAD_NATIVE_SOURCE_SNAPSHOTS','1')=='0':
        yield stats
        return
    ezdxf.readfile=readfile
    try:yield stats
    finally:
        ezdxf.readfile=original
        cache.clear()
