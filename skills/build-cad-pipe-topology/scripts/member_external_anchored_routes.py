"""Join qualified member reading scopes to independently anchored ordinary routes.

Coordinates clip a previously proved carrier; they never identify a pipe member.
Keep the clipped fragments, source omissions, component owners and namespaces.
"""
import collections,copy,hashlib,math
from confirm_crossview_paths import encode
from native_line_path_evidence import _on
from crossview_equipment_branch_inventory import index_graph,native_tee
from batch_native_path_coverage import collect as coverage
from third_arm_crossview_paths import native_component_profiles
from legacy_named_provider_inventory import current_plan_reader,require
from attach_anchored_floor_main_attributes import horizontal_domain

MODE='native_member_external_anchored_routes_v1'


def station(point,path,tol=.05):
    hits=[];offset=0.
    for a,b in zip(path,path[1:]):
        length=math.dist(a,b)
        if length>tol and _on(point,a,b,tol):
            hits.append(offset+math.dist(a,point))
        offset+=length
    require(hits and max(hits)-min(hits)<=tol,'point has no unique station on carrier')
    return sum(hits)/len(hits)


def clipped_fragments(edge,logical):
    """Clip only existing source fragments, retaining every intervening gap."""
    intervals=[]
    for path in edge['attribute_paths']:
        for a,b in zip(path,path[1:]):
            length=math.dist(a,b)
            if length<=.05:continue
            for i,(x,y)in enumerate(zip(logical,logical[1:])):
                if not _on(a,x,y,.05)and not _on(b,x,y,.05)and not _on(x,a,b,.05)and not _on(y,a,b,.05):continue
                size=math.dist(x,y)
                if size<=.05 or abs((a[0]-x[0])*(y[1]-x[1])-(a[1]-x[1])*(y[0]-x[0]))/size>.05 or abs((b[0]-x[0])*(y[1]-x[1])-(b[1]-x[1])*(y[0]-x[0]))/size>.05:continue
                u=[(y[k]-x[k])/size for k in(0,1)]
                low,high=sorted(sum((p[k]-x[k])*u[k]for k in(0,1))for p in(a,b));low=max(0.,low);high=min(size,high)
                if high-low<=.05:continue
                pts=[[x[k]+t*u[k]for k in(0,1)]for t in(low,high)]
                start=sum(math.dist(q,z)for q,z in zip(logical[:i],logical[1:i+1]))
                intervals.append((start+low,start+high,pts))
    intervals.sort(key=lambda r:r[:2]);require(intervals,'no existing source fragments in external scope')
    require(all(b[0]>=a[1]-.05 for a,b in zip(intervals,intervals[1:])),'overlapping source fragments require original member owner')
    size=sum(math.dist(a,b)for a,b in zip(logical,logical[1:]));gaps=[];last=0.;last_point=logical[0]
    for low,high,pts in intervals:
        if low-last>.05:gaps.append([last_point,pts[0]])
        last=high;last_point=pts[1]
    if size-last>.05:gaps.append([last_point,logical[-1]])
    return [p for _,_,p in intervals],gaps


def omission_evidence(edge,gaps,system):
    known=[]
    erratum=edge.get('source_drafting_erratum')
    if erratum and erratum.get('rule_scope')=='explicit_project_known_issue_only':
        known.append(dict(kind='existing_project_drafting_erratum',points=erratum['source_endpoints'],evidence=erratum))
    for row in edge.get('source_expert_riser_connections',[]):
        if row.get('system')==system:known.append(dict(kind='existing_expert_circle_interface',points=[row['center'],row['rim']],evidence=row))
    result=[]
    for gap in gaps:
        matches=[k for k in known if any(all(math.dist(a,b)<=.05 for a,b in zip(gap,points))for points in(k['points'],list(reversed(k['points']))))]
        require(len(matches)==1,'external source gap lacks its exact existing continuity evidence')
        result.append(copy.deepcopy(matches[0]))
    return result


def outward_candidates(plan,parent,interfaces,port):
    nodes={n['node_id']:n for n in parent['member_local_graph']['nodes']}
    node=nodes[port['member_node_id']];xy=[node['x'],node['y']]
    links=[(g,i)for g in interfaces['groups']for i in g['interfaces']if i['member_primary_node_id']==port['member_node_id']and i['axis_primary_T']==port['axis_node_id']]
    require(len(links)==1,'external member boundary differs from original cohort')
    group,interface=links[0]
    others=[i['plan_circle']['point']for i in group['interfaces']if i['member_primary_node_id']!=port['member_node_id']]
    require(len(others)==1,'member interval needs its independently proved other bracket')
    interior=others[0];result=[]
    for edge in plan['edges']:
        if edge['system']!=port['system']or group['plan_LINE']not in edge.get('source_handles',[]):continue
        if not any(_on(xy,a,b,.05)for path in edge['attribute_paths']for a,b in zip(path,path[1:])):continue
        path=edge['path_points'];cut=station(xy,path)
        for nid,points in [(edge['start_node_id'],[xy,*reversed([p for p in path if station(p,path)<cut-.05])]),(edge['end_node_id'],[xy,*[p for p in path if station(p,path)>cut+.05]])]:
            if len(points)<2 or sum((points[1][k]-xy[k])*(interior[k]-xy[k])for k in(0,1))>=-.05:continue
            fragments,gaps=clipped_fragments(edge,points)
            result.append(dict(plan_edge_id=edge['edge_id'],plan_remote=nid,logical_path=points,attribute_paths=fragments,gaps=gaps,
                source_omissions=omission_evidence(edge,gaps,port['system']),source_member_scope=group['primary_member_scope_id']))
    return result


def discover(plan,axis,parent,interfaces,provider,floor):
    pn,pe,pa=index_graph(plan);an,ae,aa=index_graph(axis);mapping=provider['ordinary_junction_mappings'][str(floor)];inverse={v:k for k,v in mapping.items()}
    require(len(inverse)==len(mapping),'ordinary anchor map is not injective')
    solved={r['axis_edge_id']for r in parent['records']};ports=[p for p in parent['original_external_ports']if p['axis_edge_id']not in solved];accepted=[];held=[]
    for port in ports:
        base=dict(port=copy.deepcopy(port),floor=floor,system=port['system']);routes=outward_candidates(plan,parent,interfaces,port)
        if len(routes)!=1:held.append(dict(base,reason='non_unique_outward_carrier_scope',routes=routes));continue
        route=routes[0];p=route['plan_remote'];a=port['other_axis_node'];base.update(route)
        if p not in pn or pn[p].get('node_type')not in('tee','physical_junction'):
            held.append(dict(base,reason='remote_source_endpoint_is_not_a_proved_T',existing_axis_anchor_plan_node=inverse.get(a)));continue
        if mapping.get(p,a)!=a or inverse.get(a,p)!=p:
            held.append(dict(base,reason='existing_remote_anchor_conflicts'));continue
        if any(nodes[n].get('floor')!=floor or nodes[n].get('review_required')is True or len(adj[n])!=3 or {e['system']for e in adj[n]}!={port['system']}for nodes,adj,n in[(pn,pa,p),(an,aa,a)]):
            held.append(dict(base,reason='remote_T_floor_system_or_degree_not_qualified'));continue
        links=[]
        for e in pa[p]:
            if e['edge_id']==route['plan_edge_id']:continue
            other=e['end_node_id']if e['start_node_id']==p else e['start_node_id']
            for edge in aa[a]:
                if edge['edge_id']==port['axis_edge_id']:continue
                target=edge['end_node_id']if edge['start_node_id']==a else edge['start_node_id']
                if mapping.get(other)==target:links.append(dict(plan_edge_id=e['edge_id'],axis_edge_id=edge['edge_id'],plan_anchor=other,axis_anchor=target))
        direct=mapping.get(p)==a
        if not direct and len(links)!=1:held.append(dict(base,reason='independent_adjacent_anchor_not_unique',links=links));continue
        if any(r['edge_id']==port['axis_edge_id']and r['has_existing_correspondence']for r in provider['records']):
            held.append(dict(base,reason='external_member_edge_already_mapped'));continue
        accepted.append(dict(base,axis_remote=a,direct_existing_ordinary_anchor=direct,independent_adjacent_anchors=links))
    # Whole-cohort injectivity is checked before any native adoption.
    for item in accepted:
        conflicts=[r for r in accepted if r is not item and(r['plan_remote']==item['plan_remote']and r['axis_remote']!=item['axis_remote']or r['axis_remote']==item['axis_remote']and r['plan_remote']!=item['plan_remote'])]
        require(not conflicts,'external route cohort has competing endpoint identities')
    return accepted,held


def scoped_components(profile,paths,edge_id):
    selected=[];excluded=[]
    for row in profile['records']:
        if row['edge_id']!=edge_id:continue
        points=[c['point_WCS'][:2]for c in row['native_contact']['flange_contacts']]
        inside=[any(_on(p,a,b,.05)for path in paths for a,b in zip(path,path[1:]))for p in points]
        require(len(set(inside))==1,'member scope boundary cuts a native component')
        (selected if all(inside)else excluded).append(copy.deepcopy(row))
    return dict(selected=selected,excluded_original_owners_retained=excluded,profile=dict(ball_valve=len(selected))if selected else{})


def ordered_components(scopes,paths):
    ordered={}
    for view,scope in scopes.items():
        rows=[]
        for row in scope['selected']:
            positions=[station(c['point_WCS'][:2],paths[view])for c in row['native_contact']['flange_contacts']]
            rows.append(dict(source_handle=row['source_handle'],station=sum(positions)/len(positions),
                source_signature=row['geometry']['signature'],original_owner_edge=row['edge_id']))
        rows.sort(key=lambda r:r['station'])
        require(all(b['station']-a['station']>.05 for a,b in zip(rows,rows[1:])),'ambiguous native component order')
        ordered[view]=rows
    require(len(ordered['plan'])==len(ordered['axis']),'native ordered component population differs')
    require(all(p['source_signature']==a['source_signature']for p,a in zip(ordered['plan'],ordered['axis'])),'native ordered component signatures differ')
    return [dict(plan=p,axis=a,physical_instance_identity_proved=False)for p,a in zip(ordered['plan'],ordered['axis'])]


def prove(rows,graphs,docs,provider,inputs,config,components,angles):
    indexes={v:index_graph(g)for v,g in graphs.items()};plan,axis=graphs['plan'],graphs['axis']
    targets={v:set()for v in graphs}
    for row in rows:
        targets['plan'].add(row['plan_edge_id']);targets['axis'].add(row['port']['axis_edge_id'])
        if not row['direct_existing_ordinary_anchor']:
            for link in row['independent_adjacent_anchors']:targets['plan'].add(link['plan_edge_id']);targets['axis'].add(link['axis_edge_id'])
    profiles={v:native_component_profiles(docs[v],graphs[v],components[v],sorted(targets[v]),'plan'if v=='plan'else'iso')for v in graphs}
    reader=current_plan_reader(config,inputs['plan_source']['sha256'],inputs['plan_graph']['sha256']);records=[]
    for row in rows:
        p,a=row['plan_remote'],row['axis_remote'];port=row['port'];pe=indexes['plan'][1][row['plan_edge_id']];ae=indexes['axis'][1][port['axis_edge_id']]
        tees=dict(plan=reader(docs['plan'],plan,p,inputs['plan_source']['sha256'],inputs['plan_graph']['sha256']),axis=native_tee(docs['axis'],axis,a,inputs['axis_source']['sha256'],inputs['axis_graph']['sha256']))
        require(all(len(proof['junctions'])==1 and len(proof['junctions'][0]['source_rays'])==3 for proof in tees.values()),'remote junction lacks native three-ray proof')
        private=copy.deepcopy(pe);private['attribute_paths']=copy.deepcopy(row['attribute_paths']);private['source_handles']=sorted(set(pe.get('source_handles',[])))
        native={}
        for v,g,e in [('plan',dict(plan,edges=[private]),private),('axis',axis,ae)]:
            native[v]=coverage(docs[v],g,[e['edge_id']],inputs[v+'_source']['sha256'],inputs[v+'_graph']['sha256'])
            require(not native[v]['unresolved']and all(s['status']=='single_source_line_covers'and len(s['witnesses'])==1 for e in native[v]['edges']for s in e['segments']),'external route lacks unique native source fragments')
        cp=dict(plan=scoped_components(profiles['plan'],private['attribute_paths'],pe['edge_id']),axis=scoped_components(profiles['axis'],ae['attribute_paths'],ae['edge_id']))
        require(cp['plan']['profile']==cp['axis']['profile'],'external member source component profile differs')
        axis_path=copy.deepcopy(ae['path_points'])
        if ae['start_node_id']!=port['axis_node_id']:axis_path.reverse()
        pairs=ordered_components(cp,dict(plan=row['logical_path'],axis=axis_path))
        token='MEMBER-EXTERNAL:'+hashlib.sha256(encode(dict(member=port['member_node_id'],plan_remote=p,axis_remote=a,axis_edge=ae['edge_id']))).hexdigest()[:16]
        records.append(dict(mapping_id=token,kind='member_to_ordinary_external_route',axis_edge_id=ae['edge_id'],plan_member_edge_id=token,plan_source_edge_id=pe['edge_id'],
            member_node_id=port['member_node_id'],plan_remote=p,axis_remote=a,member_axis_node=port['axis_node_id'],floor=row['floor'],system=row['system'],
            plan_attribute_paths=private['attribute_paths'],plan_logical_reading_path=row['logical_path'],source_omissions=row['source_omissions'],
            independent_adjacent_anchors=row['independent_adjacent_anchors'],direct_existing_ordinary_anchor=row['direct_existing_ordinary_anchor'],native_T=tees,native_paths=native,components=cp,ordered_native_component_pairs=pairs,
            mixed_attribute_source_split_required=True,whole_edge_DN_mm=None,whole_edge_physical_length_mm=None,attribute_adoption_allowed=False,physical_values_assigned=0,human_accepted=False))
        if row['direct_existing_ordinary_anchor']:continue
        link=row['independent_adjacent_anchors'][0];lineproof={};junctions={}
        horizontal_domain(axis,dict(iso_edges=[link['axis_edge_id']],system=row['system'],floor=row['floor'],iso_start=a,iso_end=link['axis_anchor']),angles)
        for v,eid,remote in [('plan',link['plan_edge_id'],link['plan_anchor']),('axis',link['axis_edge_id'],link['axis_anchor'])]:
            edge=indexes[v][1][eid];require(len(edge['attribute_paths'])==1,'adjacent anchored interval needs a separate fragmented-path owner')
            lineproof[v]=coverage(docs[v],graphs[v],[eid],inputs[v+'_source']['sha256'],inputs[v+'_graph']['sha256'])
            require(not lineproof[v]['unresolved']and all(s['status']=='single_source_line_covers'and len(s['witnesses'])==1 for e in lineproof[v]['edges']for s in e['segments']),'adjacent anchored interval native coverage differs')
            junctions[v]=(reader if v=='plan'else native_tee)(docs[v],graphs[v],remote,inputs[v+'_source']['sha256'],inputs[v+'_graph']['sha256'])
        profile={v:profiles[v]['profiles'][link[v+'_edge_id']]for v in graphs};require(profile['plan']==profile['axis'],'adjacent native component profiles differ')
        scopes={v:scoped_components(profiles[v],indexes[v][1][link[v+'_edge_id']]['attribute_paths'],link[v+'_edge_id'])for v in graphs}
        paths={}
        for v,start in [('plan',p),('axis',a)]:
            edge=indexes[v][1][link[v+'_edge_id']];paths[v]=copy.deepcopy(edge['path_points'])
            if edge['start_node_id']!=start:paths[v].reverse()
        pairs=ordered_components(scopes,paths)
        records.append(dict(mapping_id=token+':ADJACENT',kind='ordinary_anchored_neighbor',axis_edge_id=link['axis_edge_id'],plan_edge_id=link['plan_edge_id'],
            floor=row['floor'],system=row['system'],ordinary_endpoint_pairs=[[p,a],[link['plan_anchor'],link['axis_anchor']]],
            parent_member_external_mapping_id=token,native_paths=lineproof,native_other_T=junctions,components=profile,ordered_native_component_pairs=pairs,attribute_adoption_allowed=False,
            whole_edge_DN_mm=None,whole_edge_physical_length_mm=None,physical_values_assigned=0,human_accepted=False))
    return records,profiles
