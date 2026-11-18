"""Reconstruct circle-bracketed compound members using independent branch cohorts.

An isolated circle is not a T by itself. This family requires an already
source-qualified lower-member chain, two native brackets, unique axis approaches,
real axis Ts, and an independently read upper-member caption pair.
"""
import collections,copy,hashlib,math
from confirm_crossview_paths import encode
from native_line_path_evidence import LAYERS,_on
from native_paired_end_labels import level_key
from native_paired_caption_geometry import collect as caption_pairs
from compound_carrier_members import carrier_risks
from crossview_equipment_branch_inventory import native_tee,index_graph
from batch_native_path_coverage import collect as coverage
from native_main_endpoint_extent import qualify
from native_plan_projection_lengths import lengths
from pipe_annotation_attributes import parse_dn_annotation
from native_dn_text_position import supported
from source_direct_dn_evidence import _projection

MODE='native_circle_bracketed_compound_member_interfaces_v1'
def point(n):return [n['x'],n['y']]
def scope_id(line,level,system,floor):return 'MEMBER:'+hashlib.sha256(encode(dict(plan_LINE=line,level=level,system=system,floor=floor))).hexdigest()[:16]
def unique_path(proof):
    for edge in proof['edges']:
        if not edge['segments'] or any(s['status']!='single_source_line_covers' or len(s['witnesses'])!=1 or s['witnesses'][0]['scope']!='modelspace' for s in edge['segments']):raise ValueError('source path lacks unique native LINE coverage')
    return sorted({s['witnesses'][0]['source_handle'] for e in proof['edges'] for s in e['segments']})

def declaration(corridor,level):
    selected=[]
    for text in corridor['declarations']:
        choices=[m for m in text['members'] if level_key(m['source_level_text'])==level]
        if len(choices)!=1:raise ValueError('literal member level does not select one plan declaration')
        selected.append(dict(text_handle=text['handle'],member=choices[0]))
    if not selected or len({r['member']['nominal_mm'] for r in selected})!=1:raise ValueError('plan member declarations conflict')
    return selected[0]['member']['nominal_mm'],selected

def native_label_guard(doc,handles,nominal,captions):
    """A new/conflicting or unresolved DN label stops whole-approach inheritance."""
    owned={o['text']['handle']:o for pair in captions['pairs'] for o in pair['observations']};seen=[]
    lines=[e for e in doc.modelspace().query('LINE') if e.dxf.layer in LAYERS.values()]
    # Unresolved MTEXT or nested annotation must not disappear from a proof of
    # unchanged DN. Reuse native INSERT transforms; do not decode proxy bytes.
    def near_scope(entity):
        height=entity.dxf.height if entity.dxftype()=='TEXT' else entity.dxf.char_height
        p=entity.ocs().to_wcs(entity.dxf.insert) if entity.dxftype()=='TEXT' else entity.dxf.insert
        return any((v:=_projection(list(p)[:2],list(line.dxf.start)[:2],list(line.dxf.end)[:2])) and 0<v[0]<1 and v[1]<=2*height for line in lines if line.dxf.handle in handles)
    for entity in doc.modelspace().query('MTEXT'):
        if 'DN' in entity.plain_text().upper() and near_scope(entity):raise ValueError('native MTEXT DN requires its original annotation reader')
    cache={}
    def block_has_DN(name,trail=frozenset()):
        if name in cache:return cache[name]
        if name in trail:return False
        block=doc.blocks.get(name)
        found=block is not None and any((e.dxftype() in ('TEXT','MTEXT') and 'DN' in e.plain_text().upper()) or (e.dxftype()=='INSERT' and block_has_DN(e.dxf.name,trail|{name})) for e in block)
        cache[name]=found;return found
    from ezdxf.disassemble import recursive_decompose
    for insert in doc.modelspace().query('INSERT'):
        if not block_has_DN(insert.dxf.name):continue
        for entity in recursive_decompose([insert]):
            if entity.dxftype() in ('TEXT','MTEXT') and 'DN' in entity.plain_text().upper() and near_scope(entity):raise ValueError('nested native DN requires its original transformed annotation reader')
    for text in doc.modelspace().query('TEXT'):
        raw=text.plain_text().strip()
        if 'DN' not in raw.upper():continue
        h=text.dxf.handle
        if h in owned:
            observation=owned[h]
            if observation['native_pipe']['source_LINE'] in handles:
                if observation['text']['nominal_mm']!=nominal:raise ValueError('another native paired label stops member DN inheritance')
                seen.append(dict(text_handle=h,source_LINE=observation['native_pipe']['source_LINE'],rule='independent_native_caption_pair'))
            continue
        if not supported(text):
            points=[text.ocs().to_wcs(text.dxf.insert)]
            if text.dxf.hasattr('align_point'):points.append(text.ocs().to_wcs(text.dxf.align_point))
            for line in lines:
                if line.dxf.handle not in handles:continue
                a,b=list(line.dxf.start)[:2],list(line.dxf.end)[:2]
                if any((p:=_projection(list(q)[:2],a,b)) and 0<p[0]<1 and p[1]<=2*text.dxf.height for q in points):raise ValueError('unsupported native DN text transform blocks member inheritance')
            continue
        angle=math.radians(text.dxf.rotation);u=[math.cos(angle),math.sin(angle)];height=text.dxf.height;position=list(text.dxf.insert)[:2];candidates=[]
        for line in lines:
            a,b=list(line.dxf.start)[:2],list(line.dxf.end)[:2];length=math.dist(a,b)
            if length<=.05 or abs(u[0]*(b[1]-a[1])-u[1]*(b[0]-a[0]))/length>math.sin(math.radians(2)):continue
            foot=_projection(position,a,b)
            if foot and 0<foot[0]<1 and foot[1]<=2*height:candidates.append((foot[1],line.dxf.handle))
        candidates.sort()
        if not any(line in handles for _,line in candidates):continue
        unique=candidates and (len(candidates)==1 or candidates[1][0]-candidates[0][0]>.5*height)
        if unique and candidates[0][1] not in handles:continue
        if h in captions['F_owned_texts']:raise ValueError('member interval has an F-owned label requiring its original ordered reader')
        label=parse_dn_annotation(raw)
        if not unique or label is None:raise ValueError('unresolved native DN annotation stops member inheritance')
        if label['nominal_mm']!=nominal:raise ValueError('direct native DN changes inside member interval')
        seen.append(dict(text_handle=h,source_LINE=candidates[0][1],rule='unique_native_direct_annotation_crosscheck'))
    return seen

def group(plan_doc,axis_doc,plan,axis,rows,corridor,captions,units,angles,hashes):
    pn,_,_=index_graph(plan);an,ae,adj=index_graph(axis);first=rows[0];system=first['system'];floor=first['floor'];lower=first['member_scope_id']
    if any(r['system']!=system or r['floor']!=floor or r['member_scope_id']!=lower or r['plan_LINE']!=first['plan_LINE'] or r['axis_LINE']!=first['axis_LINE'] or r['nominal_mm']!=first['nominal_mm'] for r in rows):raise ValueError('lower member cohort identity differs')
    source=plan_doc.entitydb.get(first['plan_LINE'])
    if not source or source.dxftype()!='LINE' or source not in plan_doc.modelspace() or source.dxf.layer!=LAYERS[system]:raise ValueError('lower member carrier source differs')
    a,b=list(source.dxf.start)[:2],list(source.dxf.end)[:2];size=math.dist(a,b)
    if size<=.05:raise ValueError('degenerate native plan carrier')
    direction=[(b[i]-a[i])/size for i in(0,1)]
    station=lambda p:sum((p[i]-a[i])*direction[i] for i in(0,1))
    anchors={};links=collections.Counter()
    for row in rows:
        if len(row['anchors'])!=2:raise ValueError('two independent branch anchors required per inherited interval')
        for anchor in row['anchors']:
            old=anchors.setdefault(anchor['plan_T'],anchor)
            if old!=anchor:raise ValueError('inherited branch anchor changed within cohort')
        links[tuple(sorted(x['plan_T'] for x in row['anchors']))]+=1
    ordered=sorted(anchors.values(),key=lambda x:station(point(pn[x['plan_T']])))
    expected={tuple(sorted((x['plan_T'],y['plan_T']))) for x,y in zip(ordered,ordered[1:])}
    if len(ordered)<2 or len({x['equipment_id'] for x in ordered})!=len(ordered) or set(links)!=expected or any(n!=1 for n in links.values()):raise ValueError('complete nonduplicated lower member chain required')
    for anchor in ordered:
        if not _on(point(pn[anchor['plan_T']]),a,b,.05):raise ValueError('native branch anchor leaves compound carrier')
    ax=axis_doc.entitydb[first['axis_LINE']];aa,ab=list(ax.dxf.start)[:2],list(ax.dxf.end)[:2];alen=math.dist(aa,ab);u=[(ab[i]-aa[i])/alen for i in(0,1)]
    positions=[sum((point(an[x['axis_T']])[i]-aa[i])*u[i] for i in(0,1)) for x in ordered]
    differences=[y-x for x,y in zip(positions,positions[1:])]
    if not (all(v>.05 for v in differences) or all(v<-.05 for v in differences)):raise ValueError('independent branch order differs between views')
    native_circles=[]
    for circle in plan_doc.modelspace().query('CIRCLE'):
        p=list(circle.ocs().to_wcs(circle.dxf.center))[:2]
        if _on(p,a,b,.05):native_circles.append(dict(handle=circle.dxf.handle,point=p,station=station(p),radius=circle.dxf.radius,layer=circle.dxf.layer))
    low,high=[station(point(pn[x['plan_T']])) for x in (ordered[0],ordered[-1])]
    if any(low-.05<=c['station']<=high+.05 for c in native_circles):raise ValueError('an interior circle requires another member scope')
    choices=[[c for c in native_circles if c['station']<low-.05],[c for c in native_circles if c['station']>high+.05]]
    if any(not c for c in choices):raise ValueError('native circles do not bracket the independent branch cohort')
    brackets=[max(choices[0],key=lambda c:c['station']),min(choices[1],key=lambda c:c['station'])]
    for circle in brackets:
        if circle['layer']!=LAYERS[system] or not math.isfinite(circle['radius']) or circle['radius']<=.05 or sum(abs(c['station']-circle['station'])<.05 for c in native_circles)!=1:raise ValueError('native circle layer, radius or uniqueness differs')
    if abs(brackets[0]['radius']-brackets[1]['radius'])>.05:raise ValueError('circle bracket styles differ')
    known={r['axis_edge_id'] for r in rows};interfaces=[]
    for anchor,circle in zip((ordered[0],ordered[-1]),brackets):
        nid=anchor['axis_T'];options=[]
        for edge in adj[nid]:
            other=edge['end_node_id'] if edge['start_node_id']==nid else edge['start_node_id']
            if edge['edge_id'] not in known and edge['system']==system and an[other].get('node_type') in ('tee','physical_junction') and an[other].get('floor')==floor:options.append((edge,other))
        if len(options)!=1:raise ValueError('axis outer member approach is not unique')
        edge,other=options[0]
        if any(edge.get(k)!=floor for k in ('floor_start','floor_end')):raise ValueError('cohort approach crosses floors')
        paths=coverage(axis_doc,axis,[edge['edge_id']],hashes['axis_source'],hashes['axis_graph']);lines=unique_path(paths)
        if first['axis_LINE'] not in lines or len(lines)<2:raise ValueError('approach lacks inherited member continuation and separate local rise')
        interfaces.append(dict(plan_circle=circle,lower_anchor=copy.deepcopy(anchor),axis_primary_T=other,axis_approach_edge=edge['edge_id'],native_axis_approach=paths,
            native_axis_primary_T=native_tee(axis_doc,axis,other,hashes['axis_source'],hashes['axis_graph'])))
    targets={x['axis_primary_T'] for x in interfaces}
    mains=[e for e in axis['edges'] if e['system']==system and {e['start_node_id'],e['end_node_id']}==targets]
    if len(mains)!=1:raise ValueError('native primary main is not unique between bracket interfaces')
    main=mains[0];native_main=coverage(axis_doc,axis,[main['edge_id']],hashes['axis_source'],hashes['axis_graph']);lines=unique_path(native_main)
    if len(lines)!=1 or lines[0]==first['axis_LINE']:raise ValueError('upper and lower member native LINEs must differ')
    observations=[o for pair in captions['pairs'] for o in pair['observations'] if o['native_pipe']['source_LINE']==lines[0]]
    if not observations or len({o['text']['literal_level_key'] for o in observations})!=1:raise ValueError('upper member source caption level is missing or conflicts')
    level=observations[0]['text']['literal_level_key'];lower_level=first['literal_level_key']
    if level==lower_level:raise ValueError('caption does not distinguish two compound members')
    nominal,declared=declaration(corridor,level)
    if any(o['text']['nominal_mm']!=nominal for o in observations):raise ValueError('axis cross-check conflicts with the plan member DN')
    primary_label_guard=native_label_guard(axis_doc,lines,nominal,captions)
    for row in rows:
        old=row['axis_caption_crosscheck'];matches=[o for pair in captions['pairs'] for o in pair['observations'] if o['text']['handle']==old['text']['handle']]
        if len(matches)!=1 or matches[0]['native_pipe']['source_LINE']!=row['axis_LINE'] or matches[0]['text']!=old['text']:raise ValueError('inherited member caption lost F-safe native ownership')
    upper=scope_id(first['plan_LINE'],level,system,floor);nodes=[];edges=[];ports=[]
    for interface in interfaces:
        circle=interface['plan_circle'];nid=upper+':CIRCLE:'+circle['handle'];interface['member_primary_node_id']=nid
        nodes.append(dict(node_id=nid,node_type='tee',x=circle['point'][0],y=circle['point'][1],floor=floor,system=system,review_required=False,
            member_scope_id=upper,source_circle_handle=circle['handle'],axis_node_id=interface['axis_primary_T'],literal_level_key=level,physical_elevation_mm=None,
            source_basis='native_circle_bracket_and_independent_complete_branch_cohort_and_native_axis_three_rays',physical_port_coordinates_verified=False))
    mapping='CIRCLE-MEMBER:'+lower+':'+main['edge_id'];peid=upper+':BETWEEN:'+':'.join(sorted(c['handle'] for c in brackets))
    member_main=dict(edge_id=peid,start_node_id=nodes[0]['node_id'],end_node_id=nodes[1]['node_id'],floor_start=floor,floor_end=floor,system=system,
        attribute_paths=[[c['point'] for c in brackets]],source_handles=[first['plan_LINE']],member_scope_id=upper)
    projected=dict(nodes=nodes,edges=[member_main]);plan_coverage=coverage(plan_doc,projected,[peid],hashes['plan_source'],hashes['plan_graph']);unique_path(plan_coverage)
    maprow=dict(kind='same_floor_T_to_T_main',mapping_id=mapping,floor=floor,system=system,plan_edges=[peid],iso_edges=[main['edge_id']],
        plan_start=nodes[0]['node_id'],plan_end=nodes[1]['node_id'],iso_start=interfaces[0]['axis_primary_T'],iso_end=interfaces[1]['axis_primary_T'])
    metric=lengths(projected,plan_coverage,maprow,units);extent=qualify(projected,axis,maprow,nominal,metric,angles)
    member_main.update(diameter_nominal_mm=nominal,plan_run_centerline_mm=metric['value_mm'],installed_whole_length_mm=None,net_pipe_cut_length_mm=None)
    edges.append(member_main)
    common=dict(floor=floor,system=system,plan_LINE=first['plan_LINE'],source_hashes=copy.deepcopy(hashes),DN_used_for_mapping=False,
        installed_whole_length_mm=None,net_pipe_cut_length_mm=None,plan_component_member_allocation='unresolved',human_accepted=False)
    records=[dict(common,mapping_id=mapping,axis_edge_id=main['edge_id'],plan_member_edge_id=peid,kind='primary_member_main',nominal_mm=nominal,
        member_scope_id=upper,literal_level_key=level,physical_elevation_mm=None,plan_declarations=declared,axis_caption_crosschecks=observations,
        plan_attribute_paths=member_main['attribute_paths'],plan_projection=metric,complete_horizontal_centerline_route_mm=extent['complete_horizontal_centerline_route_mm'],
        endpoint_relations=extent['endpoint_relations'],axis_nodes=[main['start_node_id'],main['end_node_id']],axis_attribute_paths=copy.deepcopy(main['attribute_paths']),
        native_axis_coverage=native_main,native_plan_coverage=plan_coverage,native_DN_scope_guard=primary_label_guard)]
    for interface,node in zip(interfaces,nodes):
        anchor=interface['lower_anchor'];lower_nid=lower+':'+anchor['plan_T'];eid=lower+':APPROACH:'+interface['plan_circle']['handle'];p=point(pn[anchor['plan_T']]);q=interface['plan_circle']['point']
        edge=dict(edge_id=eid,start_node_id=lower_nid,end_node_id=node['node_id'],floor_start=floor,floor_end=floor,system=system,
            attribute_paths=[[p,q]],source_handles=[first['plan_LINE']],member_scope_id=lower,diameter_nominal_mm=first['nominal_mm'],
            path_domain='same_floor_horizontal_projection_and_unmeasured_local_rise',installed_whole_length_mm=None,net_pipe_cut_length_mm=None)
        readgraph=dict(nodes=[],edges=[edge]);pcov=coverage(plan_doc,readgraph,[eid],hashes['plan_source'],hashes['plan_graph']);unique_path(pcov)
        m=lengths(readgraph,pcov,dict(plan_edges=[eid],system=system),units);edges.append(edge)
        raw=ae[interface['axis_approach_edge']]
        approach_label_guard=native_label_guard(axis_doc,unique_path(interface['native_axis_approach']),first['nominal_mm'],captions)
        records.append(dict(common,mapping_id='CIRCLE-MEMBER:'+lower+':'+raw['edge_id'],axis_edge_id=raw['edge_id'],plan_member_edge_id=eid,kind='lower_member_approach_with_local_rise',
            nominal_mm=first['nominal_mm'],member_scope_id=lower,literal_level_key=lower_level,physical_elevation_mm=None,
            plan_declarations=copy.deepcopy(first['plan_declarations']),inherited_member_mapping_ids=sorted(r['mapping_id'] for r in rows),
            inherited_from_member_node=lower_nid,to_primary_member_node=node['node_id'],plan_attribute_paths=edge['attribute_paths'],plan_projection=m,
            complete_horizontal_centerline_route_mm=None,local_rise_length_mm=None,local_rise_level_literals=[lower_level,level],level_difference_used_as_length=False,
            axis_nodes=[raw['start_node_id'],raw['end_node_id']],axis_attribute_paths=copy.deepcopy(raw['attribute_paths']),native_axis_coverage=interface['native_axis_approach'],native_plan_coverage=pcov,native_DN_scope_guard=approach_label_guard))
        external=[e for e in adj[interface['axis_primary_T']] if e['edge_id'] not in (main['edge_id'],raw['edge_id'])]
        if len(adj[interface['axis_primary_T']])!=3 or len(external)!=1 or external[0]['system']!=system:raise ValueError('primary interface must retain exactly its third same-system port')
        e=external[0];ports.append(dict(member_node_id=node['node_id'],axis_node_id=interface['axis_primary_T'],axis_edge_id=e['edge_id'],
            other_axis_node=e['end_node_id'] if e['start_node_id']==interface['axis_primary_T'] else e['start_node_id'],system=system,
            status='outside_current_member_interval_plan_route_not_yet_qualified',port_not_deleted=True))
    return dict(member_scope_id=lower,primary_member_scope_id=upper,system=system,floor=floor,plan_LINE=first['plan_LINE'],axis_lower_LINE=first['axis_LINE'],axis_primary_LINE=lines[0],
        independent_branch_anchors=ordered,source_circles=brackets,interfaces=interfaces,records=records,new_member_nodes=nodes,new_member_edges=edges,external_ports=ports,
        plan_graph_modified=False,axis_graph_modified=False,component_instances_created=False)

def collect(plan_doc,axis_doc,plan,axis,parent,units,angles,hashes):
    captions=caption_pairs(axis_doc);barriers=carrier_risks(plan_doc,plan,hashes['plan_source'])
    if encode(barriers)!=encode(parent['carrier_barriers']):raise ValueError('inherited compound native carrier barriers changed')
    corridors={r['source_LINE']:r for r in barriers['corridors']};groups=collections.defaultdict(list)
    for row in parent['records']:groups[row['member_scope_id']].append(row)
    results=[];pending=[]
    for ident,rows in groups.items():
        try:results.append(group(plan_doc,axis_doc,plan,axis,rows,corridors[rows[0]['plan_LINE']],captions,units,angles,hashes))
        except ValueError as exc:pending.append(dict(member_scope_id=ident,system=rows[0]['system'],plan_LINE=rows[0]['plan_LINE'],reason=str(exc)))
    new=copy.deepcopy(parent['member_local_graph']);old_nodes={n['node_id'] for n in new['nodes']};old_edges={e['edge_id'] for e in new['edges']};records=[];ports=[]
    for g in results:
        for node in g['new_member_nodes']:
            if node['node_id'] in old_nodes:raise ValueError('member interface node identity overlaps parent')
            new['nodes'].append(node);old_nodes.add(node['node_id'])
        for edge in g['new_member_edges']:
            if edge['edge_id'] in old_edges:raise ValueError('new member interval overlaps parent')
            new['edges'].append(edge);old_edges.add(edge['edge_id'])
        records.extend(g['records']);ports.extend(g['external_ports'])
    if len({r['axis_edge_id'] for r in records})!=len(records):raise ValueError('new axis member writers overlap')
    if any(e['start_node_id'] not in old_nodes or e['end_node_id'] not in old_nodes for e in new['edges']):raise ValueError('member edge endpoint missing after reconstruction')
    if len({n['node_id'] for n in new['nodes']})!=len(new['nodes']) or len({e['edge_id'] for e in new['edges']})!=len(new['edges']):raise ValueError('member graph IDs repeat')
    new.update(scope='inherited_lower_members_plus_circle_bracketed_primary_members_and_mixed_local_approaches',external_ports=ports,global_topology_complete=False,calculation_ready=False,human_accepted=False)
    return dict(mode=MODE,groups=results,records=records,pending=pending,native_caption_pairs=captions,carrier_barriers=barriers,member_local_graph=new,
        inherited_member_records=len(parent['records']),retained_member_axis_edges=sorted(r['axis_edge_id'] for r in parent['records']),
        counts=dict(cohorts_screened=len(groups),cohorts_qualified=len(results),new_interface_nodes=sum(len(g['new_member_nodes']) for g in results),
            new_axis_correspondences=len(records),primary_member_mains=sum(r['kind']=='primary_member_main' for r in records),mixed_member_approaches=sum(r['kind']!='primary_member_main' for r in records),
            complete_centerlines=sum(r['complete_horizontal_centerline_route_mm'] is not None for r in records),unresolved_external_ports=len(ports),unique_external_axis_edges=len({p['axis_edge_id'] for p in ports}),pending_cohorts=len(pending)),
        DN_value_source='floor_plan_compound_declarations_and_inherited_member_T_continuity',DN_used_for_mapping=False,source_drawing_graphs_unchanged=True,
        member_topology_rebuilt=True,installed_lengths_assigned=0,physical_level_or_units_inferred=False,global_plan_topology_complete=False,human_accepted=False)
