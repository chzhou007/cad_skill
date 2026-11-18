"""Recover omitted known-family valves through native ports, not INSERT origins.

The existing six-line recognizer owns the signature. This adapter only binds
its flange ports to a unique source pipe and a unique current graph segment.
It preserves the prior inventory and emits unresolved native instances too.
"""
import copy,math
from collections import Counter
from native_inline_coordinates import balancing_valve_anchor
from native_line_path_evidence import LAYERS,_on

MODE='native_balancing_valve_inventory_recovery_v1'

def ports(insert,tol=.05):
    anchor=balancing_valve_anchor(insert)
    if anchor is None:return None
    parts=list(insert.virtual_entities())
    lines=sorted([(list(e.dxf.start),list(e.dxf.end))for e in parts],key=lambda ab:math.dist(*ab),reverse=True)
    z=[p[2]for ab in lines for p in ab]
    if max(z)-min(z)>tol:return None
    corners=lines[0]+lines[1]
    length=math.dist(*lines[0]);eps=max(length*1e-6,1e-7)
    flange=[ab for ab in lines[2:]if all(any(math.dist(p,q)<=eps for q in corners)for p in ab)]
    if len(flange)!=2:return None
    return dict(anchor,ports_WCS=[[(ab[0][i]+ab[1][i])/2 for i in range(3)]for ab in flange],center_WCS=anchor['center']+[sum(z)/len(z)])

def recover(doc,graph,components,tol=.05):
    if not math.isfinite(tol)or tol<=0:raise ValueError('positive finite source tolerance required')
    edge_ids=[e['edge_id']for e in graph['edges']]
    if len(set(edge_ids))!=len(edge_ids):raise ValueError('duplicate graph edge IDs')
    old=copy.deepcopy(components);claims=Counter(r.get('source_top_handle')for r in old if r.get('source_top_handle'))
    pipes=[e for e in doc.modelspace().query('LINE')if e.dxf.layer in LAYERS.values()]
    systems={v:k for k,v in LAYERS.items()};records=[];added=[]
    for insert in doc.modelspace().query('INSERT'):
        if insert.dxf.name!='平衡阀':continue
        handle=insert.dxf.handle;geometry=ports(insert,tol)
        row=dict(source_handle=handle,source_block_name=insert.dxf.name,source_layer=insert.dxf.layer,raw_INSERT_origin=list(insert.dxf.insert),geometry=geometry,native_pipe_candidates=[],graph_candidates=[],assigned_edge_id=None)
        if claims[handle]:
            row['status']='already_in_inventory'if claims[handle]==1 else'conflicting_prior_component_claims';records.append(row);continue
        if geometry is None:row['status']='unsupported_native_family_geometry';records.append(row);continue
        def covered(points,a,b):
            return all(_on(p[:2],a[:2],b[:2],tol)and abs(p[2]-(a[2]+((p[0]-a[0])*(b[0]-a[0])+(p[1]-a[1])*(b[1]-a[1]))/sum((b[i]-a[i])**2 for i in (0,1))*(b[2]-a[2])))<=tol for p in points)
        points=[geometry['center_WCS']]+geometry['ports_WCS']
        for line in pipes:
            a,b=list(line.dxf.start),list(line.dxf.end)
            if math.dist(a[:2],b[:2])<=tol:continue
            if covered(points,a,b):row['native_pipe_candidates'].append(dict(source_LINE=line.dxf.handle,system=systems[line.dxf.layer],start=a,end=b,layer=line.dxf.layer))
        if len(row['native_pipe_candidates'])!=1:
            row['status']='no_unique_native_pipe';records.append(row);continue
        native=row['native_pipe_candidates'][0]
        for edge in graph['edges']:
            if edge.get('system')!=native['system']or edge.get('connection_mode')!='continuous_original_cad_pipe':continue
            for pi,path in enumerate(edge.get('attribute_paths',[])):
                for si,(a,b)in enumerate(zip(path,path[1:])):
                    if math.dist(a[:2],b[:2])<=tol:continue
                    if not all(_on(p[:2],a[:2],b[:2],tol)for p in points):continue
                    if not all(_on(p[:2],native['start'][:2],native['end'][:2],tol)for p in(a,b)):continue
                    handles=edge.get('source_handles')
                    if handles is not None and native['source_LINE']not in handles:continue
                    row['graph_candidates'].append(dict(edge_id=edge['edge_id'],path_index=pi,segment_index=si,points=[a,b]))
        if len(row['graph_candidates'])!=1:
            row['status']='no_unique_graph_segment';records.append(row);continue
        eid=row['graph_candidates'][0]['edge_id'];name='平衡阀-NATIVE-'+handle
        if any(c.get('device_name')==name for c in old+added):raise ValueError('recovered component identity collision')
        row.update(status='recovered_unique_native_ports_and_graph_segment',assigned_edge_id=eid,system=native['system'],device_name=name,source_layer_differs_from_pipe=insert.dxf.layer!=native['layer'])
        # Use the existing plan inventory type so the unchanged cross-view
        # component-profile owner can compare the two drawing families.
        added.append(dict(device_name=name,equipment_type='balancing_valve',type_code='BAL',x=str(geometry['center'][0]),y=str(geometry['center'][1]),assignment_x=str(geometry['center'][0]),assignment_y=str(geometry['center'][1]),source_kind='block_insert',source_block_name=insert.dxf.name,source_top_handle=handle,owner_equipment='',system_hint=native['system'],edge_id=eid,edge_distance='0',assignment_status='assigned',original_edge_id='',assignment_basis=MODE,original_device_name='',original_owner_equipment=''))
        records.append(row)
    return dict(mode=MODE,records=records,added_components=added,components=old+added,counts=dict(native_population=len(records),prior_components=len(old),added_components=len(added),output_components=len(old)+len(added),statuses=dict(Counter(r['status']for r in records))),prior_components_unchanged=True,source_graph_unchanged=True,resistance_parameters_assigned=0,human_accepted=False)
