"""Bounded floor-plan contact reading; raw XYZ and 3D axis guards are retained.

This is a drawing-view projection, never a new physical contact or pipe length.
It composes the unchanged finite-flange and member-route readers.
"""
import collections
import copy
import math
import types
from native_flange_contact_ownership import flange_contacts as contacts_3d
from native_ball_contact_reapplication import footprint
from native_line_path_evidence import _on
from native_inline_joint_path_coverage import native_joint
from repair_native_flexible_joints import fingerprint
import third_arm_crossview_paths as original_profiles
import member_external_anchored_routes as original_routes

MODE='qualified_member_floor_plan_XY_contact_reading_v1'
VIEW='floor_plan_orthographic_XY'

def require(value,message):
    if not value:raise ValueError(message)

def projected_contacts(geometry,start,end,tol=.05,*,view):
    require(view==VIEW and tol==.05,'explicit floor-plan reading and original tolerance required')
    points=[*geometry['ports_WCS'],*[p for pair in geometry['flanges_WCS']for p in pair]]
    require(all(len(p)==3 and all(math.isfinite(v)for v in p)for p in [*points,start,end]),'finite native XYZ required')
    private=copy.deepcopy(geometry)
    xy=lambda p:[p[0],p[1],0.]
    private['ports_WCS']=[xy(p)for p in geometry['ports_WCS']]
    private['flanges_WCS']=[[xy(p)for p in pair]for pair in geometry['flanges_WCS']]
    contacts=contacts_3d(private,xy(start),xy(end),tol)
    if contacts is None:return None
    # An unrelated tilted LINE is not a contact candidate. A tilted finite
    # candidate remains a blocker; never silently discard a competing pipe.
    require(max(p[2]for p in points)-min(p[2]for p in points)<=tol and abs(start[2]-end[2])<=tol,'tilted geometry needs another native view owner')
    for index,row in enumerate(contacts):
        a,b=geometry['flanges_WCS'][index];t,u=row['pipe_fraction'],row['flange_fraction']
        raw_pipe=[start[i]+t*(end[i]-start[i])for i in range(3)]
        raw_flange=[a[i]+u*(b[i]-a[i])for i in range(3)]
        row.update(point_WCS=raw_pipe,source_flange_WCS=copy.deepcopy([a,b]),
            source_pipe_contact_WCS=raw_pipe,source_flange_contact_WCS=raw_flange,
            source_XYZ_separation=math.dist(raw_pipe,raw_flange),
            contact_coordinate_frame=VIEW,raw_3D_contact_proved=False,
            source_Z_used_as_physical_elevation=False)
    return contacts

def projected_plan_owners(geometry,pipes,graph):
    namespace=dict(original_profiles.plan_owners.__globals__)
    namespace['flange_contacts']=lambda g,a,b:projected_contacts(g,a,b,view=VIEW)
    reader=types.FunctionType(original_profiles.plan_owners.__code__,namespace,original_profiles.plan_owners.__name__)
    return reader(geometry,pipes,graph)

def contact_scope(points,paths):
    """Use both finite contacts; a cut or contained fragment must not disappear."""
    require(len(points)==2,'two native contacts required')
    inside=[any(_on(p[:2],a[:2],b[:2],.05)for path in paths for a,b in zip(path,path[1:]))for p in points]
    require(inside[0]==inside[1],'source scope cuts a component')
    for path in paths:
        for p in (path[0],path[-1]):
            if _on(p[:2],points[0][:2],points[1][:2],.05)and min(math.dist(p[:2],q[:2])for q in points)>.05:
                raise ValueError('source scope boundary lies inside a component')
    return inside[0]

def bounded_plan_profiles(doc,graph,inventory,scopes,template):
    edges={e['edge_id']:e for e in graph['edges']};require(scopes and set(scopes)<=set(edges),'existing plan source edges required')
    private=copy.deepcopy(graph);claims=collections.Counter((c.get('source_top_handle')or c.get('source_handle'))for c in inventory)
    for eid,paths in scopes.items():
        require(paths,'empty source scope')
        for path in paths:
            for a,b in zip(path,path[1:]):
                require(any(_on(a[:2],x[:2],y[:2],.05)and _on(b[:2],x[:2],y[:2],.05)for p in edges[eid]['attribute_paths']for x,y in zip(p,p[1:])),'scope adds an unproved source fragment')
        next(e for e in private['edges']if e['edge_id']==eid)['attribute_paths']=copy.deepcopy(paths)
    pipes=list(doc.modelspace().query('LINE'));selected=[];audit=[]
    for row in inventory:
        eid=row['edge_id']
        if eid not in scopes:continue
        handle=row.get('source_top_handle')or row.get('source_handle');require(handle and claims[handle]==1,'source component has competing original claims')
        insert=doc.entitydb.get(handle);require(insert is not None and insert.dxftype()=='INSERT'and insert in doc.modelspace(),'native modelspace component required')
        kind=original_profiles.ALIASES.get(row['equipment_type']);details={}
        if kind=='ball_valve':
            geometry=footprint(insert);require(geometry is not None,'complete original ball signature required')
            native,owners=projected_plan_owners(geometry,pipes,graph)
            require(len(native)==len(owners)==1 and owners[0]['edge_id']==eid,'projected source contact/graph owner is not unique')
            points=[c['point_WCS']for c in native[0]['flange_contacts']];details=dict(geometry=geometry,native_contact=native[0],native_graph_owner=owners[0])
        elif row['equipment_type']in('flexible_joint','金属软接'):
            require(template and template['block_name']in doc.blocks and fingerprint(doc.blocks[template['block_name']])==template['block_fingerprint_sha256'],'original joint template required')
            joint=native_joint(doc,graph,edges[eid],row,template['block_name'],template['block_fingerprint_sha256'],.05)
            points=joint['contact_points_wcs'];details=dict(native_joint=joint)
        else:raise ValueError('component family needs its existing native scope owner')
        inside=contact_scope(points,scopes[eid])
        if inside:
            require(kind=='ball_valve','in-scope joint requires the joint-aware route profile owner')
            selected.append(copy.deepcopy(row))
        audit.append(dict(source_handle=handle,original_owner_edge=eid,scope='selected_external_route'if inside else'excluded_outside_external_route_original_owner_retained',original_instance=copy.deepcopy(row),**details))
    namespace=dict(original_profiles.native_component_profiles.__globals__);namespace['plan_owners']=projected_plan_owners
    reader=types.FunctionType(original_profiles.native_component_profiles.__code__,namespace,original_profiles.native_component_profiles.__name__)
    profile=reader(doc,private,selected,sorted(scopes),'plan')
    require(len(profile['records'])==len(selected),'selected source component not fully witnessed')
    profile.update(reading_mode=MODE,source_component_scope_audit=audit,original_inventory_mutated=False,
        raw_source_Z_preserved=True,raw_3D_contact_proved=False,physical_lengths_assigned=0)
    return profile

def prove_member_routes(rows,graphs,docs,provider,inputs,config,components,angles,template,*,junction_transition_spec=None):
    """Only independently anchored floor-plan/member contexts may use this view."""
    require(rows,'complete nonempty route cohort required');scopes=collections.defaultdict(list)
    for row in rows:
        require(row['direct_existing_ordinary_anchor']is True,'this reading context needs an existing independent ordinary anchor')
        require(provider['ordinary_junction_mappings'][str(row['floor'])].get(row['plan_remote'])==row['axis_remote'],'source ordinary anchor differs')
        port=row['port'];require(port['system']==row['system']and port['member_node_id'].startswith('MEMBER:'),'qualified same-system member port required')
        scopes[row['plan_edge_id']].extend(copy.deepcopy(row['attribute_paths']))
    # Different external ports may reuse an identical fragment: the profile reads
    # the union once; original per-port component cuts still run inside prove().
    scopes={eid:list({tuple(tuple(p)for p in path):path for path in paths}.values())for eid,paths in scopes.items()}
    plan_profile=bounded_plan_profiles(docs['plan'],graphs['plan'],components['plan'],scopes,template)
    original=original_routes.native_component_profiles
    def profiles(doc,graph,inventory,edge_ids,view):
        if view=='plan':
            require(set(edge_ids)==set(scopes),'native route target scope differs');return copy.deepcopy(plan_profile)
        return original(doc,graph,inventory,edge_ids,view)
    namespace=dict(original_routes.prove.__globals__);namespace['native_component_profiles']=profiles
    if junction_transition_spec is not None:
        from source_stable_junction_reapplication import prepare
        junction_reader=prepare(config,inputs['plan_source'],inputs['plan_graph'],graphs['plan'],junction_transition_spec)
        def junction_factory(supplied,source_hash,graph_hash):
            require(supplied==config and source_hash==inputs['plan_source']['sha256']and graph_hash==inputs['plan_graph']['sha256'],'junction source scope differs')
            return junction_reader
        namespace['current_plan_reader']=junction_factory
    reader=types.FunctionType(original_routes.prove.__code__,namespace,original_routes.prove.__name__)
    records,native_profiles=reader(rows,graphs,docs,provider,inputs,config,components,angles)
    for record in records:
        record['plan_component_reading_mode']=MODE
        record['original_source_Z_preserved']=True
        record['axis_component_reader_3D_unchanged']=True
    return records,native_profiles
