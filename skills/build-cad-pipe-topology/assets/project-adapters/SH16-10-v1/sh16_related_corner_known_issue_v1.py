"""SH16-10-only continuation of ERR-817809; never a general circle rule.

The original marked controls stay immutable. The right-return case is native
source checked against those controls, not represented as a new expert answer.
"""
import argparse,copy,csv,io,json,math,sys
from collections import Counter
from pathlib import Path
R=Path(__file__).resolve().parent;ROOT=R.parents[1]
sys.path.insert(0,str(ROOT/'skills/build-cad-pipe-topology/scripts'))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from edge_endpoint_semantics import reconcile
from inherited_wave_pair_continuity import verify_output as verify_wave,csv_bytes
from native_line_path_evidence import LAYERS

MODE='SH16_10_source_checked_related_corner_known_issue_v1'
SOURCE_SHA='4008f96373fe154c5ad1de1892f6b1dbd0e07ff9582267f819f8a66a7ba268e1'
ISSUE_SHA='c9f569f24e811232bddee4eaffae3fd588cef2111eca5e97b194ad96da7b54f9'
CONTEXT_SHA='a79197d868294be0cf4adb361df39b2e38f9bedc4ea6a13d2e446d0ba62c0e2a'
PARENT_SHA='bb3f4642b9aad5cc86db4117af9864fed6a3c03c5c8c3ba49d3b63f40f46c371'
CASE=dict(system='return',circle='15224',nodes=['UT0054','UT0056'],edges=['E0007','E0001'],lines=['B405','B408'])
CONTROLS=[dict(system='return',circle='15221',nodes=['UT0049','UT0055'],lines=['B407','B3E1']),
          dict(system='supply',circle='15222',nodes=['UT0148','UT0153'],lines=['B404','B3E2'])]


def point_line_distance(point,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];d=dx*dx+dy*dy
    t=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/d)) if d else 0
    return math.hypot(point[0]-a[0]-t*dx,point[1]-a[1]-t*dy)


def native_corner(doc,spec,points):
    circle=doc.entitydb[spec['circle']]
    if (circle.dxftype()!='CIRCLE' or circle not in doc.modelspace() or circle.dxf.layer!=LAYERS[spec['system']]
        or tuple(circle.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.) or abs(circle.dxf.radius-100)>.05):raise ValueError('SH16 known-issue circle geometry differs')
    centre=list(circle.dxf.center);ends=[];directions=[]
    for handle,point in zip(spec['lines'],points):
        entity=doc.entitydb[handle]
        if entity.dxftype()!='LINE' or entity not in doc.modelspace() or entity.dxf.layer!=LAYERS[spec['system']]:raise ValueError('known-issue typed source line differs')
        a,b=list(entity.dxf.start),list(entity.dxf.end)
        if math.dist(a[:2],point)>math.dist(b[:2],point):a,b=b,a
        if math.dist(a[:2],point)>.05 or abs(a[2]-centre[2])>.05:raise ValueError('known-issue native endpoint or Z differs')
        length=math.dist(a[:2],b[:2])
        if length<300:raise ValueError('known-issue source ray is too short')
        ends.append(a);directions.append([(b[i]-a[i])/length for i in (0,1)])
    radius=circle.dxf.radius
    if math.dist(ends[0],centre)>.05 or abs(math.dist(ends[1],centre)-radius)>.05:raise ValueError('known-issue centre/rim endpoints differ')
    rim=[(ends[1][i]-centre[i])/radius for i in (0,1)]
    if abs(sum(a*b for a,b in zip(directions[0],directions[1])))>1e-8 or sum(a*b for a,b in zip(rim,directions[1]))<1-1e-8:
        raise ValueError('known-issue source rays are not the supported orthogonal corner')
    contacts=[];opposite=[]
    for entity in doc.modelspace().query('LINE'):
        if entity.dxf.layer not in LAYERS.values():continue
        distance=point_line_distance(centre[:2],list(entity.dxf.start)[:2],list(entity.dxf.end)[:2])
        if distance<=radius+.05:
            (contacts if entity.dxf.layer==LAYERS[spec['system']] else opposite).append(entity.dxf.handle)
    if set(contacts)!=set(spec['lines']) or opposite:raise ValueError('known-issue corner has additional or opposite-system pipe contacts')
    return dict(circle_handle=spec['circle'],system=spec['system'],radius_drawing_units=radius,
        source_pipe_handles=spec['lines'],native_circle_center=centre,native_endpoints=ends,source_ray_directions=directions,
        coordinate_relation='one_source_endpoint_at_redundant_circle_center_other_at_rim',
        global_circle_rule=False,physical_connector_length_mm=None)


def merge_case(graph,rows,evidence):
    if graph.get('metadata',{}).get('source_sha256')!=SOURCE_SHA:raise ValueError('project extension is SH16-10 only')
    g=copy.deepcopy(graph);prior_rows=copy.deepcopy(rows);rows=copy.deepcopy(rows);nodes={n['node_id']:n for n in g['nodes']};edges={e['edge_id']:e for e in g['edges']}
    left,right=(edges[eid] for eid in CASE['edges']);a,b=(nodes[nid] for nid in CASE['nodes'])
    for edge,node,handle in zip((left,right),(a,b),CASE['lines']):
        if (node.get('subtype')!='unresolved_source_terminal' or node.get('system')!=CASE['system'] or node.get('floor')!=3
            or edge['system']!=CASE['system'] or handle not in edge['source_handles']
            or sum(node['node_id'] in (e.get('start_node_id'),e.get('end_node_id')) for e in edges.values())!=1):raise ValueError('known-issue current leaf differs')
        if any(k in edge for k in ('cross_view_attributes','plan_segment_attributes','axis_riser_attributes','pipe_diameter','source_segment_dimensions')):
            raise ValueError('known-issue affected attributes need explicit reconciliation')
    allowed={'edge_id','start_node_id','end_node_id','edge_type','system','start_floor','end_floor','path','attribute_paths','path_length',
        'source_handles','equipment_counts','equipment_names','path_points','endpoint_semantics','path_length_complete','path_length_scope',
        'connection_mode','source_flexible_joints','physical_length','source_drafting_erratum','start_port_id','end_port_id'}
    if (set(left)|set(right))-allowed:raise ValueError('unhandled field in project corner extension')
    def other(edge,nid):return edge['end_node_id'] if edge['start_node_id']==nid else edge['start_node_id']
    start,end=other(left,a['node_id']),other(right,b['node_id'])
    if start==end or any(nodes[nid]['node_type']!='tee' or nodes[nid]['system']!='return' for nid in (start,end)):raise ValueError('project corner changes physical endpoint roles')
    def paths_from(edge,nid):
        paths=copy.deepcopy(edge['attribute_paths'])
        return paths if edge['start_node_id']==nid else [list(reversed(path)) for path in reversed(paths)]
    paths=paths_from(left,start)+paths_from(right,b['node_id']);flat=[point for path in paths for point in path]
    merged=copy.deepcopy(left);merged.update(start_node_id=start,end_node_id=end,path=copy.deepcopy(flat),path_points=copy.deepcopy(flat),attribute_paths=paths,
        source_handles=list(dict.fromkeys(left['source_handles']+right['source_handles'])),path_length=sum(math.dist(a,b) for p in paths for a,b in zip(p,p[1:])),
        path_length_complete=False,path_length_scope='source_drawn_pipe_only_SH16_related_corner_and_existing_omissions_unknown',physical_length='unknown',
        connection_mode='source_checked_SH16_10_related_project_erratum_unreviewed',
        equipment_names=left['equipment_names']+right['equipment_names'],equipment_counts=dict(Counter(left['equipment_counts'])+Counter(right['equipment_counts'])))
    for key in ('start_port_id','end_port_id'):merged.pop(key,None)
    if left.get('start_port_id'):merged['start_port_id']=left['start_port_id']
    if right.get('start_port_id'):merged['end_port_id']=right['start_port_id']
    if right.get('source_flexible_joints'):merged['source_flexible_joints']=copy.deepcopy(left.get('source_flexible_joints',[])+right['source_flexible_joints'])
    merged['source_SH16_related_corner']=dict(project_scope='SH16-10',source_sha256=SOURCE_SHA,case='right_return_15224',
        original_issue_sha256=ISSUE_SHA,original_marked_scope_inherited=False,new_case_expert_confirmed=False,
        source_evidence=copy.deepcopy(evidence),physical_length_mm=None)
    snapshots=[copy.deepcopy(left),copy.deepcopy(right)];edges[left['edge_id']]=merged;del edges[right['edge_id']]
    for nid in CASE['nodes']:del nodes[nid]
    for row in rows:
        if row['edge_id']==right['edge_id']:row['edge_id']=left['edge_id']
    if Counter(r['device_name'] for r in rows)!=Counter(r['device_name'] for r in prior_rows) or len({r['device_name'] for r in rows})!=len(rows):raise ValueError('canonical component identities differ')
    if any({key:value for key,value in row.items() if key!='edge_id'}!={key:value for key,value in before.items() if key!='edge_id'} for before,row in zip(prior_rows,rows)):
        raise ValueError('project corner changed component source metadata')
    for edge in edges.values():
        assigned=[r for r in rows if r['edge_id']==edge['edge_id']]
        if Counter(r['device_name'] for r in assigned)!=Counter(edge['equipment_names']) or Counter(r['equipment_type'] for r in assigned)!=Counter(edge['equipment_counts']):raise ValueError('canonical corner component assignment differs')
    if any(row['edge_id'] not in edges for row in rows):raise ValueError('orphan corner component')
    g['nodes']=list(nodes.values());g['edges']=list(edges.values());g,_=reconcile(g)
    g['sourceSH16RelatedCornerKnownIssue']=dict(mode=MODE,project_scope='SH16-10',source_sha256=SOURCE_SHA,input_graph_sha256=PARENT_SHA,
        original_issue_sha256=ISSUE_SHA,original_context_sha256=CONTEXT_SHA,new_case_expert_confirmed=False,general_circle_rule=False,
        retired_node_snapshots=[copy.deepcopy(n) for n in graph['nodes'] if n['node_id'] in CASE['nodes']],parent_edge_snapshots=snapshots,
        edge_id_mapping={right['edge_id']:left['edge_id']},native_evidence=copy.deepcopy(evidence),physical_lengths_assigned=0,human_accepted=False)
    g['derivedEvidenceInvalidation']=dict(previous=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),
        reason='source-checked SH16-only related known-issue corner, no general circle rule',affected_edges=CASE['edges'],affected_physical_nodes=[start,end],
        recompute=['source_comparison','diameter_inheritance','crossview_mapping','attribute_fusion','human_acceptance'])
    g['metadata'].update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_SH16_related_corner_known_issue')
    return g,rows


def compute(paths):
    if sha(paths['source'])!=SOURCE_SHA or sha(paths['issue'])!=ISSUE_SHA or sha(paths['context'])!=CONTEXT_SHA or sha(paths['graph'])!=PARENT_SHA:
        raise ValueError('SH16 known-issue project/source/context/parent identity differs')
    if Path(paths['devices']).resolve()!=Path(paths['graph']).resolve().parent/'assigned_edge_device_instances.csv':raise ValueError('canonical SH16 parent component table required')
    parent=verify_wave(Path(paths['graph']).parent)
    if parent['output_graph_sha256']!=PARENT_SHA:raise ValueError('native wave parent differs')
    issue=load(paths['issue']);context=load(paths['context']);graph=load(paths['graph'])
    original=graph.get('sourceDraftingErrata',{})
    if original.get('issue_sha256')!=ISSUE_SHA or original.get('source_sha256')!=SOURCE_SHA or original.get('project_scope')!='SH16-10':raise ValueError('original SH16-only known-issue ancestry differs')
    if issue['issue']['id']!='8178093e-d251-406e-81ce-bad68328a204':raise ValueError('wrong original project issue')
    doc,preflight=read_source(paths['source']);old={n['node_id']:n for n in context['nodes']};nodes={n['node_id']:n for n in graph['nodes']}
    controls=[native_corner(doc,spec,[[old[nid]['x'],old[nid]['y']] for nid in spec['nodes']]) for spec in CONTROLS]
    for spec in CONTROLS:
        if not set(spec['nodes'])<=set(issue['issue']['nodes']):raise ValueError('control is outside original marked expert scope')
    evidence=native_corner(doc,CASE,[[nodes[nid]['x'],nodes[nid]['y']] for nid in CASE['nodes']])
    protected=dict(system='supply',circle='15223',lines=['B402','B409'])
    circ=doc.entitydb['15223'];centre=list(circ.dxf.center);rim=list(doc.entitydb['B409'].dxf.start)
    supply_evidence=native_corner(doc,protected,[centre[:2],rim[:2]])
    existing=[e for e in graph['edges'] if set(protected['lines'])<=set(e['source_handles'])]
    if len(existing)!=1:raise ValueError('known same-form supply protection case differs')
    with Path(paths['devices']).open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    result,assigned=merge_case(graph,rows,evidence)
    proof=dict(source_preflight=preflight,original_issue_note=issue['issue']['note'],original_marked_controls=controls,
        new_right_return_native_evidence=evidence,protected_already_connected_supply=dict(edge_id=existing[0]['edge_id'],native_evidence=supply_evidence),
        nodes_before=len(graph['nodes']),nodes_after=len(result['nodes']),edges_before=len(graph['edges']),edges_after=len(result['edges']),
        canonical_components=len(rows),new_case_expert_confirmed=False,general_circle_rule=False,physical_lengths_assigned=0)
    return result,assigned,fields,proof


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'SH16-related-corner-known-issue-audit.json')
    if receipt['mode']!=MODE or receipt['owner_sha256']!=sha(__file__):raise ValueError('SH16 project owner changed')
    if any(sha(item['path'])!=item['sha256'] for item in receipt['inputs'].values()):raise ValueError('SH16 project corner inputs changed')
    graph,rows,fields,proof=compute({key:item['path'] for key,item in receipt['inputs'].items()})
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or proof!=receipt['proof'] or csv_bytes(fields,rows)!=(directory/'assigned_edge_device_instances.csv').read_bytes():
        raise ValueError('SH16 related-corner native replay differs')
    return receipt


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','parent_run','issue','context','output'):parser.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    paths=dict(source=args.source,graph=args.parent_run/'graph_with_edges.json',devices=args.parent_run/'assigned_edge_device_instances.csv',issue=args.issue,context=args.context)
    graph,rows,fields,proof=compute(paths);args.output.mkdir(parents=True);target=args.output/'graph_with_edges.json';target.write_bytes(encode(graph))
    (args.output/'assigned_edge_device_instances.csv').write_bytes(csv_bytes(fields,rows))
    audit=dict(mode=MODE,owner_sha256=sha(__file__),inputs={key:dict(path=str(path.resolve()),sha256=sha(path)) for key,path in paths.items()},
        output_graph_sha256=sha(target),proof=proof,human_accepted=False,hil_ready=False)
    (args.output/'SH16-related-corner-known-issue-audit.json').write_bytes(encode(audit))
    print(dict(project='SH16-10',native_related_corner_repaired=1,retired_drawing_terminals=2,components=len(rows),expert_confirmation_claimed=False,general_circle_rule=False),flush=True)


if __name__=='__main__':main()
