"""Reuse ordered-main branch rules for native circle-glyph drawing interfaces.

The sole type projection is a temporary reader adapter. It never changes the
source graph, creates a physical device, or infers a remote endpoint identity.
"""
import collections,copy,hashlib,math
from cad_ceiling_native_rules import match_out_of_plane_symbol
from crossview_equipment_branch_inventory import index_graph,native_tee
from ordered_anchor_branch_paths import outward,branch_snapshot
from batch_native_path_coverage import collect as coverage
from current_plan_crossover_path_reapplication import audit as plan_path_coverage
from native_drawing_marker_ports import collect as marker_ports
from native_plan_projection_lengths import lengths
from legacy_named_provider_inventory import require
from confirm_crossview_paths import encode
from native_line_path_evidence import LAYERS

MODE='native_anchored_terminal_branch_context_reapplication_v1'

def terminal_geometry(doc,node,edge):
    require(node.get('subtype')=='out_of_plane_interface'and node.get('node_type')=='virtual_equipment','native circle interface role required')
    circle=doc.entitydb.get(node.get('source_handle'));handles=node.get('source_handles',[])
    require(circle is not None and circle in doc.modelspace()and circle.dxftype()=='CIRCLE'and circle.dxf.layer==LAYERS[edge['system']], 'typed native interface circle missing')
    require(len(set(handles))==len(handles)==5 and circle.dxf.handle in handles,'complete original interface glyph inventory required')
    xy=[float(circle.dxf.center.x),float(circle.dxf.center.y)]
    require(math.dist(xy,[node['x'],node['y']])<=.05,'native interface position changed')
    glyphs=[]
    for h in handles:
        if h==circle.dxf.handle:continue
        line=doc.entitydb.get(h)
        require(line is not None and line in doc.modelspace()and line.dxftype()=='LINE'and line.dxf.layer=='空调立管、水平支管','native interface LINE family differs')
        glyphs.append(dict(handle=h,a=list(line.dxf.start)[:2],b=list(line.dxf.end)[:2]))
    hit=match_out_of_plane_symbol(dict(center=xy,radius=float(circle.dxf.radius)),glyphs)
    require(hit is not None and {r['handle']for group in hit for r in group}==set(handles)-{circle.dxf.handle},'native interface glyph does not match original kernel')
    return dict(source_circle=circle.dxf.handle,source_handles=sorted(handles),native_XYZ=list(circle.dxf.center),native_radius=float(circle.dxf.radius),
        original_matcher='cad_ceiling_native_rules.match_out_of_plane_symbol',physical_port_verified=False,remote_equipment_identity_inferred=False)

def source_terminal_outward(doc,graph,anchor,blocked,system,floor):
    nodes,edges,adj=index_graph(graph);options=[e for e in adj[anchor]if e['edge_id']not in blocked]
    require(len(options)==1,'main anchor has no unique third arm')
    e=options[0];peer=e['end_node_id']if e['start_node_id']==anchor else e['start_node_id'];node=nodes.get(peer,{})
    require(node.get('floor')==floor and len(adj[peer])==1 and node.get('system')==system and node.get('review_required')is not True,'circle interface is not a unique same-floor typed drawing endpoint')
    geometry=terminal_geometry(doc,node,e)
    reading=copy.deepcopy(graph);projected=next(n for n in reading['nodes']if n['node_id']==peer)
    projected['subtype']='external_system_interface'
    route=outward(reading,anchor,blocked,system,floor)
    require(route['terminal_id']==peer and route['edges']==[e['edge_id']],'original outward reader chose another source path')
    return route,geometry,dict(node_id=peer,original_subtype=node['subtype'],reader_subtype='external_system_interface',scope='temporary drawing-interface reader schema only',source_graph_mutated=False)

def discover(parent,provider,graphs):
    require(parent.get('complete_corrected_parent_replayed')is True and parent.get('all_historical_main_roles_reapplied')is True,'complete current parent native evidence required')
    owner={r['edge_id']:r for r in provider['records']};mapping=provider['ordinary_junction_mappings'];groups=collections.defaultdict(list);axis_edges=index_graph(graphs['iso'])[1]
    for row in parent['records']:groups[row['floor'],row['system']].append(row)
    candidates=[];pending=[];used={v:set()for v in('plan','iso')}
    for (floor,system),rows in sorted(groups.items()):
        require(len(mapping[str(floor)])==len(set(mapping[str(floor)].values())),'ordinary anchor identities collapse')
        require(len({r['axis_edge_id']for r in rows})==len(rows),'duplicate source main correspondence')
        blocked=dict(plan={r['plan_edge_id']for r in rows},iso={r['axis_edge_id']for r in rows});inc=collections.defaultdict(list)
        for r in rows:
            for pn,an in r['original_correspondence']['ordinary_endpoint_pairs']:inc[pn,an].append(r)
        for (pn,an),relations in sorted(inc.items()):
            if len(relations)!=2:continue
            base=dict(floor=floor,system=system,plan_anchor=pn,axis_anchor=an,blocked={v:sorted(es)for v,es in blocked.items()},known_main_mapping_ids=[r['mapping_id']for r in relations])
            try:
                require(mapping[str(floor)].get(pn)==an,'ordinary anchor is absent from adopted parent')
                adj={v:index_graph(graphs[v])[2][n]for v,n in [('plan',pn),('iso',an)]}
                off={v:[e for e in adj[v]if e['edge_id']not in blocked[v]]for v in graphs}
                require(all(len(es)==1 for es in off.values()),'unique off-main branch required in both views')
                pe,ae=off['plan'][0],off['iso'][0]
                require(pe['system']==ae['system']==system,'branch system differs')
                require(not owner[ae['edge_id']]['has_existing_correspondence'],'old axis branch provider must be preserved')
                require(not any(pe['edge_id']in o['plan_edges']for record in provider['records']for o in record['correspondence_observations']if o.get('floor',axis_edges[record['edge_id']].get('floor_start',floor))==floor),'old plan branch provider must be preserved')
                for relation in relations:
                    require(any(o['mapping_id']==relation['mapping_id']and o['plan_edges']==[relation['plan_edge_id']]for o in owner[relation['axis_edge_id']]['correspondence_observations']),'main relation is not independently adopted')
                for view,e in [('plan',pe),('iso',ae)]:
                    require(e['edge_id']not in used[view],'competing branch ownership')
                key=hashlib.sha256(encode(dict(floor=floor,system=system,plan=pe['edge_id'],axis=ae['edge_id'],anchors=[pn,an]))).hexdigest()[:16]
                row=dict(base,mapping_id='ANCHORED-INTERFACE-F'+str(floor)+'-'+key,plan_edge_id=pe['edge_id'],axis_edge_id=ae['edge_id'])
                candidates.append(row)
                for view,e in [('plan',pe),('iso',ae)]:used[view].add(e['edge_id'])
            except ValueError as exc:pending.append(dict(base,reason=str(exc)))
    return candidates,pending

def qualify(row,graphs,docs,hashes,reader,plan_DN,units,marker_cache):
    routes={};checks={}
    routes['plan'],glyph,projection=source_terminal_outward(docs['plan'],graphs['plan'],row['plan_anchor'],set(row['blocked']['plan']),row['system'],row['floor'])
    routes['iso']=outward(graphs['iso'],row['axis_anchor'],set(row['blocked']['iso']),row['system'],row['floor'])
    require(routes['iso']['terminal_kind']=='drawing_marker_interface','axis branch is not a separate original drawing interface')
    nid=routes['iso']['terminal_id']
    if nid not in marker_cache:marker_cache[nid]=marker_ports(docs['iso'],graphs['iso'],nid,hashes['iso']['source_sha256'],hashes['iso']['graph_sha256'])
    ports=[p for p in marker_cache[nid]['records']if p['edge_id']==row['axis_edge_id']and p['system']==row['system']]
    require(len(ports)==1,'axis typed drawing branch port differs')
    for view in graphs:
        require(routes[view]['edges']==[row['plan_edge_id'if view=='plan'else'axis_edge_id']],'third arm traverses another edge')
        h=hashes[view]
        path=(plan_path_coverage(docs[view],graphs[view],row['plan_edge_id'],row['plan_anchor'],h['source_sha256'],h['graph_sha256'],reader)
              if view=='plan'else coverage(docs[view],graphs[view],routes[view]['edges'],h['source_sha256'],h['graph_sha256']))
        for e in path['edges']:
            for seg in e['segments']:
                if view=='iso'and seg['index']==ports[0]['display_segment_index']:continue
                require(seg['status']=='single_source_line_covers','native source branch fragment is not uniquely supported')
        anchor=row['plan_anchor'if view=='plan'else'axis_anchor']
        tee=(reader if view=='plan'else native_tee)(docs[view],graphs[view],anchor,h['source_sha256'],h['graph_sha256'])
        checks[view]=dict(native_T=tee,native_path=path,snapshot=branch_snapshot(graphs[view],routes[view]['edges']))
    dn=copy.deepcopy(plan_DN[row['plan_edge_id']]);edge=index_graph(graphs['plan'])[1][row['plan_edge_id']]
    require(dn['system']==row['system']and dn['scope_paths']==edge['attribute_paths'],'current local DN has another source scope')
    metric=lengths(graphs['plan'],checks['plan']['native_path'],dict(plan_edges=routes['plan']['edges'],system=row['system']),units)
    return dict(row,routes=routes,native_checks=checks,plan_terminal_glyph=glyph,temporary_reader_projection=projection,axis_drawing_port=copy.deepcopy(ports[0]),
        plan_DN_record=dn,plan_horizontal_projection=metric,source_scope='source_checked_third_arm_drawing_context_not_remote_identity',physical_port_verified=False,
        remote_equipment_identity_inferred=False,whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,vertical_values_assigned=0,
        source_graphs_mutated=False,human_accepted=False)
