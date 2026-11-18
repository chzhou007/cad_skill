"""Audit existing modelspace equipment branches against inherited source rules.

Bounded offsets require independent previously reconstructed native controls;
wrong-colour inner lines require the exact confirmed upstream-resolution row.
No node, pipe, source endpoint, component owner or physical length is changed.
"""
import argparse,csv,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from native_nested_joint_evidence import fingerprint
from native_line_path_evidence import LAYERS,_on
from native_path_coverage_audit import audit as audit_paths
from reconstruct_native_block_branches import source_child
from repair_upstream_joint_systems import RULE
from source_readability import read_source
from crossview_equipment_branch_inventory import native_tee


def near(a,b):return math.dist(list(a),list(b))<=.05
def ends(line):return [list(line.dxf.start),list(line.dxf.end)]


def bars(joint):
    parts=list(joint.virtual_entities());lines=[e for e in parts if e.dxftype()=='LINE']
    if len(parts)!=6 or len(lines)!=2 or sum(e.dxftype()=='ARC' for e in parts)!=4:raise ValueError('endpoint joint transform differs')
    return [list((e.dxf.start+e.dxf.end)/2) for e in lines]


def profile(endpoint,center,contact,radius,span):
    vector=[endpoint[i]-contact[i] for i in range(3)];length=math.sqrt(sum(x*x for x in vector))
    if length<=.05 or not all(math.isfinite(v) for p in (endpoint,center,contact) for v in p) or not math.isfinite(radius) or radius<=0:raise ValueError('invalid endpoint profile')
    u=[x/length for x in vector];delta=[endpoint[i]-center[i] for i in range(3)]
    if abs(u[2])>1e-8:raise ValueError('nonplanar endpoint profile not supported')
    return [radius,length,sum(delta[i]*u[i] for i in range(3)),-delta[0]*u[1]+delta[1]*u[0],delta[2],span]


def component(graph,inventory,edge,owner,name=None,top=None):
    rows=[r for r in inventory if (name is None or r.get('device_name')==name) and (top is None or r.get('source_top_handle')==top) and r.get('equipment_type')=='金属软接' and r.get('assignment_status')=='assigned']
    if len(rows)!=1 or rows[0]['edge_id']!=edge['edge_id'] or rows[0]['owner_equipment']!=owner:raise ValueError('endpoint component is not uniquely owned')
    row=rows[0];names=[n for x in edge.get('equipment_inventory',[]) if x['equipment_type']=='金属软接' for n in x['device_names']]
    if names.count(row['device_name'])!=1:raise ValueError('endpoint graph component inventory differs')
    return row


def controls(doc,graph,inventory,policy,hashes):
    previous=load(policy['offset_policy']);audit=load(policy['offset_audit'])
    for key in ('offset_policy','offset_audit'):
        if sha(policy[key])!=policy[key+'_sha256']:raise ValueError('inherited endpoint control input changed')
    if (previous['source_sha256']!=hashes['source_sha256'] or audit['source_sha256']!=hashes['source_sha256'] or audit['policy_sha256']!=policy['offset_policy_sha256']
        or audit['status']!='source_evidence_repaired_unreviewed' or previous['joint_block']!=policy['joint_block'] or previous['block_fingerprint_sha256']!=policy['block_fingerprint_sha256']):raise ValueError('historical endpoint controls differ')
    bound=previous.get('max_radius_ratio')
    if isinstance(bound,bool) or not isinstance(bound,(float,int)) or not 0<bound<=.2:raise ValueError('historical offset bound cannot be increased')
    root=graph.get('sourceNativeBlockBranchReconstruction',{});records=[r for r in root.get('records',[]) if r.get('offset_contact')]
    expected={r['to_edge'] for r in previous['corrections']}
    if ({r['edge_id'] for r in records}!=expected or len(expected)<4 or root.get('source_sha256')!=hashes['source_sha256'] or root.get('human_accepted') is not False):raise ValueError('all inherited offset controls must be retained')
    edges={e['edge_id']:e for e in graph['edges']};results=[]
    for record in records:
        eid=record['edge_id'];edge=edges[eid];offset=record['offset_contact'];c=offset['contact'];old=[r for r in audit['changes'] if r['to_edge']==eid]
        matches=record['native_joint_evidence']['edges'][0]['matches']
        if (len(old)!=1 or len(matches)!=1 or old[0]['offset_circle_evidence']!=c or old[0]['joint_evidence']!=matches[0] or offset['control_policy_sha256']!=policy['offset_policy_sha256'] or offset['control_audit_sha256']!=policy['offset_audit_sha256']):raise ValueError('historical offset witness differs')
        match=matches[0];parent=doc.entitydb.get(record['source_insert_handle']);binding=edge.get('source_native_block_branch',{});snap=binding.get('endpoint_snapshot',{})
        if (not parent or parent.dxftype()!='INSERT' or parent not in doc.modelspace() or binding.get('source_sha256')!=hashes['source_sha256'] or binding.get('equipment_id')!=record['equipment_id']
            or snap.get('attribute_paths')!=edge['attribute_paths'] or snap.get('start_node_id')!=edge['start_node_id'] or snap.get('end_node_id')!=edge['end_node_id']):raise ValueError('current control branch binding differs')
        inner=source_child(parent,match['inner_line_chain'][1],'LINE');circle=source_child(parent,match['circle_chain'][1],'CIRCLE');joint=source_child(parent,match['joint_chain'][1],'INSERT')
        if joint.dxf.name!=policy['joint_block'] or fingerprint(doc.blocks[joint.dxf.name])!=policy['block_fingerprint_sha256'] or inner.dxf.layer!=LAYERS[record['system']]:raise ValueError('native control definition differs')
        points=bars(joint);ic=match['inner_contact'];oc=match['outer_contact'];remote=[p for p in ends(inner) if not near(p,ic)]
        center=list(circle.ocs().to_wcs(circle.dxf.center))
        if len(remote)!=1 or not any(near(ic,p) for p in ends(inner)) or not any(near(ic,p) for p in points) or not any(near(oc,p) for p in points) or not near(remote[0],c['line_endpoint']) or not near(center,c['circle_center']) or abs(circle.dxf.radius-c['radius'])>.05:raise ValueError('native control endpoint moved')
        component(graph,inventory,edge,record['equipment_id'],name=match['component_name'],top=parent.dxf.handle)
        results.append(dict(edge_id=eid,source_insert_handle=parent.dxf.handle,profile=profile(remote[0],center,ic,circle.dxf.radius,math.dist(ic,oc))))
    if len({r['source_insert_handle'] for r in results})<4:raise ValueError('offset controls are not independent native instances')
    return results,bound


def collect(doc,graph,inventory,policy,hashes):
    for key in ('source_sha256','graph_sha256','inventory_sha256'):
        if policy.get(key)!=hashes.get(key):raise ValueError('endpoint source/graph/inventory differs')
    definition=doc.blocks.get(policy['joint_block'])
    if definition is None or fingerprint(definition)!=policy['block_fingerprint_sha256']:raise ValueError('endpoint joint fingerprint differs')
    baseline,bound=controls(doc,graph,inventory,policy,hashes)
    selections=policy['selections'];edges={e['edge_id']:e for e in graph['edges']};nodes={n['node_id']:n for n in graph['nodes']}
    if not selections or len({s['edge_id'] for s in selections})!=len(selections) or len({s['joint_handle'] for s in selections})!=len(selections):raise ValueError('invalid endpoint scope')
    typed=[e for e in doc.modelspace().query('LINE') if e.dxf.layer in LAYERS.values()];circles=list(doc.modelspace().query('CIRCLE'));rows=[]
    for spec in selections:
        edge=edges[spec['edge_id']];owner=spec['equipment_id'];system=spec['system'];node=nodes.get(owner)
        if not node or node.get('node_type') not in ('equipment','physical_equipment') or edge.get('device_label')!=owner or owner not in (edge['start_node_id'],edge['end_node_id']) or edge['system']!=system:raise ValueError('logical endpoint owner differs')
        if edge.get('physical_length')!='unknown' or edge.get('path_length_complete') is not False:raise ValueError('endpoint physical-length uncertainty must be preserved')
        captions=[e for e in doc.modelspace().query('TEXT MTEXT') if e.plain_text()==owner]
        if len(captions)!=1:raise ValueError('endpoint native equipment caption ambiguous')
        tee_id=edge['end_node_id'] if edge['start_node_id']==owner else edge['start_node_id']
        junction=native_tee(doc,graph,tee_id,hashes['source_sha256'],hashes['graph_sha256'])
        joint=doc.entitydb.get(spec['joint_handle']);inner=doc.entitydb.get(spec['inner_line']);outer=doc.entitydb.get(spec['outer_line']);circle=doc.entitydb.get(spec['circle_handle'])
        if not joint or joint.dxftype()!='INSERT' or joint not in doc.modelspace() or joint.dxf.name!=policy['joint_block']:raise ValueError('modelspace endpoint joint differs')
        if any(not line or line.dxftype()!='LINE' or line not in doc.modelspace() or line.dxf.layer not in LAYERS.values() for line in (inner,outer)) or outer.dxf.layer!=LAYERS[system]:raise ValueError('modelspace endpoint source lines differ')
        if not circle or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace() or tuple(circle.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.) or circle.dxf.layer!='空调平面':raise ValueError('native equipment circle differs')
        points=bars(joint);pairs=[(i,j) for i in range(2) for j in range(2) if i!=j and sum(near(points[i],p) for p in ends(inner))==1 and sum(near(points[j],p) for p in ends(outer))==1]
        if len(pairs)!=1:raise ValueError('endpoint joint contacts ambiguous')
        ic,oc=points[pairs[0][0]],points[pairs[0][1]]
        for point,line in ((ic,inner),(oc,outer)):
            if [l.dxf.handle for l in typed if any(near(p,point) for p in ends(l))]!=[line.dxf.handle]:raise ValueError('competing native endpoint pipe')
        remote=next(p for p in ends(inner) if not near(p,ic));center=list(circle.dxf.center);offset=math.dist(remote,center)
        candidates=[c for c in circles if tuple(c.dxf.get('extrusion',(0,0,1)))==(0.,0.,1.) and c.dxf.radius>0 and math.dist(remote,list(c.dxf.center))<=bound*c.dxf.radius+.05]
        if candidates!=[circle]:raise ValueError('native endpoint circle ambiguous')
        relation='exact_native_circle_contact';matched=[]
        if offset>.05:
            p=profile(remote,center,ic,circle.dxf.radius,math.dist(ic,oc));matched=[r for r in baseline if all(abs(a-b)<=.05 for a,b in zip(p,r['profile']))]
            if len({r['source_insert_handle'] for r in matched})<4:raise ValueError('offset lacks independent inherited geometry controls')
            relation='inherited_native_offset_profile_no_endpoint_snap'
        row=component(graph,inventory,edge,owner,top=joint.dxf.handle)
        coverage=audit_paths(doc,graph,dict(source_sha256=hashes['source_sha256'],graph_sha256=hashes['graph_sha256'],edges=[edge['edge_id']]),hashes['source_sha256'],hashes['graph_sha256'])
        segments=coverage['edges'][0]['segments'];missing=[s for s in segments if s['status']!='single_source_line_covers']
        anchor=[node['x'],node['y']]
        if len(missing)!=1 or missing[0]['status']!='no_witness_in_scoped_search' or not ((near(missing[0]['start'],anchor) and near(missing[0]['end'],oc[:2])) or (near(missing[0]['end'],anchor) and near(missing[0]['start'],oc[:2]))):raise ValueError('unsupported gap is not the existing unknown equipment anchor')
        resolution=None
        if inner.dxf.layer!=LAYERS[system]:
            records=[r for r in edge.get('source_inline_system_resolutions',[]) if r.get('joint_handle')==joint.dxf.handle]
            if len(records)!=1:raise ValueError('source colour conflict has no exact confirmed resolution')
            resolution=records[0];confirmation=resolution.get('confirmation',{})
            if (graph.get('sourceInlineSystemResolutions',[]).count(resolution)!=1 or resolution.get('source_sha256')!=hashes['source_sha256'] or resolution.get('to_edge')!=edge['edge_id'] or resolution.get('system')!=system or resolution.get('logical_owner_equipment')!=owner
                or resolution.get('device_name')!=row['device_name'] or confirmation.get('rule')!=RULE or confirmation.get('status')!='user_confirmed' or not confirmation.get('source_reference') or not confirmation.get('statement')):raise ValueError('confirmed upstream resolution binding differs')
            if (resolution.get('upstream_tee')!=tee_id or resolution.get('status')!='source_colour_error_resolved_by_confirmed_upstream_rule'
                or resolution.get('physical_port_verified') is not False or resolution.get('physical_length')!='unknown' or resolution.get('whole_graph_human_accepted') is not False):raise ValueError('confirmed source uncertainty or upstream node changed')
            tee=resolution['upstream_tee'];other=nodes[tee];ordered=segments if near(segments[0]['start'],[other['x'],other['y']]) else [dict(s,start=s['end'],end=s['start']) for s in reversed(segments)]
            prefix=[]
            for segment in ordered:
                if segment['status']!='single_source_line_covers':break
                prefix.append(segment)
            if not prefix or [s['witnesses'][0]['source_handle'] for s in prefix]!=resolution['source_line_handles'] or not near(prefix[-1]['end'],oc[:2]) or prefix[-1]['witnesses'][0]['source_handle']!=outer.dxf.handle:raise ValueError('confirmed same-system upstream route no longer reaches joint')
            contacts=resolution['original_conflict']['contacts'];claimed=[l for c in contacts for l in c['lines']]
            if {l['source_handle'] for l in claimed}!={inner.dxf.handle,outer.dxf.handle}:raise ValueError('recorded source colour conflict changed')
            for literal in claimed:
                actual=doc.entitydb[literal['source_handle']]
                if actual.dxf.layer!=LAYERS[literal['system']] or not near(actual.dxf.start,literal['line_start']) or not near(actual.dxf.end,literal['line_end']):raise ValueError('native colour-error source differs')
        rows.append(dict(edge_id=edge['edge_id'],equipment_id=owner,system=system,joint_handle=joint.dxf.handle,component_name=row['device_name'],inner_line_handle=inner.dxf.handle,outer_line_handle=outer.dxf.handle,circle_handle=circle.dxf.handle,
            native_inner_line_XYZ=ends(inner),native_circle_center=center,inner_contact=ic,outer_contact=oc,circle_relation=relation,native_circle_offset=offset,matched_inherited_control_edges=[r['edge_id'] for r in matched],
            source_colour_resolution=resolution,coverage=coverage,upstream_junction_evidence=junction,unknown_anchor_segment_index=missing[0]['index'],physical_port_verified=False,physical_length_mm=None,human_accepted=False))
    return dict(status='native_exploded_endpoint_chains_replayed_not_physical_ports',source_sha256=hashes['source_sha256'],graph_sha256=hashes['graph_sha256'],inventory_sha256=hashes['inventory_sha256'],
        inherited_controls=baseline,records=rows,graph_mutated=False,component_owners_changed=False,hil_ready=False,human_accepted=False)


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','inventory','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    doc,preflight=read_source(a.source)
    with a.inventory.open(encoding='utf-8-sig',newline='') as stream:inventory=list(csv.DictReader(stream))
    hashes=dict(source_sha256=sha(a.source),graph_sha256=sha(a.graph),inventory_sha256=sha(a.inventory));result=collect(doc,load(a.graph),inventory,load(a.policy),hashes)
    result.update(policy_sha256=sha(a.policy),source_preflight=preflight,implementation_sha256=sha(__file__));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(encode(result));print({'replayed_endpoints':len(result['records']),'graph_mutated':False},flush=True)


if __name__=='__main__':main()
