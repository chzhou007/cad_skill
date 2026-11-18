"""Prove native LEADER components do not reach one declared DN scope.

This is a read-only catalog adapter, not a leader interpretation or deletion.
Every same-layer straight annotation stroke participates in connectivity. A
leader with an annotation reference, unsupported geometry or contact with the
scope remains unsupported by the inherited catalog.
"""
import math,re
from pipe_annotation_attributes import contact,source_texts
from native_equipment_body import point_segment_distance


def touches(a,b,c,d):
    return contact(a,b,c,d) is not None or min(point_segment_distance(a,c,d),point_segment_distance(b,c,d),
        point_segment_distance(c,a,b),point_segment_distance(d,a,b))<=.05


def collect(doc,paths,source_hash):
    scope=[(a,b) for p in paths for a,b in zip(p,p[1:])]
    if not source_hash or not scope or any(len(p)!=2 or not all(math.isfinite(x) for x in p) for s in scope for p in s):
        raise ValueError('invalid annotation isolation scope')
    leaders=list(doc.modelspace().query('LEADER'));layers={e.dxf.layer for e in leaders};strokes=[]
    for e in doc.modelspace():
        if e.dxf.layer not in layers:continue
        kind=e.dxftype()
        if kind in ('LINE','LEADER','LWPOLYLINE'):
            if kind=='LINE':points=[list(e.dxf.start),list(e.dxf.end)]
            elif kind=='LEADER':
                if e.dxf.get('annotation_handle') not in (None,'0'):raise ValueError('leader annotation reference requires interpretation')
                points=[list(p) for p in e.vertices]
            else:
                if any(abs(p[4])>1e-9 for p in e.get_points()):raise ValueError('curved annotation component requires interpretation')
                points=[list(p) for p in e.vertices_in_wcs()]
                if e.closed and points:points.append(points[0])
            if len(points)<2 or any(len(p)!=3 or not all(math.isfinite(x) for x in p) for p in points):raise ValueError('invalid native annotation geometry')
            for a,b in zip(points,points[1:]):
                if math.dist(a[:2],b[:2])<=.05:raise ValueError('degenerate annotation geometry')
                strokes.append(dict(handle=e.dxf.handle,type=kind,layer=e.dxf.layer,XYZ=[a,b]))
        elif kind in ('INSERT','ARC','CIRCLE','ELLIPSE','SPLINE','POLYLINE','MLINE','MLEADER','MULTILEADER','ACAD_PROXY_ENTITY'):
            raise ValueError('unsupported geometry on native LEADER layer '+kind)
    texts=[t for t in source_texts(doc,'source',source_hash) if re.search(r'DN',t['text'],re.I)]
    remaining=set(range(len(strokes)));components=[]
    while remaining:
        group={min(remaining)};remaining-=group;queue=list(group)
        while queue:
            i=queue.pop();a,b=[p[:2] for p in strokes[i]['XYZ']]
            linked={j for j in remaining if strokes[j]['layer']==strokes[i]['layer'] and touches(a,b,*[p[:2] for p in strokes[j]['XYZ']])}
            remaining-=linked;group|=linked;queue.extend(sorted(linked))
        if not any(strokes[i]['type']=='LEADER' for i in group):continue
        segments=[[p[:2] for p in strokes[i]['XYZ']] for i in sorted(group)]
        if any(touches(a,b,c,d) for a,b in segments for c,d in scope):raise ValueError('native LEADER component reaches DN scope')
        for text in texts:
            near_component=any(point_segment_distance(text['position'],a,b)<=3*text['height'] for a,b in segments)
            near_scope=any(point_segment_distance(text['position'],a,b)<=3*text['height'] for a,b in scope)
            if near_component and near_scope:raise ValueError('native LEADER and nearby DN can affect scope')
        components.append(dict(strokes=[strokes[i] for i in sorted(group)],
            leader_handles=sorted({strokes[i]['handle'] for i in group if strokes[i]['type']=='LEADER'}),
            role='native_annotation_component_does_not_reach_declared_DN_scope'))
    handles=sorted(h for c in components for h in c['leader_handles'])
    if handles!=sorted(e.dxf.handle for e in leaders):raise ValueError('not every native LEADER was classified')
    return dict(status='native_LEADER_components_geometrically_isolated_from_declared_DN_scope',source_sha256=source_hash,
        scope_paths=paths,components=components,isolated_leader_handles=handles,source_mutated=False,
        leader_meaning_interpreted=False,physical_values_assigned=0,human_accepted=False)


class CatalogDocument:
    """Hide only proved out-of-scope LEADERs from catalog's unsupported loop.

    Native queries, entitydb and all other document behaviour remain unchanged.
    In particular the shared source is never modified or globally monkeypatched.
    """
    def __init__(self,doc,evidence):
        self._doc=doc;self._hidden=set(evidence['isolated_leader_handles'])
    def __getattr__(self,key):return getattr(self._doc,key)
    def modelspace(self):
        original=self._doc.modelspace();hidden=self._hidden
        class CatalogSpace:
            def __iter__(self):return (e for e in original if not (e.dxftype()=='LEADER' and e.dxf.handle in hidden))
            def __getattr__(self,key):return getattr(original,key)
        return CatalogSpace()
