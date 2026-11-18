"""Replay explicitly confirmed hidden-overlap contacts for downstream DN roles.

The original repair owns connectivity. Its display connector is not a physical
pipe or a native main ray. Reuse that repair on its real immutable input, then
read the two current native main arms and the original branch orientation.
"""
import csv,math
from pathlib import Path
from confirm_crossview_paths import load,sha
from repair_confirmed_overlapping_branches import apply
from native_line_path_evidence import LAYERS,_on


def roots(graph):
    root=graph.get('userConfirmedOverlappingBranches');seen=set()
    while isinstance(root,dict):
        if id(root)in seen:raise ValueError('cyclic confirmed-overlap owner history')
        seen.add(id(root));yield root;root=root.get('previous_repair')


def replay(doc,source_hash,entry):
    required={'policy','evidence_manifest','parent_graph','parent_devices'}
    if set(entry)!=required:raise ValueError('complete original confirmed-overlap owner inputs required')
    for spec in entry.values():
        if sha(spec['path'])!=spec['sha256']:raise ValueError('original confirmed-overlap owner input changed')
    policy=load(entry['policy']['path']);evidence=load(entry['evidence_manifest']['path']);parent=load(entry['parent_graph']['path'])
    if (policy.get('confirmed_by')!='user'or policy.get('source_sha256')!=source_hash
        or policy.get('graph_sha256')!=entry['parent_graph']['sha256']
        or policy.get('devices_sha256')!=entry['parent_devices']['sha256']
        or policy.get('evidence_manifest_sha256')!=entry['evidence_manifest']['sha256']):
        raise ValueError('original confirmed-overlap policy/source binding differs')
    if not evidence.get('items')or any(sha(item['path'])!=item['sha256']for item in evidence['items']):
        raise ValueError('original confirmed-overlap user evidence missing or changed')
    with Path(entry['parent_devices']['path']).open(encoding='utf-8-sig',newline='')as stream:devices=list(csv.DictReader(stream))
    graph,audit=apply(doc,parent,devices,policy,source_hash,entry['parent_graph']['sha256'],entry['evidence_manifest']['sha256'])
    return graph,audit,policy


def collect(doc,graph,node_id,source_hash,graph_hash,entries):
    nodes={n['node_id']:n for n in graph['nodes']};node=nodes[node_id]
    incident=[e for e in graph['edges']if node_id in(e.get('start_node_id'),e.get('end_node_id'))]
    if (graph.get('metadata',{}).get('source_sha256')!=source_hash or node.get('node_type')not in('tee','physical_junction')
        or node.get('review_required')is True or len(incident)!=3 or len({e['edge_id']for e in incident})!=3
        or node.get('system')not in LAYERS or {e.get('system')for e in incident}!={node['system']}):
        raise ValueError('confirmed-overlap current T/source incidence differs')
    meta=node.get('user_confirmed_overlap_connection',{})
    candidates=[]
    for entry in entries:
        policy=load(entry['policy']['path'])
        if (policy.get('graph_sha256')==meta.get('source_graph_sha256')
            and entry['evidence_manifest']['sha256']==meta.get('user_evidence_manifest_sha256')):candidates.append(entry)
    if len(candidates)!=1:raise ValueError('confirmed overlap needs one original immutable owner')
    entry=candidates[0];original,audit,policy=replay(doc,source_hash,entry)
    records=[r for r in audit['records']if r['tee']==node_id and r['circle_handle']==meta.get('circle_handle')]
    historical=[root for root in roots(graph)if root.get('input_graph_sha256')==policy['graph_sha256']
        and root.get('source_sha256')==source_hash and root.get('evidence_manifest_sha256')==entry['evidence_manifest']['sha256']]
    if len(records)!=1 or len(historical)!=1 or records[0]not in historical[0].get('records',[]):
        raise ValueError('current confirmed overlap record differs from actual original repair')
    record=records[0];old_node=next(n for n in original['nodes']if n['node_id']==node_id)
    old_branch=next(e for e in original['edges']if e['edge_id']==record['branch_edge'])
    branch=next((e for e in incident if e['edge_id']==record['branch_edge']),None)
    connection=next(c for c in policy['connections']if c['circle_handle']==meta['circle_handle'])
    point=[node['x'],node['y']];anchor=connection['display_route'][0]
    if (meta!=old_node.get('user_confirmed_overlap_connection')or branch is None
        or branch.get('user_confirmed_overlap_connection')!=old_branch.get('user_confirmed_overlap_connection')
        or meta.get('route_is_physical')is not False or meta.get('physical_length')!='unknown'
        or branch.get('physical_length')!='unknown'or branch.get('path_length_complete')is not False
        or point!=[old_node['x'],old_node['y']]or node['floor']!=old_node['floor']or node['system']!=old_node['system']):
        raise ValueError('current confirmed overlap scope/unknown connector differs')
    circle,main,native_branch=[doc.entitydb.get(connection[k])for k in('circle_handle','main_handle','branch_handle')]
    if circle is None or main is None or native_branch is None:raise ValueError('confirmed overlap native entities missing')
    if connection['pipe_layer']!=LAYERS[node['system']]:raise ValueError('confirmed overlap pipe service differs')
    rays=[]
    for edge in incident:
        at=anchor if edge is branch else point;touch=[]
        for path in edge.get('attribute_paths',[]):
            for a,b in zip(path,path[1:]):
                if math.dist(a,at)<=.05 and math.dist(b,at)>.05:touch.append((a,b))
                elif math.dist(b,at)<=.05 and math.dist(a,at)>.05:touch.append((b,a))
        if len(touch)!=1:raise ValueError('confirmed overlap current native ray missing or ambiguous')
        a,b=touch[0]
        hits=[line.dxf.handle for line in doc.modelspace().query('LINE')if line.dxf.layer==LAYERS[node['system']]
            and _on(a,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05)
            and _on(b,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05)]
        expected=connection['branch_handle']if edge is branch else connection['main_handle']
        if hits!=[expected]or expected not in edge.get('source_handles',[]):raise ValueError('confirmed overlap native ray owner differs or is ambiguous')
        length=math.dist(a,b);direction=[(b[i]-a[i])/length for i in(0,1)]
        rays.append(dict(edge_id=edge['edge_id'],source_line_handle=expected,graph_segment=[a,b],direction=direction,
            scope='confirmed_original_native_branch_orientation_for_DN_role_only'if edge is branch else'native_current_main_LINE_arm',
            physical_connector_length_mm=None))
    main_rays=[r for r in rays if r['edge_id']!=branch['edge_id']]
    center_contacts=[line.dxf.handle for line in doc.modelspace().query('LINE')if line.dxf.layer==LAYERS[node['system']]
        and _on(point,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05)]
    if center_contacts!=[connection['main_handle']]:raise ValueError('unaccounted same-service LINE at confirmed overlap circle center')
    if sum(x*y for x,y in zip(main_rays[0]['direction'],main_rays[1]['direction']))>-math.cos(math.radians(1)):
        raise ValueError('confirmed overlap native main arms are not a through pair')
    branch_ray=next(r for r in rays if r['edge_id']==branch['edge_id'])
    if abs(sum(x*y for x,y in zip(branch_ray['direction'],main_rays[0]['direction'])))>=math.cos(math.radians(10)):
        raise ValueError('confirmed overlap branch orientation cannot establish a distinct DN branch role')
    xyz=dict(circle_center=list(circle.dxf.center),main=[list(main.dxf.start),list(main.dxf.end)],branch=[list(native_branch.dxf.start),list(native_branch.dxf.end)])
    if any(not math.isfinite(v)for p in [xyz['circle_center'],*xyz['main'],*xyz['branch']]for v in p):raise ValueError('nonfinite confirmed overlap native coordinates')
    return dict(status='original_confirmed_overlap_owner_and_current_native_main_roles_replayed',
        source_sha256=source_hash,graph_sha256=graph_hash,junctions=[dict(node_id=node_id,system=node['system'],position=point,source_rays=rays)],
        original_owner=entry,original_connection_mode=connection['connection_mode'],original_native_XYZ=xyz,
        original_owner_replayed=True,branch_role_basis='original_user_confirmed_branch_on_same_service_native_main',
        source_branch_anchor=anchor,display_route_is_physical=False,hidden_connection_length_mm=None,
        graph_mutated=False,physical_values_assigned=0,physical_ports_verified=False,human_accepted=False,hil_ready=False)


def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name))for name in(Path(__file__).name,'repair_confirmed_overlapping_branches.py',
        'repair_confirmed_circle_junctions.py','native_line_path_evidence.py')}
