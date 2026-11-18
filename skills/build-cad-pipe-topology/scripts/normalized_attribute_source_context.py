"""Reuse original applied junction normalization in a private DN reader view.

The raw route/source and physical length coverage remain unchanged. Only an
exact applied, source-replayed normalized T ray receives the old reader schema
in this private context; its original raw gap and source XYZ remain explicit.
"""
import copy,math
from confirm_crossview_paths import encode
from axis_unbranched_vertical_DN import source_key
from native_line_path_evidence import LAYERS
import normalized_native_junction_evidence as original

MODE='original_normalization_private_attribute_source_context_v1'
def require(value,message):
    if not value:raise ValueError(message)

class AttributeSource(original._ProjectedSource):
    def __getattr__(self,name):return getattr(self.original,name)
    def __iter__(self):
        return iter(self.replacements.get(e.dxf.handle,e)for e in self.original.modelspace())

def prepare(doc,graph,route,items,source_hash,graph_hash,audit_spec,node_id,edge_id):
    require(graph['metadata']['source_sha256']==source_hash and route['inputs']['source']['sha256']==source_hash
        and route['inputs']['graph']['sha256']==graph_hash,'current raw source graph and route bindings required')
    before=encode(graph),encode(route),encode(items)
    normalization=original.prepare(doc,graph,source_hash,graph_hash,audit_spec)
    tee=original.collect(doc,graph,node_id,source_hash,graph_hash,normalization)
    rays=[r for r in tee['junctions'][0]['source_rays']if r['edge_id']==edge_id and r.get('scope')=='normalized_modelspace_line']
    require(len(rays)==1,'one original normalization-replayed target ray required');ray=rays[0]
    require(ray['normalization']['status']=='applied'and ray['normalization']['action']=='extend'
        and ray['normalization']['physical_length']=='unknown'and ray['source_gap_is_measured']is False
        and ray['physical_gap_length']is None,'only original applied semantic extension may enter the DN reader')
    h=ray['source_line_handle'];line=doc.entitydb.get(h)
    require(line is not None and line.dxftype()=='LINE'and line in doc.modelspace(),'original modelspace LINE required')
    selected=[s for s in route['records']if s['edge_id']==edge_id and
        (s['scope_points']==ray['graph_segment']or s['scope_points']==list(reversed(ray['graph_segment'])))]
    require(len(selected)==1,'normalized ray has no unique original source domain');target=selected[0]
    require(target['native_source_status']=='no_witness_in_scoped_search'and not target['native_witnesses'],
            'raw ambiguous or already owned source domain cannot be overwritten')
    require(line.dxf.layer==LAYERS[target['system']],'normalized attribute source system changed')
    raw_xyz=[list(line.dxf.start),list(line.dxf.end)];replacement=line.copy();replacement.dxf.handle=h
    a,b=ray['normalized_segment'];z=line.dxf.start.z;replacement.dxf.start=(*a,z);replacement.dxf.end=(*b,z)
    private_items=copy.deepcopy(items);hits=[s for s in private_items if s['root_handle']is None and s['child_handle']==h and s['layer']==line.dxf.layer]
    require(len(hits)==1 and hits[0]['XYZ']==raw_xyz,'attribute normalization must compose with one unchanged original source item')
    hits[0].update(XYZ=[list(replacement.dxf.start),list(replacement.dxf.end)],raw_native_XYZ=raw_xyz,
        semantic_normalization_evidence=copy.deepcopy(ray),coordinate_role='semantic_source_connectivity_not_raw_LINE_coverage')
    private_route=copy.deepcopy(route);private_target=next(s for s in private_route['records']if source_key(s)==source_key(target))
    private_target.update(native_source_status='single_source_line_covers',raw_native_source_status=target['native_source_status'],
        native_witnesses=[dict(scope='modelspace',source_handle=h,layer=line.dxf.layer,
            start=list(replacement.dxf.start)[:2],end=list(replacement.dxf.end)[:2],
            coordinate_role='private_original_reader_schema_for_replayed_normalization',raw_native_XYZ=raw_xyz,
            semantic_normalization_evidence=copy.deepcopy(ray))],
        private_reader_schema_only=True,raw_source_coverage_not_promoted=True)
    source=AttributeSource(doc,{h:replacement});normalization.check(doc,graph,source_hash,graph_hash)
    require(before==(encode(graph),encode(route),encode(items)),'raw graph, route or source items mutated')
    evidence=dict(mode=MODE,source_hash=source_hash,graph_hash=graph_hash,node_id=node_id,edge_id=edge_id,
        source_domain=list(source_key(target)),original_raw_scope=copy.deepcopy(target),original_native_LINE_XYZ=raw_xyz,
        original_T_evidence=tee,original_normalization_ray=copy.deepcopy(ray),
        raw_source_coverage_unchanged=True,raw_source_graph_route_items_unchanged=True,
        private_schema_not_raw_LINE_evidence=True,physical_gap_length_mm=None,physical_lengths_assigned=0,
        source_texts_changed=False,human_accepted=False)
    return source,private_route,private_items,evidence
