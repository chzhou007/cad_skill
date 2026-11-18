"""Reapply existing ball-valve signatures and actual WCS flange contacts.

Equipment membership remains descriptive. It cannot override a uniquely
witnessed physical pipe owner. Component identities and counts are conserved.
"""
import copy
import math
from collections import Counter
from itertools import combinations
from native_inline_coordinates import ball_valve_anchor
from native_flange_contact_ownership import flange_contacts
from native_line_path_evidence import LAYERS, _on

MODE='native_ball_valve_contact_owner_reapplication_v1'

def footprint(insert,tol=.05):
    if insert.dxf.name!='H-PICPNT-91':return None
    anchor=ball_valve_anchor(insert)
    if anchor is None:return None
    parts=list(insert.virtual_entities());lines=[(list(e.dxf.start),list(e.dxf.end))for e in parts if e.dxftype()=='LINE']
    circle=next(e for e in parts if e.dxftype()=='LWPOLYLINE');world=list(circle.vertices_in_wcs())
    z=[point[2]for pair in lines for point in pair]+[point[2]for point in world]
    if not all(math.isfinite(value)for pair in lines for point in pair for value in point)or max(z)-min(z)>tol:return None
    options=[]
    for first,second in combinations(lines,2):
        a=[first[1][i]-first[0][i]for i in range(2)];b=[second[1][i]-second[0][i]for i in range(2)]
        if abs(a[0]*b[1]-a[1]*b[0])>1e-6*max(math.dist(*first)*math.dist(*second),1):continue
        p=[(first[0][i]+first[1][i])/2 for i in range(3)];q=[(second[0][i]+second[1][i])/2 for i in range(3)]
        if math.dist(p,q)<=tol:continue
        axis=[q[i]-p[i]for i in range(2)];fraction=sum((anchor['center'][i]-p[i])*axis[i]for i in range(2))/sum(value*value for value in axis)
        if not 0<fraction<1:continue
        geometry=dict(anchor,ports_WCS=[p,q],flanges_WCS=[first,second],center_WCS=anchor['center']+[sum(z)/len(z)])
        centre=geometry['center_WCS'];a=[centre[i]-2*(q[i]-p[i])for i in range(3)];b=[centre[i]+2*(q[i]-p[i])for i in range(3)]
        if flange_contacts(geometry,a,b,tol)is not None:options.append(geometry)
    return options[0]if len(options)==1 else None

def source_owners(geometry,pipes,graph,tol=.05):
    native=[];systems={value:key for key,value in LAYERS.items()}
    for line in pipes:
        if line.dxftype()!='LINE'or line.dxf.layer not in systems:continue
        start,end=list(line.dxf.start),list(line.dxf.end);contacts=flange_contacts(geometry,start,end,tol)
        if contacts is not None:native.append(dict(source_LINE=line.dxf.handle,system=systems[line.dxf.layer],start=start,end=end,flange_contacts=contacts))
    owners=[]
    if len(native)==1:
        line=native[0];points=[contact['point_WCS']for contact in line['flange_contacts']]
        for edge in graph['edges']:
            if edge['system']!=line['system']or edge.get('connection_mode')!='continuous_original_cad_pipe':continue
            if edge.get('source_handles')is not None and line['source_LINE']not in edge['source_handles']:continue
            for pi,path in enumerate(edge.get('attribute_paths',[])):
                for si,(a,b)in enumerate(zip(path,path[1:])):
                    if math.dist(a[:2],b[:2])>tol and all(_on(point[:2],a[:2],b[:2],tol)for point in points)and all(_on(point[:2],line['start'][:2],line['end'][:2],tol)for point in(a,b)):owners.append(dict(edge_id=edge['edge_id'],path_index=pi,segment_index=si))
    return native,owners

def reapply(doc,graph,components,tol=.05):
    if not math.isfinite(tol)or tol<=0:raise ValueError('positive finite contact tolerance required')
    edges={edge['edge_id']:edge for edge in graph['edges']}
    if len(edges)!=len(graph['edges']):raise ValueError('duplicate native graph edge IDs')
    original=copy.deepcopy(components);output=copy.deepcopy(components);claims={}
    for index,row in enumerate(original):
        if row.get('source_top_handle'):claims.setdefault(row['source_top_handle'],[]).append(index)
    pipes=list(doc.modelspace().query('LINE'));records=[];changes=[];population=0
    for insert in doc.modelspace().query('INSERT'):
        if insert.dxf.name!='H-PICPNT-91':continue
        population+=1;handle=insert.dxf.handle;geometry=footprint(insert,tol)
        row=dict(source_handle=handle,geometry=geometry,prior_claim_indices=claims.get(handle,[]),native_candidates=[],graph_candidates=[])
        if geometry is None:records.append(dict(row,status='unsupported_native_signature_or_flange_footprint'));continue
        native,owners=source_owners(geometry,pipes,graph,tol);row.update(native_candidates=native,graph_candidates=owners)
        status='no_unique_native_contact'if len(native)!=1 else'no_unique_graph_owner'if len(owners)!=1 else'unclaimed_source_instance'if not row['prior_claim_indices']else'conflicting_prior_claims'if len(row['prior_claim_indices'])!=1 else None
        if status:records.append(dict(row,status=status));continue
        index=row['prior_claim_indices'][0];old=original[index];new_id=owners[0]['edge_id'];old_id=old['edge_id']
        if old_id not in edges or edges[old_id]['system']!=native[0]['system']:
            records.append(dict(row,status='prior_pipe_system_conflict_not_reassigned'));continue
        if old.get('equipment_type')not in ('球阀','ball_valve','Ball Valve'):
            records.append(dict(row,status='prior_component_type_conflict_not_reassigned'));continue
        if old_id==new_id:records.append(dict(row,status='existing_native_owner_agrees'));continue
        contacts=native[0]['flange_contacts'];midpoint=[sum(contact['point_WCS'][i]for contact in contacts)/2 for i in range(3)]
        updated=output[index];updated.update(edge_id=new_id,assignment_x=str(midpoint[0]),assignment_y=str(midpoint[1]),edge_distance=str(math.dist([float(old['x']),float(old['y'])],midpoint[:2])),assignment_status='assigned',assignment_basis=MODE,original_edge_id=old.get('original_edge_id')or old_id)
        if updated['owner_equipment']!=old['owner_equipment']:raise ValueError('descriptive equipment membership changed')
        changes.append(dict(source_handle=handle,before=copy.deepcopy(old),after=copy.deepcopy(updated),contact_midpoint_WCS=midpoint,native_contact_evidence=copy.deepcopy(native[0]),native_graph_owner=copy.deepcopy(owners[0]),equipment_membership_retained=True,source_symbol_geometry_moved=False))
        records.append(dict(row,status='native_contact_owner_reapplied',old_edge_id=old_id,new_edge_id=new_id))
    if len(output)!=len(original)or Counter(row['device_name']for row in output)!=Counter(row['device_name']for row in original)or Counter(row['equipment_type']for row in output)!=Counter(row['equipment_type']for row in original):raise ValueError('native component identity or count changed')
    return dict(mode=MODE,records=records,changes=changes,components=output,counts=dict(named_source_population=population,prior_components=len(original),output_components=len(output),reassigned_components=len(changes),statuses=dict(Counter(row['status']for row in records))),all_component_ids_and_counts_conserved=True,equipment_membership_retained=True,source_graph_and_symbol_geometry_unchanged=True,physical_parameters_assigned=0,related_mapping_confirmations_inherited=False,published_graph_changed=False,human_accepted=False)
