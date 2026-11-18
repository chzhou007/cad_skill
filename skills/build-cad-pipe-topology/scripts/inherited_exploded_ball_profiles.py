"""Replay the original exploded-ball recognizer and finite flange ownership.

The old SH16 recognizer remains byte-exact. Its drawing bounds are replaced
only for candidate discovery; complete native bodies and unique native/graph
contacts, not a symbol centre or nearest edge, qualify a selected instance.
"""
import collections,copy,importlib,itertools,math,sys,types
from pathlib import Path
from ezdxf import bbox
from legacy_named_provider_inventory import require
from native_ball_contact_reapplication import source_owners
from native_flange_contact_ownership import flange_contacts
from third_arm_crossview_paths import native_component_profiles,plan_owners

FAMILY='EXPLODED:H-PICPNT-91'

def owner():
    directory=Path(__file__).parent/'legacy_v17'
    sys.path.insert(0,str(directory))
    try:module=importlib.import_module('build_edges')
    finally:sys.path.pop(0)
    require(Path(module.__file__).resolve()==(directory/'build_edges.py').resolve(),
            'exploded recognizer escaped the original native owner')
    return module

def footprint(parts,point,tol=.05):
    """Only the original six-primitive body; no incomplete shape fallback."""
    if collections.Counter(e.dxftype()for e in parts)!={'LINE':3,'ELLIPSE':2,'HATCH':1}:return None
    if any(e.dxf.get('color',256)!=2 for e in parts):return None
    lines=[(list(e.dxf.start),list(e.dxf.end))for e in parts if e.dxftype()=='LINE']
    if not all(math.isfinite(v)for ab in lines for p in ab for v in p):return None
    z=[p[2]for ab in lines for p in ab]
    if max(z)-min(z)>tol:return None
    hatch=next(e for e in parts if e.dxftype()=='HATCH');bounds=bbox.extents([hatch],fast=True)
    if not bounds.has_data:return None
    z.extend([bounds.extmin.z,bounds.extmax.z])
    z.extend(e.dxf.center.z for e in parts if e.dxftype()=='ELLIPSE')
    if max(z)-min(z)>tol:return None
    center=[(bounds.extmin[i]+bounds.extmax[i])/2 for i in(0,1)]
    if math.dist(center,point)>tol:return None
    options=[]
    for first,second in itertools.combinations(lines,2):
        a=[first[1][i]-first[0][i]for i in(0,1)];b=[second[1][i]-second[0][i]for i in(0,1)]
        if abs(a[0]*b[1]-a[1]*b[0])>1e-6*max(math.dist(*first)*math.dist(*second),1):continue
        p=[sum(q[i]for q in first)/2 for i in range(3)];q=[sum(t[i]for t in second)/2 for i in range(3)]
        length=math.dist(p,q)
        if length<=tol:continue
        fraction=sum((center[i]-p[i])*(q[i]-p[i])for i in(0,1))/sum((q[i]-p[i])**2 for i in(0,1))
        if not 0<fraction<1:continue
        geometry=dict(center_WCS=center+[sum(z)/len(z)],ports_WCS=[p,q],flanges_WCS=[first,second],
                      signature='original_HATCH_two_ELLIPSE_three_LINE_exploded_ball')
        c=geometry['center_WCS'];start=[c[i]-2*(q[i]-p[i])for i in range(3)];end=[c[i]+2*(q[i]-p[i])for i in range(3)]
        if flange_contacts(geometry,start,end,tol)is not None:options.append(geometry)
    return options[0]if len(options)==1 else None

def candidates(doc):
    old=owner();kernel=old.collect_exploded_ball_valve_instances
    discover=types.FunctionType(kernel.__code__,dict(kernel.__globals__,point_is_in_graph_scope=lambda point,layout:True),kernel.__name__)
    return old,discover(doc,None)

def recover(doc,graph,components,view):
    """Recover physical source instances absent from the old inventory.

    Keep the canonical graph and every old row unchanged. The separate reading
    inventory names each recovered native instance by its stable source handle.
    No ambiguous source or graph contact creates a new instance.
    """
    require(view in('plan','iso'),'explicit native component view required')
    original=copy.deepcopy(components);output=copy.deepcopy(components);claims=collections.defaultdict(list)
    for row in components:
        if row.get('source_top_handle'):claims[row['source_top_handle']].append(row)
    old,population=candidates(doc);pipes=list(doc.modelspace().query('LINE'));records=[];held=[]
    reader=plan_owners if view=='plan'else source_owners
    for candidate in population:
        handle=candidate.source_top_handle;top=doc.entitydb.get(handle)
        geometry=footprint(list(old.graph.recursive_entities(top)),[candidate.x,candidate.y])if top is not None else None
        native,owners=reader(geometry,pipes,graph)if geometry is not None else([],[])
        if claims.get(handle):continue
        if geometry is None or len(native)!=1 or len(owners)!=1:
            held.append(dict(source_handle=handle,reason='unclaimed_known_candidate_lacks_unique_complete_body_or_native_graph_contact',native_candidates=native,graph_candidates=owners));continue
        points=[c['point_WCS']for c in native[0]['flange_contacts']];mid=[sum(p[i]for p in points)/2 for i in range(3)]
        row={key:''for key in original[0]}if original else{}
        row.update(device_name='球阀-SRC-'+handle,equipment_type='球阀',type_code='BV',x=str(candidate.x),y=str(candidate.y),
                   assignment_x=str(mid[0]),assignment_y=str(mid[1]),source_kind='exploded_geometry',source_block_name=FAMILY,
                   source_top_handle=handle,owner_equipment='',system_hint=native[0]['system'],edge_id=owners[0]['edge_id'],
                   edge_distance=str(math.dist([candidate.x,candidate.y],mid[:2])),assignment_status='assigned')
        require(row['device_name']not in{r['device_name']for r in output},'recovered source instance ID collides')
        output.append(row);records.append(dict(source_handle=handle,edge_id=row['edge_id'],geometry=geometry,native_contact=native[0],native_graph_owner=owners[0],recovered_instance=copy.deepcopy(row)))
    require(output[:len(original)]==original,'exploded recovery changed an old component')
    return output,dict(records=records,held=held,original_count=len(original),reading_inventory_count=len(output),
                       original_candidate_population=len(population),source_graph_mutated=False,original_instances_exact=True,
                       recovered_physical_source_instances=len(records),human_accepted=False)

def collect(doc,graph,components,edge_ids,view):
    selected=set(edge_ids);require(len(selected)==len(edge_ids),'duplicate exploded profile target')
    require(view in('plan','iso'),'explicit native component view required')
    old,population=candidates(doc);claims=collections.defaultdict(list)
    for row in components:
        if row.get('source_block_name')==FAMILY:claims[row.get('source_top_handle')].append(row)
    pipes=list(doc.modelspace().query('LINE'));records=[];held=[];represented=set()
    reader=plan_owners if view=='plan'else source_owners
    for candidate in population:
        prior=claims.get(candidate.source_top_handle,[]);top=doc.entitydb.get(candidate.source_top_handle)
        geometry=footprint(list(old.graph.recursive_entities(top)),[candidate.x,candidate.y])if top is not None else None
        native,owners=reader(geometry,pipes,graph)if geometry is not None else([],[])
        relevant=any(r['edge_id']in selected for r in prior)or any(r['edge_id']in selected for r in owners)
        if not relevant:continue
        require(geometry is not None and len(native)==len(owners)==len(prior)==1,'exploded body, original claim or native/graph contact is not unique')
        row=prior[0];require(row['edge_id']==owners[0]['edge_id']and row['equipment_type']in('球阀','ball_valve','Ball Valve'),'exploded original owner or family differs')
        require(row['source_top_handle']not in represented,'exploded instance represented twice')
        represented.add(row['source_top_handle'])
        records.append(dict(source_handle=row['source_top_handle'],edge_id=row['edge_id'],geometry=geometry,
                            native_contact=native[0],native_graph_owner=owners[0],original_instance=copy.deepcopy(row)))
    target=[r for r in components if r['edge_id']in selected and r.get('source_block_name')==FAMILY]
    require(len(target)==len(represented)and all(r['source_top_handle']in represented for r in target),'selected exploded source instance was not independently requalified')
    # Preserve the named family reader and require all other target families to
    # have their original owner. Recognition does not reassign any instance.
    named=native_component_profiles(doc,graph,[r for r in components if r.get('source_block_name')!=FAMILY],edge_ids,view)
    combined=named['records']+records
    profiles={eid:dict(collections.Counter('ball_valve'for r in combined if r['edge_id']==eid))for eid in edge_ids}
    return dict(records=combined,profiles=profiles,original_exploded_recognizer_reused=True,
                original_candidate_population=len(population),native_double_flange_contacts_required=True,
                discovery_scope='complete_modelspace_original_geometry_kernel_then_finite_native_graph_owner',
                component_owners_mutated=False,component_instances_created=0,human_accepted=False)
