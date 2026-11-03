"""Read declared DXF proxy class/block identity without decoding binary payloads."""
import hashlib,json,math

def proxy_identity(doc, entity):
    if entity.dxftype()!='ACAD_PROXY_ENTITY':raise ValueError('Not a proxy entity')
    tags=entity.acdb_proxy_entity
    ids=[t.value for t in tags if t.code==91]
    if len(ids)!=1:raise ValueError('Missing or ambiguous proxy class ID')
    classes=list(doc.classes);index=int(ids[0])-500
    if not 0<=index<len(classes):raise ValueError('Undeclared custom proxy class')
    cls=classes[index];blocks=[]
    for tag in tags:
        if tag.code!=340:continue
        obj=doc.entitydb.get(tag.value)
        if obj is not None and obj.dxftype()=='BLOCK_RECORD':blocks.append({'handle':obj.dxf.handle,'name':obj.dxf.name})
    return {'proxy_handle':entity.dxf.handle,'class_id':ids[0],
            'class_name':cls.dxf.name,'cpp_class_name':cls.dxf.cpp_class_name,
            'block_records':blocks,'method':'declared DXF CLASS index and typed object pointers; binary payload not decoded'}

def block_fingerprint(block):
    # Geometry and per-primitive layer are compared, not importer-dependent handles.
    from ezdxf.lldxf.tagwriter import TagCollector
    def value(v):
        if isinstance(v,(int,float)):return round(float(v),5)
        if isinstance(v,(list,tuple))or hasattr(v,'x'):return [value(x)for x in v]
        return v
    rows=[]
    for e in block:
        col=TagCollector(dxfversion='AC1032');e.export_dxf(col)
        rows.append([[t.code,value(t.value)]for t in col.tags if t.code!=5 and not 330<=t.code<=369 and t.code!=1005])
    encoded=json.dumps(sorted(rows,key=lambda x:json.dumps(x)),ensure_ascii=False,separators=(',',':')).encode('utf8')
    return hashlib.sha256(encoded).hexdigest()

def inside_segment_bounds(a,b,box):
    lo,hi=0.,1.
    for i in (0,1):
        delta=b[i]-a[i]
        if abs(delta)<1e-12:
            if a[i]<box[i]or a[i]>box[i+2]:return False
        else:
            t0,t1=(box[i]-a[i])/delta,(box[i+2]-a[i])/delta
            lo=max(lo,min(t0,t1));hi=min(hi,max(t0,t1))
            if lo>hi:return False
    return True

def native_inline_candidates(edges,bounds,port_axis):
    norm=math.hypot(*port_axis)
    if norm<=0:raise ValueError('Native port axis required')
    found=[]
    for edge in edges:
        for a,b in zip(edge['path_points'],edge['path_points'][1:]):
            v=(b[0]-a[0],b[1]-a[1]);length=math.hypot(*v)
            if length and abs(v[0]*port_axis[0]+v[1]*port_axis[1])/(length*norm)>=.999 and inside_segment_bounds(a,b,bounds):
                found.append(edge['edge_id']);break
    return sorted(set(found))
