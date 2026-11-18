"""Opt-in C-backed clone for plain native JSON graph values, not arbitrary objects.

Original CAD readers and evidence hashes still execute. Explicit memo callers,
non-graph roots and custom objects retain standard deepcopy behavior. Mutable
containers, aliases and cycles are preserved. Immutable scalar object identity
across the original and clone is outside this JSON graph value contract.
"""
import contextlib, copy, io, pickle, threading

class UnsupportedGraphType(TypeError):pass

class NativeGraphPickler(pickle.Pickler):
    def reducer_override(self,obj):
        # Exact builtin data containers/scalars use the C pickler fast path.
        # Every custom reducer is rejected before executing user code.
        raise UnsupportedGraphType(type(obj).__name__)

def clone_graph(value):
    stream=io.BytesIO();NativeGraphPickler(stream,protocol=5).dump(value)
    return pickle.loads(stream.getbuffer())

@contextlib.contextmanager
def accelerated_graph_copy():
    if threading.active_count()!=1:raise RuntimeError('native graph copy context requires an isolated single-thread worker')
    original=copy.deepcopy;stats=dict(graph_copies=0,fallbacks=0)
    def deepcopy(value,memo=None,*args,**kwargs):
        if memo is None and not args and not kwargs and type(value)is dict and type(value.get('nodes'))is list and type(value.get('edges'))is list:
            try:result=clone_graph(value)
            except (UnsupportedGraphType,pickle.PickleError,TypeError,ValueError,RecursionError):stats['fallbacks']+=1
            else:stats['graph_copies']+=1;return result
        return original(value,memo,*args,**kwargs)
    copy.deepcopy=deepcopy
    try:yield stats
    finally:copy.deepcopy=original
