"""Exact-byte copy-on-write backend for the pinned read-only projection kernel.

Only that kernel's selected edge attribute_paths may change. All geometry
readers still run. Canonical JSON prefix/suffix bytes reproduce the original
pretty JSON SHA256 without copying/serializing unrelated graph history per path.
"""
import contextlib,copy,hashlib,json,os,pickle
from collections import OrderedDict

_envelopes=OrderedDict()
_envelope_bytes=0
_envelope_budget=64*1024*1024
_encoded_values=OrderedDict()
_encoded_value_bytes=0
_encoded_value_budget=32*1024*1024

def clear_projection_serializations():
    global _envelope_bytes,_encoded_value_bytes
    _envelopes.clear();_envelope_bytes=0
    _encoded_values.clear();_encoded_value_bytes=0

def _json_values_only(value):
    pending=[value];seen=set()
    while pending:
        item=pending.pop();kind=type(item)
        if kind in (dict,list):
            if id(item)in seen:return False
            seen.add(id(item))
        if kind is dict:
            if any(type(k)is not str for k in item):return False
            pending.extend(item.values())
        elif kind is list:pending.extend(item)
        elif kind not in (str,int,float,bool,type(None)):return False
    return True

def _canonical_envelope(graph,encode):
    """Build exactly the original encoder's bytes and selected-edge spans."""
    chunks=[b'{\n'];size=2;spans={}
    def append(value):
        nonlocal size
        chunks.append(value);size+=len(value)
    def formatted(value,indent):return _formatted_value(value,indent,encode)
    for ki,(key,value)in enumerate(graph.items()):
        if type(key)is not str:raise ValueError('native graph keys must be strings')
        append((b',\n'if ki else b'')+b'  '+json.dumps(key,ensure_ascii=False).encode('utf8')+b': ')
        if key!='edges':append(formatted(value,b'  '));continue
        append(b'[\n')
        for i,edge in enumerate(value):
            append((b',\n'if i else b'')+b'    ');start=size
            append(formatted(edge,b'    '));spans[edge['edge_id']]=(start,size,i)
        append(b'\n  ]')
    append(b'\n}\n');raw=b''.join(chunks)
    return raw,spans

def _formatted_value(value,indent,encode):
    """Tokenize and reuse unchanged subtrees when one reconstructed edge changes."""
    global _encoded_value_bytes
    token=(id(encode),indent,hashlib.sha256(pickle.dumps(value,protocol=5)).digest())
    if token in _encoded_values:
        _encoded_values.move_to_end(token);return _encoded_values[token][0]
    if not _json_values_only(value):raise ValueError('unsupported graph value')
    raw=encode(value)[:-1].replace(b'\n',b'\n'+indent)
    if len(raw)<=_encoded_value_budget:
        while _encoded_values and _encoded_value_bytes+len(raw)>_encoded_value_budget:
            _,old=_encoded_values.popitem(last=False);_encoded_value_bytes-=len(old[0])
        _encoded_values[token]=(raw,encode);_encoded_value_bytes+=len(raw)
    return raw

def serialization_fragments(graph,eid,encode):
    """Reuse serialization, never a geometry result or a verifier pass.

    A fresh protocol-5 token checks every graph value, key order and shared
    structure on every call. Consumer mutations invalidate it. Only builtin
    JSON values qualify, and the first layout is checked against the unchanged
    original encoder. The job/worker-local byte budget is bounded.
    """
    global _envelope_bytes
    if os.environ.get('CAD_NATIVE_SERIALIZATION_REUSE','1')=='0':return fragments(graph,eid,encode)
    try:key=(id(encode),hashlib.sha256(pickle.dumps(graph,protocol=5)).digest())
    except (pickle.PickleError,TypeError,AttributeError,RecursionError):return fragments(graph,eid,encode)
    if key not in _envelopes:
        if type(graph)is not dict or type(graph.get('edges'))is not list:return fragments(graph,eid,encode)
        try:raw,spans=_canonical_envelope(graph,encode)
        except ValueError:return fragments(graph,eid,encode)
        if len(raw)>_envelope_budget:return fragments(graph,eid,encode)
        while _envelopes and _envelope_bytes+len(raw)>_envelope_budget:
            _,old=_envelopes.popitem(last=False);_envelope_bytes-=len(old[0])
        _envelopes[key]=(raw,spans,encode);_envelope_bytes+=len(raw)
    else:_envelopes.move_to_end(key)
    raw,spans,_=_envelopes[key];start,end,index=spans[eid]
    return memoryview(raw)[:start],memoryview(raw)[end:],index

def fragments(graph,eid,encode):
    if any(type(k)is not str for k in graph):raise ValueError('native graph keys must be strings')
    edges=graph['edges'];positions=[i for i,e in enumerate(edges)if e['edge_id']==eid]
    if len(positions)!=1:raise ValueError('unique selected edge required')
    index=positions[0]
    def formatted(value,indent):return encode(value)[:-1].replace(b'\n',b'\n'+indent)
    before=[b'{\n'];after=[];selected=False
    for ki,(key,value)in enumerate(graph.items()):
        start=(b',\n'if ki else b'')+b'  '+json.dumps(key,ensure_ascii=False).encode('utf8')+b': '
        if key!='edges':(after if selected else before).append(start+formatted(value,b'  '));continue
        before.append(start+b'[\n')
        for i,edge in enumerate(edges):
            prefix=(b',\n'if i else b'')+b'    '
            if i<index:before.append(prefix+formatted(edge,b'    '))
            elif i==index:before.append(prefix);selected=True
            else:after.append(prefix+formatted(edge,b'    '))
        after.append(b'\n  ]')
    after.append(b'\n}\n')
    return b''.join(before),b''.join(after),index

@contextlib.contextmanager
def projection_values(module,graph,eid):
    previous_copy=copy.deepcopy;previous_hash=module.value_sha;created={};parts=None
    positions=[i for i,e in enumerate(graph['edges'])if e['edge_id']==eid]
    if len(positions)!=1:
        yield;return
    index=positions[0]
    def deepcopy(value,memo=None,*args,**kwargs):
        if value is graph and memo is None and not args and not kwargs:
            result=dict(graph);result['edges']=list(graph['edges']);result['edges'][index]=dict(graph['edges'][index]);created[id(result)]=result;return result
        return previous_copy(value,memo,*args,**kwargs)
    def value_sha(value):
        nonlocal parts
        if id(value)not in created:return previous_hash(value)
        source=graph['edges'][index];target=value['edges'][index]
        same=(list(value)==list(graph)and len(value['edges'])==len(graph['edges'])and list(target)==list(source)
            and all(value[k]is graph[k]for k in graph if k!='edges')
            and all(e is graph['edges'][i]for i,e in enumerate(value['edges'])if i!=index)
            and all(target[k]is source[k]for k in source if k!='attribute_paths')
            and len(target['attribute_paths'])==1 and target['attribute_paths'][0]in source['attribute_paths'])
        if not same:return previous_hash(value)
        if parts is None:parts=serialization_fragments(graph,eid,module.encode)
        prefix,suffix,_=parts;middle=module.encode(target)[:-1].replace(b'\n',b'\n    ')
        digest=hashlib.sha256();digest.update(prefix);digest.update(middle);digest.update(suffix);return digest.hexdigest()
    copy.deepcopy=deepcopy;module.value_sha=value_sha
    try:yield
    finally:copy.deepcopy=previous_copy;module.value_sha=previous_hash

def projected(module,doc,graph,eid,sh,original=None):
    original=original or module.projected_coverage
    with projection_values(module,graph,eid):return original(doc,graph,eid,sh)
