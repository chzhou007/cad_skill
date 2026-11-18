"""Explicit read-only view of an already evidenced native main LINE family.

Only the graph's canonical provenance is presented to legacy unique-LINE
geometry readers. Every raw coincident entity remains in the source manifest;
this never resolves physical pipe multiplicity or permits an arbitrary duplicate.
"""
import hashlib
from ezdxf.query import EntityQuery
from confirm_crossview_paths import encode
from native_line_path_evidence import LAYERS,_on
from duplicate_native_main_diagnostics import same_line
from match_source_checked_crossview_paths import native_main_corridor


class _Space:
    def __init__(self,space,excluded):self.space=space;self.excluded=excluded
    def __iter__(self):return (e for e in self.space if e.dxf.handle not in self.excluded)
    def query(self,text):return EntityQuery(list(self)).query(text)


class CanonicalLineDocument:
    def __init__(self,doc,excluded):self.original=doc;self.excluded=frozenset(excluded)
    def __getattr__(self,key):return getattr(self.original,key)
    def modelspace(self):return _Space(self.original.modelspace(),self.excluded)


def project(doc,graph,taps,system,floor,spec,anchor_evidence,source_hash,graph_hash):
    canonical=spec.get('canonical_source_handle');family=spec.get('coincident_source_family',[])
    if (system not in LAYERS or not taps or len(set(taps.values()))!=len(taps) or not isinstance(family,list)
        or not family or len(set(family))!=len(family) or canonical not in family):raise ValueError('explicit unique canonical source family required')
    nodes={n['node_id']:n for n in graph['nodes']};lines=[]
    for handle in family:
        line=doc.entitydb.get(handle)
        if not line or line.dxftype()!='LINE' or line not in doc.modelspace() or line.dxf.layer!=LAYERS[system]:raise ValueError('canonical family native LINE missing or wrong system')
        lines.append(line)
    line=doc.entitydb[canonical]
    if any(not same_line(line,item,.05) for item in lines):raise ValueError('canonical family differs in native XYZ')
    points=[]
    for nid in taps.values():
        node=nodes[nid];entry=anchor_evidence.get(nid,{});proof=entry.get('evidence',{});junctions=proof.get('junctions',[])
        if (node.get('node_type') not in ('tee','physical_junction') or node.get('system',system)!=system or node.get('floor')!=floor
            or proof.get('source_sha256')!=source_hash or proof.get('graph_sha256')!=graph_hash or len(junctions)!=1
            or junctions[0].get('node_id')!=nid or junctions[0].get('system')!=system):raise ValueError('canonical family lacks current native anchor evidence')
        mains=[r for r in junctions[0]['source_rays'] if r['edge_id'] not in entry.get('branch_edges',[])]
        if len(mains)!=2 or any(r.get('source_line_handle')!=canonical or set(r.get('coincident_native_main_handles',[canonical]))!=set(family) for r in mains):
            raise ValueError('canonical graph source owner differs across anchors')
        points.append([node['x'],node['y']])
    covering=[e.dxf.handle for e in doc.modelspace().query('LINE') if e.dxf.layer==LAYERS[system]
        and all(_on(p,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05) for p in points)]
    if set(covering)!=set(family):raise ValueError('unexplained native main covers selected anchors')
    excluded=set(family)-{canonical};view=CanonicalLineDocument(doc,excluded)
    corridor,basis=native_main_corridor(view,graph,taps,system,floor)
    if basis['source_line_handle']!=canonical:raise ValueError('canonical source view changed owner')
    manifest=dict(raw_source_sha256=source_hash,local_graph_sha256=graph_hash,system=system,floor=floor,
        canonical_source_handle=canonical,coincident_source_family=sorted(family),excluded_from_unique_LINE_query=sorted(excluded),
        source_entities=[dict(handle=h,layer=doc.entitydb[h].dxf.layer,XYZ=[list(doc.entitydb[h].dxf.start),list(doc.entitydb[h].dxf.end)]) for h in sorted(family)],
        physical_source_identity_resolved=False,source_entities_deleted=False,local_graph_mutated=False,
        scope='canonical_graph_LINE_provenance_view_not_unique_physical_pipe_identity')
    manifest['projection_sha256']=hashlib.sha256(encode(manifest)).hexdigest()
    return view,corridor,dict(basis,canonical_source_projection=manifest)
