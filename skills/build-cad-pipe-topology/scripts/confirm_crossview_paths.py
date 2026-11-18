"""Confirm explicitly reviewed path correspondence after native local checks.

The mapping is a separate layer. It establishes neither equal segment counts,
installed lengths nor diameter values, and never repairs either local graph.
"""
import argparse,copy,csv,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from source_readability import read_source
from crossview_route_diagnostics import _caption
from native_path_coverage_audit import audit as audit_paths
from native_junction_ray_evidence import collect as audit_junctions
from native_exploded_device_joint_evidence import collect as audit_device_joints
from classify_device_anchor_spans import classify as classify_anchors

DECISION='可以对应，具体范围见说明'
INPUTS=('plan_source','iso_source','plan_graph','iso_graph','reviewed_plan','reviewed_iso','pair_audit','pair','reply','iso_devices')
encode=lambda value:(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')
load=lambda path:json.loads(Path(path).read_text(encoding='utf-8-sig'))
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
data_sha=lambda value:hashlib.sha256(encode(value)).hexdigest()

def route(graph,edge_ids,start,end,system):
    nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']}
    if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']) or not edge_ids or len(set(edge_ids))!=len(edge_ids):raise ValueError('duplicate or empty path')
    if start not in nodes or end not in nodes or system not in ('supply','return'):raise ValueError('invalid path endpoints')
    current=start;seen={start};visited=[start]
    for eid in edge_ids:
        edge=edges.get(eid)
        if not edge or edge.get('system')!=system or current not in (edge.get('start_node_id'),edge.get('end_node_id')):raise ValueError('disconnected or mixed-system path')
        current=edge['end_node_id'] if current==edge['start_node_id'] else edge['start_node_id']
        if current not in nodes or current in seen:raise ValueError('cyclic or missing path node')
        if nodes[current].get('floor')!=nodes[start].get('floor'):raise ValueError('same-floor mapping cannot include inter-floor path')
        if current!=end and nodes[current].get('node_type') in ('equipment','physical_equipment','virtual_equipment'):raise ValueError('path crosses another equipment or boundary')
        if nodes[current].get('review_required') is True:raise ValueError('local topology review still unresolved')
        seen.add(current);visited.append(current)
    if current!=end or nodes[end].get('node_type') not in ('equipment','physical_equipment'):raise ValueError('path does not reach selected equipment')
    return visited

def snapshot(graph,edge_ids):
    edges={e['edge_id']:e for e in graph['edges']};ids={n for eid in edge_ids for n in (edges[eid]['start_node_id'],edges[eid]['end_node_id'])}
    edge_keys=('edge_id','system','start_node_id','end_node_id','path_points','attribute_paths','source_handles','source_insert_handle','source_exploded_device_chain','confirmed_equipment_interface')
    node_keys=('node_id','node_type','floor','system','x','y','source_handle')
    return dict(edges=[{k:edges[eid].get(k) for k in edge_keys} for eid in edge_ids],
        nodes=sorted(({k:n.get(k) for k in node_keys} for n in graph['nodes'] if n['node_id'] in ids),key=lambda n:n['node_id']))

def reviewed_answer(reply,pair_hash,question_id,equipment):
    matches=[(section,q) for section in reply['sections'] for q in section['questions'] if q['id']==question_id]
    if len(matches)!=1:raise ValueError('missing or duplicate scoped reply')
    section,q=matches[0]
    if (section['image']['sha256']!=pair_hash or not any(equipment in text for text in (q['id'],q['text'],section.get('title','')))
        or q.get('answer',{}).get('decision')!=DECISION or not q['answer'].get('comment','').strip()):raise ValueError('explicit path reply or original Pair differs')
    return copy.deepcopy(q)

def build(paths,policy):
    for key in INPUTS:
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('stale '+key)
    pair=load(paths['pair_audit'])
    if (pair['image_sha256']!=sha(paths['pair']) or pair['plan_graph_sha256']!=sha(paths['reviewed_plan'])
        or pair['iso_graph_sha256']!=sha(paths['reviewed_iso'])
        or pair['plan_source_sha256']!=sha(paths['plan_source']) or pair['iso_source_sha256']!=sha(paths['iso_source'])):raise ValueError('reviewed Pair audit mismatch')
    equipment=policy['equipment_id'];answer=reviewed_answer(load(paths['reply']),sha(paths['pair']),policy['question_id'],equipment)
    graphs={view:load(paths[view+'_graph']) for view in ('plan','iso')}
    docs={view:read_source(paths[view+'_source'])[0] for view in ('plan','iso')}
    hashes={view:dict(source_sha256=sha(paths[view+'_source']),graph_sha256=sha(paths[view+'_graph'])) for view in ('plan','iso')}
    reviewed={view:load(paths['reviewed_'+view]) for view in ('plan','iso')}
    rows=policy['routes']
    if len(rows)!=2 or {r['system'] for r in rows}!={'supply','return'}:raise ValueError('scoped device must preserve both independent services')
    evidence={};records=[]
    for view in ('plan','iso'):
        graph=graphs[view];native=docs[view];hs=hashes[view]
        _caption(native,policy[view+'_text_handle'],equipment)
        selected=[eid for r in rows for eid in r[view+'_edges']]
        if snapshot(graph,selected)!=snapshot(reviewed[view],selected):raise ValueError('reviewed local topology changed: '+view)
        if len(set(selected))!=len(selected):raise ValueError('mapping paths share a service edge')
        evidence[view]=dict(coverage=audit_paths(native,graph,dict(hs,edges=selected),**dict(source_hash=hs['source_sha256'],graph_hash=hs['graph_sha256'])),
            junctions=audit_junctions(native,graph,dict(hs,junctions=policy[view+'_junctions']),hs['source_sha256'],hs['graph_sha256']))
        node=next(n for n in graph['nodes'] if n['node_id']==equipment)
        if node.get('floor')!=policy['floor']:raise ValueError('equipment floor differs from reviewed mapping')
    with Path(paths['iso_devices']).open(encoding='utf-8-sig',newline='') as stream:inventory=list(csv.DictReader(stream))
    joint_policy=dict(policy['iso_joint_policy'],**hashes['iso'],inventory_sha256=sha(paths['iso_devices']))
    joints=audit_device_joints(docs['iso'],graphs['iso'],inventory,joint_policy,dict(hashes['iso'],inventory_sha256=sha(paths['iso_devices'])))
    joints.update(hashes['iso'])
    anchor_hashes=dict(hashes['iso'],coverage_sha256=data_sha(evidence['iso']['coverage']),joints_sha256=data_sha(joints))
    anchors=classify_anchors(graphs['iso'],evidence['iso']['coverage'],joints,dict(anchor_hashes,edge_ids=[r['iso_edges'][-1] for r in rows]),anchor_hashes)
    allowed_gaps={(r['edge_id'],r['unwitnessed_segment_index']) for r in anchors['records']}
    for view in ('plan','iso'):
        for e in evidence[view]['coverage']['edges']:
            for segment in e['segments']:
                if segment['status']!='single_source_line_covers' and not (view=='iso' and (e['edge_id'],segment['index']) in allowed_gaps):raise ValueError('local source path still lacks unique native coverage')
    plan_edges={e['edge_id']:e for e in graphs['plan']['edges']}
    for item in rows:
        system=item['system']
        expected=[r for r in pair['records'] if r['system']==system]
        if len(expected)!=1:raise ValueError('original Pair service scope ambiguous')
        for view,key in (('plan','plan_edge'),('iso','isometric_edge')):
            permitted=expected[0].get(view+'_edges') or [expected[0][key]]
            if permitted!=item[view+'_edges']:raise ValueError('mapping exceeds original reviewed path scope')
            route(graphs[view],item[view+'_edges'],item[view+'_start'],equipment,system)
            starts=[j for j in evidence[view]['junctions']['junctions'] if j['node_id']==item[view+'_start'] and j['system']==system]
            if len(starts)!=1 or item[view+'_edges'][0] not in {r['edge_id'] for r in starts[0]['source_rays']}:raise ValueError('mapped start lacks native T incidence')
        leaf=plan_edges[item['plan_edges'][-1]];interface=leaf.get('confirmed_equipment_interface') or {}
        if (interface.get('source_sha256')!=hashes['plan']['source_sha256'] or interface.get('confirmation',{}).get('confirmed_by')!='user'
            or equipment not in (leaf['start_node_id'],leaf['end_node_id'])):raise ValueError('plan device interface not independently confirmed')
        records.append(dict(equipment_id=equipment,system=system,floor=policy['floor'],plan_edges=item['plan_edges'],iso_edges=item['iso_edges'],
            plan_start=item['plan_start'],iso_start=item['iso_start'],status='expert_confirmed_same_floor_route_correspondence_native_checked',
            plan_snapshot=snapshot(graphs['plan'],item['plan_edges']),iso_snapshot=snapshot(graphs['iso'],item['iso_edges']),
            parameter_fusion=dict(status='pending_segment_extent_and_annotation_checks',horizontal_source='plan',inter_floor_vertical_source='isometric',
                physical_diameter_mm=None,physical_length_mm=None,axis_vertical_stroke_is_not_inter_floor_proof=True),
            physical_port_verified=False,whole_graph_accepted=False))
    return dict(status='confirmed_path_correspondence_attributes_pending',**{view+'_graph_sha256':hashes[view]['graph_sha256'] for view in hashes},
        source_sha256={view:hashes[view]['source_sha256'] for view in hashes},records=records,answer=answer,
        evidence=dict(local=evidence,iso_device_joints=joints,iso_anchor_connectors=anchors),
        local_scope='reviewed device branches and their source-witnessed main Ts only; other drawing regions remain independent',
        local_graphs_mutated=False,human_accepted=False,hil_ready=False)

def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in ('confirm_crossview_paths.py','crossview_route_diagnostics.py','native_path_coverage_audit.py','native_junction_ray_evidence.py','native_exploded_device_joint_evidence.py','classify_device_anchor_spans.py','source_readability.py','native_line_path_evidence.py')}

def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'mapping-receipt.json')
    if receipt['implementation_sha256']!=implementation_hashes():raise ValueError('stale mapping implementation')
    for spec in receipt['inputs'].values():
        if sha(spec['path'])!=spec['sha256']:raise ValueError('stale mapping input')
    result=build({key:item['path'] for key,item in receipt['inputs'].items()},load(receipt['inputs']['policy']['path']))
    if encode(result)!=(directory/'mapping.json').read_bytes() or sha(directory/'mapping.json')!=receipt['output_sha256']:raise ValueError('mapping native replay differs')
    return result

def main():
    parser=argparse.ArgumentParser()
    for key in INPUTS+('policy','output'):parser.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    args=parser.parse_args();paths={key:getattr(args,key) for key in INPUTS}
    if args.output.exists():raise FileExistsError(args.output)
    result=build(paths,load(args.policy));args.output.mkdir(parents=True)
    (args.output/'mapping.json').write_bytes(encode(result))
    receipt=dict(inputs={key:dict(path=str(getattr(args,key).resolve()),sha256=sha(getattr(args,key))) for key in INPUTS+('policy',)},
        output_sha256=sha(args.output/'mapping.json'),implementation_sha256=implementation_hashes(),human_accepted=False)
    (args.output/'mapping-receipt.json').write_bytes(encode(receipt))
    print(json.dumps(dict(status=result['status'],mapped_paths=len(result['records']),local_graphs_mutated=False)))

if __name__=='__main__':main()
