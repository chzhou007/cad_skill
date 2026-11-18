"""Reapply native member interfaces through already confirmed main/detail aliases.

The projection is a separate reading domain. Original local graphs, old member
records and correspondence IDs stay intact. All native geometry algorithms are
inherited; this adapter supplies their missing confirmed coordinate relation.
"""
import collections,copy,hashlib,math
from confirm_crossview_paths import encode
from crossview_equipment_branch_inventory import index_graph
from batch_native_path_coverage import collect as coverage
from native_paired_caption_geometry import collect as captions
from compound_pipe_label_evidence import collect as labels
from compound_member_interfaces import group,scope_id
from native_line_path_evidence import _on,LAYERS
from axis_attribute_source_routing import collect as routing

MODE='native_confirmed_alias_circle_member_interfaces_v1'

def source_domains(row,directions):
    spans=[copy.deepcopy(x)for x in directions['records']if x['edge_id']==row['axis_edge_id']]
    kinds=collections.Counter(x['direction_class']for x in spans)
    if row['kind']=='primary_member_main':
        if set(kinds)!={'horizontal'}:raise ValueError('primary member is not a pure horizontal source domain')
    elif row['kind']=='lower_member_approach_with_local_rise':
        if kinds['horizontal']!=1 or kinds['vertical']<1 or set(kinds)!={'horizontal','vertical'}:raise ValueError('approach needs its own horizontal-domain reader')
    else:raise ValueError('unknown native interface role')
    native={(e['edge_id'],s.get('path_index',0),s['index']):s for e in row['native_axis_coverage']['edges']for s in e['segments']}
    for span in spans:
        witness=native.get((span['edge_id'],span['path_index'],span['segment_index']))
        if witness is None or witness['status']!='single_source_line_covers'or span['scope_points']!=[witness['start'],witness['end']]:raise ValueError('native direction-domain identity differs')
        span.update(source_line_coverage_checked=True,native_witnesses=copy.deepcopy(witness['witnesses']))
    return dict(records=spans,horizontal_nominal_mm=row['nominal_mm'],horizontal_complete_centerline_mm=row['plan_projection']['value_mm'],horizontal_source='corresponding_floor_plan_horizontal',vertical_DN_and_length_source='axis_11_native_vertical',whole_edge_nominal_mm=row['nominal_mm']if set(kinds)=={'horizontal'}else None,whole_edge_complete_centerline_mm=row['complete_horizontal_centerline_route_mm'],vertical_lengths_assigned=0)

def detail_bracket(doc,plan,anchor,system,source_hash,graph_hash):
    nodes,_,adj=index_graph(plan);at=anchor['plan_T'];options=[]
    for edge in adj[at]:
        other=edge['end_node_id']if edge['start_node_id']==at else edge['start_node_id']
        if edge['system']==system and nodes[other].get('subtype')=='unresolved_source_terminal':options.append((edge,other))
    if len(options)!=1:raise ValueError('confirmed detail outer anchor lacks one retained drawing extent')
    edge,other=options[0];circles=[]
    for circle in doc.modelspace().query('CIRCLE'):
        p=list(circle.ocs().to_wcs(circle.dxf.center))[:2]
        if circle.dxf.layer!=LAYERS[system]or not any(_on(p,a,b,.05)for path in edge['attribute_paths']for a,b in zip(path,path[1:])):continue
        if any(math.dist(p,[n['x'],n['y']])<=.05 for n in nodes.values()):continue
        circles.append(dict(handle=circle.dxf.handle,point=p,radius=circle.dxf.radius,layer=circle.dxf.layer))
    if len(circles)!=1 or circles[0]['radius']<=.05:raise ValueError('detail bracket circle is missing or competing')
    proof=coverage(doc,plan,[edge['edge_id']],source_hash,graph_hash)
    if any(s['status']!='single_source_line_covers'for e in proof['edges']for s in e['segments']):raise ValueError('detail extent needs a specific native path reader')
    return dict(source_circle=circles[0],source_edge=edge['edge_id'],retained_drawing_extent_end=other,native_visible_paths=proof,extra_tail_not_promoted_to_physical_pipe=True)

def provider_index(context):
    records=[r for key in('member_plan_runs','ordered_owner_plan_runs')for r in context.get(key,{}).get('records',[])]
    result={}
    for row in records:
        key=(row['floor'],row['system'],row['plan_edge_id'])
        if key in result:raise ValueError('member provider intervals overlap')
        result[key]=row
    return result

def collect(pd,ad,plan,axis,members,context,mappings,units,policy,hashes):
    before=encode(plan),encode(axis);pn,_,_=index_graph(plan);an,ae,_=index_graph(axis)
    cp=captions(ad);decl={r['handle']:r for r in labels(pd,hashes['plan_source'])['records']};providers=provider_index(context)
    anchors={(r['member_scope_id'],r['equipment_id']):r for r in members['anchors']}
    if len(anchors)!=len(members['anchors']):raise ValueError('confirmed alias anchors duplicate')
    buckets=collections.defaultdict(list)
    for row in members['records']:buckets[row['member_scope_id']].append(row)
    directions=routing(axis,policy);results=[];pending=[];records=[];nodes=[];edges=[];references=[]
    for gid,source_rows in sorted(buckets.items()):
        try:
            normalized=[];projected_nodes={};projected_edges=[];lower=None
            for old in source_rows:
                provider=providers.get((old['floor'],old['system'],old['plan_edge_id']))
                if not provider or any(provider.get(k)!=old[k]for k in('canonical_Ts','canonical_attribute_paths','equipment_anchors','plan_points','nominal_mm','shared_projected_source_LINE','source_view_aliases')):raise ValueError('current inherited member provider or confirmed alias changed')
                edge=ae[provider['axis_edge_id']];pairs=list(zip(old['canonical_Ts'],old['equipment_anchors'],old['plan_points']))
                if len(pairs)!=2 or len(old['canonical_Ts'])!=2 or {mappings[p]for p,_,_ in pairs}!={edge['start_node_id'],edge['end_node_id']}or old['system']!=edge['system']:raise ValueError('known member interval endpoint correspondence differs')
                cov=coverage(ad,axis,[edge['edge_id']],hashes['axis_source'],hashes['axis_graph']);segments=[s for e in cov['edges']for s in e['segments']]
                if not segments or any(s['status']!='single_source_line_covers'for s in segments):raise ValueError('known axis member path needs its native source reader')
                lines={s['witnesses'][0]['source_handle']for s in segments}
                if len(lines)!=1:raise ValueError('known member interval spans native LINEs')
                line=next(iter(lines));observations=[o for pair in cp['pairs']for o in pair['observations']if o['native_pipe']['source_LINE']==line]
                if not observations or len({o['text']['literal_level_key']for o in observations})!=1:raise ValueError('lower member native caption missing or competing')
                level=observations[0]['text']['literal_level_key'];scope=scope_id(old['shared_projected_source_LINE'],level,old['system'],old['floor'])
                if lower is not None and lower!=scope:raise ValueError('confirmed group crosses member scopes')
                lower=scope;aa=[]
                for nid,did,p in pairs:
                    anchor=anchors[(gid,did)]
                    if anchor['canonical_tee']!=nid or anchor['question_id']not in old['source_view_aliases']or anchor['plan_main_hit']['point']!=p or anchor['plan_main_hit']['source_handle']!=old['shared_projected_source_LINE']:raise ValueError('confirmed view alias projection differs')
                    n=dict(pn[nid],x=p[0],y=p[1],original_detail_point=[pn[nid]['x'],pn[nid]['y']],reading_projection_from_confirmed_alias=anchor['question_id'])
                    if nid in projected_nodes and projected_nodes[nid]!=n:raise ValueError('alias coordinate projection competes')
                    projected_nodes[nid]=n;aa.append(dict(equipment_id=did,plan_T=nid,axis_T=mappings[nid],plan_branch=anchor['canonical_branch'],confirmed_alias_question=anchor['question_id']))
                normalized.append(dict(floor=old['floor'],system=old['system'],member_scope_id=scope,source_member_scope_id=gid,plan_LINE=old['shared_projected_source_LINE'],axis_LINE=line,nominal_mm=old['nominal_mm'],anchors=aa,axis_edge_id=edge['edge_id'],mapping_id=provider.get('axis_mapping_id',provider.get('mapping_id')),axis_caption_crosscheck=observations[0],literal_level_key=level,plan_declarations=[dict(text_handle=old['compound_text_handle'],member=dict(nominal_mm=old['nominal_mm']))]))
                projected_edges.append(dict(edge_id=old['plan_edge_id'],start_node_id=old['canonical_Ts'][0],end_node_id=old['canonical_Ts'][1],system=old['system'],attribute_paths=[old['plan_points']],source_handles=[old['shared_projected_source_LINE']]))
            projected=dict(nodes=list(projected_nodes.values()),edges=projected_edges)
            projection_hash=hashlib.sha256(encode(projected)).hexdigest();reading_hashes=dict(hashes,original_plan_graph=hashes['plan_graph'],plan_graph=projection_hash)
            corridor=dict(source_LINE=normalized[0]['plan_LINE'],system=normalized[0]['system'],declarations=[decl[h]for h in sorted({x['compound_text_handle']for x in source_rows})])
            result=group(pd,ad,projected,axis,normalized,corridor,cp,units,policy['isometric_horizontal_directions_degrees'],reading_hashes)
            detail_aliases=[]
            for interface in result['interfaces']:
                detail=detail_bracket(pd,plan,interface['lower_anchor'],result['system'],hashes['plan_source'],hashes['plan_graph'])
                detail_aliases.append(dict(detail=detail,projected_main_circle=interface['plan_circle'],axis_primary_T=interface['axis_primary_T'],basis='complete_confirmed_equipment_alias_order_and_independent_native_bracket_interface_kernel'))
            result.update(source_alias_group_id=gid,reading_projection=projected,reading_projection_sha256=projection_hash,original_plan_graph_sha256=hashes['plan_graph'],detail_circle_aliases=detail_aliases)
            for row in result['records']:
                row.update(attribute_source_domains=source_domains(row,directions),source_alias_group_id=gid,original_plan_graph_sha256=hashes['plan_graph'],reading_projection_sha256=projection_hash)
            for nid,n in projected_nodes.items():
                nodes.append(dict(n,node_id=lower+':'+nid,source_drawing_node_id=nid,member_scope_id=lower,source_coordinate_domain='confirmed_main_plan_projection',axis_node_id=mappings[nid]))
            for old in source_rows:
                edges.append(dict(edge_id=lower+':'+old['plan_edge_id'],start_node_id=lower+':'+old['canonical_Ts'][0],end_node_id=lower+':'+old['canonical_Ts'][1],system=old['system'],member_scope_id=lower,source_drawing_edge_id=old['plan_edge_id'],attribute_paths=[old['plan_points']],coordinate_domain='confirmed_main_plan_projection',nominal_mm=old['nominal_mm'],plan_run_centerline_mm=old['horizontal_plan_run_centerline_mm'],installed_whole_length_mm=None))
            references.extend(dict(equipment_id=a['equipment_id'],system=result['system'],canonical_branch=a['canonical_branch'],canonical_tee=a['canonical_tee'],member_node_id=lower+':'+a['canonical_tee'],confirmed_alias_question=a['question_id'],unshown_connector_length_mm=None)for a in members['anchors']if a['member_scope_id']==gid)
            nodes.extend(result['new_member_nodes']);edges.extend(result['new_member_edges']);records.extend(result['records']);results.append(result)
        except (ValueError,KeyError)as exc:pending.append(dict(source_alias_group_id=gid,reason=str(exc)))
    node_index={n['node_id']:n for n in nodes}
    if len(node_index)!=len(nodes)or len({e['edge_id']for e in edges})!=len(edges):raise ValueError('member topology has competing nodes or edges')
    if any(e[k]not in node_index for e in edges for k in('start_node_id','end_node_id')):raise ValueError('member edge references missing node')
    if before!=(encode(plan),encode(axis)):raise ValueError('source local topology mutated')
    return dict(mode=MODE,groups=results,records=records,pending=pending,member_local_graph=dict(scope='confirmed_alias_lower_member_mains_and_native_circle_primary_interfaces',nodes=nodes,edges=edges,equipment_branch_references=references,external_ports=[p for g in results for p in g['external_ports']],global_topology_complete=False,calculation_ready=False,human_accepted=False),counts=dict(cohorts_screened=len(buckets),cohorts_qualified=len(results),new_axis_correspondences=len(records),primary_member_mains=sum(r['kind']=='primary_member_main'for r in records),mixed_horizontal_domain_approaches=sum(r['kind']!='primary_member_main'for r in records),original_detail_circle_aliases=sum(len(g['detail_circle_aliases'])for g in results)),original_local_graphs_mutated=False,ordinary_junction_mapping_extended=False,existing_member_providers_preserved=True,DN_used_for_mapping=False,vertical_attributes_assigned_from_plan=0,installed_lengths_assigned=0,net_pipe_lengths_assigned=0,human_accepted=False)
