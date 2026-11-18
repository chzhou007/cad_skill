"""Recover floor-plan paths for a confirmed member of overlapping pipe carriers.

Detail topology remains the canonical graph. Original confirmed view aliases,
native wave rays, independently checked detail Ts and an explicit compound-lane
reply bind the additional plan coordinate domain. No detail drawing length,
unshown branch connector or other member's T is promoted to a measured pipe.
"""
import argparse,csv,hashlib,math,sys
from pathlib import Path
_pipeline=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(_pipeline)not in sys.path:sys.path.insert(0,str(_pipeline))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from confirmed_compound_pipe_lanes import verify_output as verify_lanes
from native_sideview_equipment_branch_evidence import collect as verify_detail
from native_plan_projection_lengths import unit_evidence
from inherited_wave_pair_continuity import contact,wave_feature
from reconstruct_wave_main_cohorts import forward_hits
from wave_omission_candidates import block_fingerprint
from native_line_path_evidence import LAYERS,_on
from native_replay_session import verify_once

MODE='confirmed_overlap_member_floor_plan_paths_v1'
TOL=.05

def point(n):return[n['x'],n['y']]

def projection(doc,graph,relation,source_hash,graph_hash):
    state=graph['confirmedSideviewCanonicalization'];nodes={n['node_id']:n for n in state['representation_only_nodes']}
    archived={e['edge_id']:e for e in state['representation_only_edges']};edges={e['edge_id']:e for e in graph['edges']}
    branch=edges[relation['canonical_edge']];meta=branch.get('source_sideview_equipment_interface',{})
    if meta.get('question_id')!=relation['question_id'] or branch['system']!=relation['system']:raise ValueError('current branch/view alias differs')
    proof=verify_detail(doc,graph,relation['verified_detail_tee']['tee'],source_hash,graph_hash)
    if proof['logical_equipment_owner']!=meta['equipment_id']:raise ValueError('detail equipment owner differs')
    old=archived[relation['abbreviated_edge']];terminal=nodes[relation['retired_wave_terminal']];p=point(terminal)
    if old['system']!=branch['system']or old['source_wave_terminal']['source_sha256']!=source_hash:raise ValueError('archived native wave scope differs')
    endpoint=contact(doc,old,p,branch['system']);tail=max([q[:2]for q in endpoint['line_XYZ']],key=lambda q:math.dist(q,p));distance=math.dist(p,tail)
    outward=[(p[i]-tail[i])/distance for i in (0,1)];wave=old['source_wave_terminal'];fingerprint=block_fingerprint(doc.blocks[wave['source_block_name']])
    curve=wave_feature(doc,wave['source_wave_handle'],p,endpoint['XYZ'],outward,wave['source_block_name'],fingerprint)
    hits=forward_hits(doc,p,outward,branch['system'])
    if not hits or sum(abs(h['distance']-hits[0]['distance'])<=TOL for h in hits)!=1:raise ValueError('projected main ray is absent or competing')
    return dict(equipment_id=meta['equipment_id'],system=branch['system'],canonical_branch=branch['edge_id'],canonical_tee=relation['verified_detail_tee']['tee'],
        question_id=relation['question_id'],pair_sha256=relation['pair_sha256'],native_detail_T=proof,native_wave=curve,
        original_abbreviated_edge=old['edge_id'],plan_main_hit=hits[0],unshown_branch_connector_length_mm=None)

def on_segment(p,a,b):return _on(p,a,b,TOL)and math.dist(p,a)>TOL and math.dist(p,b)>TOL

def collect(doc,graph,components,lanes,policy,units,source_hash,graph_hash):
    if (graph.get('metadata',{}).get('source_sha256')!=source_hash or lanes.get('source_sha256')!=source_hash
        or units.get('status')!='native_mm_units_corroborated_not_pipe_dimension_assignment'):raise ValueError('source/member/plan unit evidence differs')
    state=graph['confirmedSideviewCanonicalization'];edges={e['edge_id']:e for e in graph['edges']};nodes={n['node_id']:n for n in graph['nodes']}
    if len(edges)!=len(graph['edges'])or len(nodes)!=len(graph['nodes']):raise ValueError('duplicate local graph identities')
    declarations={r['handle']:r for r in lanes['records']};seen_edges=set();seen_groups=set();anchors=[];records=[];groups=[]
    if not policy.get('groups'):raise ValueError('explicit confirmed member groups required')
    for group in policy['groups']:
        gid=group['group_id'];equipment=group['equipment_ids'];floor=group['floor']
        if gid in seen_groups or len(equipment)<3 or len(set(equipment))!=len(equipment):raise ValueError('duplicate or insufficient member cohort')
        seen_groups.add(gid)
        if set(group['compound_text_by_system'])!={'supply','return'}:raise ValueError('paired separate services required')
        group_rows=[]
        for system in ('supply','return'):
            declaration=declarations[group['compound_text_by_system'][system]];members=[m for m in declaration['members']if m['role']=='sideview_network_lane']
            if len(members)!=1 or declaration['source_LINE_membership_confirmed']is not False:raise ValueError('confirmed member role differs')
            nominal=members[0]['nominal_mm'];by={}
            for name in equipment:
                candidates=[]
                for relation in state['records']:
                    edge=edges.get(relation['canonical_edge'],{});meta=edge.get('source_sideview_equipment_interface',{})
                    if meta.get('equipment_id')==name and relation['system']==system:candidates.append(relation)
                if len(candidates)!=1 or nodes.get(name,{}).get('floor')!=floor:raise ValueError('unique current paired device alias required')
                by[name]=projection(doc,graph,candidates[0],source_hash,graph_hash)
            hits=[r['plan_main_hit']for r in by.values()];handles={h['source_handle']for h in hits}
            if len(handles)!=1:raise ValueError('cohort needs one continuous native projected carrier; split or omitted carriers require their own reader')
            handle=next(iter(handles));line=doc.entitydb.get(handle)
            if not line or line.dxftype()!='LINE'or line not in doc.modelspace()or line.dxf.layer!=LAYERS[system]:raise ValueError('native carrier service differs')
            native=[list(line.dxf.start),list(line.dxf.end)];a,b=[p[:2]for p in native];length=math.dist(a,b);direction=[(b[i]-a[i])/length for i in (0,1)]
            if any(not _on(h['point'],a,b,TOL)for h in hits):raise ValueError('projected anchor leaves native carrier')
            order=sorted(by,key=lambda n:sum((by[n]['plan_main_hit']['point'][i]-a[i])*direction[i]for i in (0,1)))
            label=doc.entitydb.get(declaration['handle']);pos=list(label.dxf.insert)[:2];textdir=[math.cos(math.radians(label.dxf.rotation)),math.sin(math.radians(label.dxf.rotation))]
            start,end=by[order[0]]['plan_main_hit']['point'],by[order[-1]]['plan_main_hit']['point'];projection_at=sum((pos[i]-start[i])*direction[i]for i in (0,1));span=math.dist(start,end)
            offset=abs((pos[0]-a[0])*direction[1]-(pos[1]-a[1])*direction[0])
            if (abs(sum(x*y for x,y in zip(textdir,direction)))<math.cos(math.radians(.1))or not 0<=projection_at<=span
                or not TOL<offset<=label.dxf.height*1.5):raise ValueError('compound declaration geometry outside confirmed member extent')
            for name in order:anchors.append(dict(by[name],group_id=gid,source_compound_text=declaration['handle'],nominal_mm=nominal,member_scope_id=gid+':'+system))
            for left,right in zip(order,order[1:]):
                u,v=by[left]['canonical_tee'],by[right]['canonical_tee'];p,q=by[left]['plan_main_hit']['point'],by[right]['plan_main_hit']['point']
                candidates=[e for e in graph['edges']if e['system']==system and {e.get('start_node_id'),e.get('end_node_id')}=={u,v}]
                if len(candidates)!=1:raise ValueError('adjacent projected anchors lack one canonical same-service main edge')
                edge=candidates[0];eid=edge['edge_id']
                if eid in seen_edges or any(edge.get(k)!=floor for k in ('start_floor','end_floor')):raise ValueError('duplicate member edge or floor conflict')
                seen_edges.add(eid)
                competitors=[e.dxf.handle for e in doc.modelspace().query('LINE')if e.dxf.layer==LAYERS[system]and _on(p,list(e.dxf.start)[:2],list(e.dxf.end)[:2],TOL)and _on(q,list(e.dxf.start)[:2],list(e.dxf.end)[:2],TOL)]
                if competitors!=[handle]:raise ValueError('member plan path has competing native LINEs')
                window=units['plan_window']
                if any(not(window[0]<=t[0]<=window[1]and window[2]<=t[1]<=window[3])for t in (p,q)):raise ValueError('member metric leaves verified floor-plan window')
                inline=[c['device_name']for c in components if on_segment([float(c['x']),float(c['y'])],p,q)]
                detail=list(edge.get('equipment_names',[]))
                # End-to-end run centreline is independent of component body
                # allocation. It is not net pipe cut length. In particular no
                # detail-symbol station or body dimension is scaled to plan.
                value=math.dist(p,q)
                row=dict(group_id=gid,member_scope_id=gid+':'+system,floor=floor,system=system,plan_edge_id=eid,canonical_Ts=[u,v],equipment_anchors=[left,right],
                    nominal_mm=nominal,compound_text_handle=declaration['handle'],source_declaration_slot_id=members[0]['declaration_slot_id'],
                    shared_projected_source_LINE=handle,native_LINE_endpoints_WCS=native,plan_points=[p,q],
                    canonical_detail_points=[point(nodes[u]),point(nodes[v])],canonical_attribute_paths=edge['attribute_paths'],
                    status='confirmed_member_native_plan_run_centerline',
                    horizontal_plan_run_centerline_mm=value,net_pipe_cut_length_mm=None,installed_whole_edge_length_mm=None,unshown_branch_connector_length_mm=None,
                    run_centerline_includes_inline_assembly_extents=True,detail_inline_positions_scaled_to_plan=False,
                    projected_inline_components=inline,projected_component_member_allocation='unresolved'if inline else'no_projected_inline_marker_in_interval',
                    canonical_detail_inline_components=detail,canonical_component_plan_stations_mm=None,
                    source_view_aliases=[by[left]['question_id'],by[right]['question_id']],physical_pipe_id=None,human_accepted=False)
                records.append(row);group_rows.append(eid)
        groups.append(dict(group_id=gid,equipment_ids=equipment,member_edges=group_rows,other_member_Ts_or_connections_inferred=False))
    return dict(mode=MODE,source_sha256=source_hash,graph_sha256=graph_hash,groups=groups,anchors=anchors,records=records,unit_evidence=units,
        counts=dict(groups=len(groups),anchors=len(anchors),member_main_edges=len(records),run_centerline_ready=len(records),net_pipe_cut_lengths_assigned=0),
        local_connectivity_changed=False,detail_drawing_span_used_as_length=False,other_member_connections_inferred=False,
        installed_lengths_assigned=0,physical_pipe_count_inferred=False,human_accepted=False)

def implementation_hashes():
    names=('confirmed_compound_pipe_lanes','native_sideview_equipment_branch_evidence','native_plan_projection_lengths',
        'inherited_wave_pair_continuity','reconstruct_wave_main_cohorts','wave_omission_candidates','native_line_path_evidence','source_readability')
    import importlib
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('confirmed member input changed')
    checked();graph=load(paths['graph']);sh=sha(paths['source']);gh=sha(paths['graph'])
    from rebuild_full_plan_DN import PARENTS
    import importlib
    if manifest['parent_mode']not in PARENTS:raise ValueError('unsupported local topology owner')
    verify_parent=importlib.import_module(PARENTS[manifest['parent_mode']]).verify_output
    parent=verify_once(paths['graph'].parent,verify_parent)
    if parent['output_graph_sha256']!=gh:raise ValueError('current local topology owner replay differs')
    lanes=verify_once(paths['lanes'].parent,verify_lanes)
    if lanes['source_sha256']!=sh:raise ValueError('confirmed lane source differs')
    doc,preflight=read_source(paths['source']);units=unit_evidence(doc,load(paths['units']))
    with paths['components'].open(encoding='utf-8-sig',newline='')as stream:components=list(csv.DictReader(stream))
    result=collect(doc,graph,components,lanes,load(paths['policy']),units,sh,gh);result['source_preflight']=preflight;result['local_topology_owner_replayed']=True
    checked();return result

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest_path));output.mkdir(parents=True);target=output/'member-plan-paths.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=implementation_hashes(),output_sha256=sha(target))))
    return result

def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');m=r['manifest'];target=output/'member-plan-paths.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=r['output_sha256']:raise ValueError('member plan proof binding changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('member plan native replay differs')
    return fresh

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:
            if a.manifest or a.output:p.error('verification uses original inputs')
            result=verify_output(a.verify_output)
        else:
            if not(a.manifest and a.output):p.error('manifest and new output required')
            result=produce(a.manifest,a.output)
    print(result['counts'],flush=True)
if __name__=='__main__':main()
