"""Inherit qualified floor-plan main DN onto native axis branch horizontals.

The source of the scalar is the floor plan. Axis geometry proves a true third
arm and continuity; axis labels only check for transitions/conflicts. This
does not assign an individual device correspondence, vertical DN or length.
"""
import copy,math
from confirm_crossview_paths import encode
from crossview_equipment_branch_inventory import index_graph,native_tee
from inherited_marker_and_crossover_evidence import collect as marker_ports,population
from axis_unbranched_vertical_DN import chain_evidence,source_Z,source_key,annotation_index
from compound_member_interfaces import native_label_guard
from native_paired_caption_geometry import collect as captions
from pipe_annotation_attributes import contact

MODE='native_plan_seeded_axis_T_branch_horizontal_DN_v1'

def require(value,message):
    if not value:raise ValueError(message)

def main_endpoint_support(graph,node_id,main_edges,owners):
    """Both actual through arms need a qualified domain at this exact T."""
    nodes,_,_=index_graph(graph);node=nodes[node_id];point=[node['x'],node['y']]
    require(len(main_edges)==2 and len(owners)==2,'two qualified plan-main arms required')
    require(len({(r['source_scope_id'],r['nominal_mm'],r['floor'],r['system'])for r in owners})==1,
            'two independently plan-owned main arms disagree')
    nominal=owners[0]['nominal_mm']
    require(type(nominal)in(int,float)and math.isfinite(nominal)and nominal>0,'positive source-plan DN required')
    found=[]
    for edge,owner in zip(main_edges,owners):
        require(owner['axis_edge_id']==edge['edge_id']and owner['axis_attribute_paths']==edge['attribute_paths']
            and owner['axis_nodes']==[edge['start_node_id'],edge['end_node_id']]
            and owner['system']==edge['system']and edge['floor_start']==edge['floor_end']==owner['floor'],
            'qualified plan-main owner has another graph, floor or system')
        hits=[s for s in owner['horizontal_segment_domains']if min(math.dist(point,p)for p in s['scope_points'])<=.05]
        require(len(hits)==1,'main endpoint lacks exact plan-owned horizontal domain')
        s=hits[0];pi,si=s['path_index'],s['segment_index']
        require(s['edge_id']==edge['edge_id']and s['system']==edge['system']and s['direction_class']=='horizontal'
            and s['native_source_status']=='single_source_line_covers'
            and s['scope_points']==edge['attribute_paths'][pi][si:si+2],
            'source-plan main domain changed or is not horizontal')
        found.append(copy.deepcopy(s))
    return found

def discover(graph,main_rows):
    nodes,_,adj=index_graph(graph);records=[]
    for nid in sorted(nodes):
        arms=adj[nid]
        if len(arms)!=3 or nodes[nid].get('node_type')not in('tee','physical_junction'):continue
        owned=[e for e in arms if e['edge_id']in main_rows]
        if not owned:continue
        for branch in arms:
            if branch['edge_id']in main_rows:continue
            peers=[x for x in(branch['start_node_id'],branch['end_node_id'])if x!=nid]
            if len(peers)!=1 or peers[0]not in nodes:continue
            peer=nodes[peers[0]]
            if peer.get('node_type')!='virtual_equipment'or peer.get('subtype')!='external_system_interface':continue
            records.append(dict(axis_edge_id=branch['edge_id'],axis_T=nid,axis_interface=peers[0],
                main_arms=[e['edge_id']for e in arms if e is not branch]))
    require(len({r['axis_edge_id']for r in records})==len(records),'competing main-to-branch owners')
    return records

def qualify(candidate,doc,graph,route,main_rows,values,items,sh,gh,pop,caps,annotation,marker_cache):
    nodes,edges,adj=index_graph(graph);nid=candidate['axis_T'];eid=candidate['axis_edge_id'];branch=edges[eid]
    arms=adj[nid];mains=[edges[x]for x in candidate['main_arms']]
    require(len(arms)==3 and {e['edge_id']for e in arms}=={eid,*candidate['main_arms']},'current three-arm star changed')
    require({e['system']for e in arms}=={branch['system']},'supply and return cannot inherit across one T')
    require(all(e['edge_id']in main_rows for e in mains),'two qualified plan-main arms required')
    owners=[main_rows[e['edge_id']]for e in mains];root_scopes=main_endpoint_support(graph,nid,mains,owners)
    nominal=owners[0]['nominal_mm'];point=[nodes[nid]['x'],nodes[nid]['y']]
    require(branch['floor_start']==branch['floor_end']==owners[0]['floor'],'branch leaves the source-plan floor')
    proof=native_tee(doc,graph,nid,sh,gh);rays=proof.get('junctions',[{}])[0].get('source_rays',[])
    require(len(rays)==3,'three source-proved native T rays required')
    pairs=[{a['edge_id'],b['edge_id']}for i,a in enumerate(rays)for b in rays[i+1:]
        if sum(x*y for x,y in zip(a['direction'],b['direction']))<-math.cos(math.radians(.1))]
    require(pairs==[set(candidate['main_arms'])],'plan-owned arms are not the unique original through pair')
    far=candidate['axis_interface']
    if far not in marker_cache:marker_cache[far]=marker_ports(doc,graph,far,sh,gh,pop)
    ports=[r for r in marker_cache[far]['records']if r['edge_id']==eid and r['system']==branch['system']]
    require(len(ports)==1,'one typed drawing port required');port=ports[0]
    rows={source_key(s):s for s in route['records']}
    require(len(rows)==len(route['records']),'duplicate original route domains')
    physical=[copy.deepcopy(s)for s in route['records']if s['edge_id']==eid and s['segment_index']!=port['display_segment_index']]
    require(len(branch['attribute_paths'])==1 and len(physical)==len(branch['attribute_paths'][0])-2,
            'complete physical branch population required')
    for s in physical:
        require(s['path_index']==0 and s['scope_points']==branch['attribute_paths'][0][s['segment_index']:s['segment_index']+2]
            and s['system']==branch['system']and s['floor_start']==s['floor_end']==owners[0]['floor']
            and s['native_source_status']=='single_source_line_covers'and s['direction_class']in('horizontal','vertical'),
            'unresolved physical source domain, floor or direction')
    physical.sort(key=lambda s:s['segment_index'])
    require(bool(physical),'physical source branch required')
    if math.dist(physical[0]['scope_points'][0],point)>.05:
        physical.reverse()
        for s in physical:s['scope_points'].reverse()
    require(math.dist(physical[0]['scope_points'][0],point)<=.05,'physical branch does not start at the native T')
    chain=chain_evidence(physical,None,items)
    for s in root_scopes:
        h=s['native_witnesses'][0]['source_handle'];line=doc.entitydb.get(h)
        require(line is not None and line in doc.modelspace()and line.dxftype()=='LINE','original through-main LINE required')
        require(abs(source_Z(dict(XYZ=[list(line.dxf.start),list(line.dxf.end)]),point)-source_Z(chain['native_chain'][0],point))<=.05,
                'branch/main native XYZ contact differs')
    handles={x['child_handle']for x in chain['native_chain']}
    guard=native_label_guard(doc,handles,nominal,caps)
    require(not any(contact(a,b,*s['scope_points'])is not None for a,b in annotation['F_strokes']for s in physical),
            'ordered F leader crosses branch inheritance corridor')
    horizontal=[copy.deepcopy(rows[source_key(s)])for s in physical if s['direction_class']=='horizontal']
    require(bool(horizontal),'no horizontal attribute domain')
    old=values[eid].get('diameter_nominal_mm')
    require(old in(None,'')or old==nominal,'old whole diameter conflicts; preserve old writer')
    return dict(candidate,system=branch['system'],floor=owners[0]['floor'],nominal_mm=nominal,
        axis_nodes=[branch['start_node_id'],branch['end_node_id']],axis_attribute_paths=copy.deepcopy(branch['attribute_paths']),
        main_source_scope_id=owners[0]['source_scope_id'],main_owner_records=copy.deepcopy(owners),
        native_T=proof,branch_chain=chain,horizontal_segment_domains=horizontal,
        scope_paths=[s['scope_points']for s in horizontal],excluded_marker_display_segment=port['display_segment_index'],
        native_marker_port=copy.deepcopy(port),original_caption_consistency_guard=guard,old_whole_DN=old,
        source='floor_plan_main_DN_inherited_through_source_checked_axis_T',
        mapping_kind='uniform_plan_main_DN_to_native_third_arm_without_individual_view_pairing',
        axis_labels_validation_only=True,whole_axis_DN_assigned=False,physical_length_mm=None,
        vertical_values_assigned=0,internal_device_identities_assigned=False,human_accepted=False)

def collect(doc,graph,route,main_records,values,items,sh,gh):
    require(graph['metadata']['source_sha256']==sh and route['inputs']['source']['sha256']==sh
        and route['inputs']['graph']['sha256']==gh,'current source graph and routing bindings required')
    before=encode(graph),encode(route),encode(main_records),encode(values),encode(items)
    main_rows={r['axis_edge_id']:r for r in main_records}
    require(len(main_rows)==len(main_records),'competing qualified source-plan main owners')
    candidates=discover(graph,main_rows);pop=population(doc,sh);caps=captions(doc);index=annotation_index(doc,graph,sh)
    markers={};records=[];pending=[]
    for row in candidates:
        try:records.append(qualify(row,doc,graph,route,main_rows,values,items,sh,gh,pop,caps,index,markers))
        except ValueError as exc:pending.append(dict(row,reason=str(exc),new_DN_assigned=None,physical_length_mm=None))
    require(before==(encode(graph),encode(route),encode(main_records),encode(values),encode(items)),
            'original graph, routes, source owners, values or normalized items mutated')
    require(len(records)+len(pending)==len(candidates),'complete candidate conservation failed')
    return dict(mode=MODE,records=records,pending=pending,source_marker_population=pop['proof'],
        counts=dict(screened_branches=len(candidates),qualified_branches=len(records),held_branches=len(pending),
            qualified_horizontal_domains=sum(len(r['horizontal_segment_domains'])for r in records)),
        original_native_T_bend_marker_and_caption_owners_reused=True,branch_labels_never_seed_the_main=True,
        graph_mutated=False,components_changed=False,vertical_values_assigned=0,physical_lengths_assigned=0,
        individual_equipment_correspondences_assigned=0,human_accepted=False,whole_goal_complete=False)
