"""Inventory both native service branches before expanding cross-view mappings.

This is a source comparison queue, not a correspondence confirmation. Caption,
floor or nearby geometry alone never establish equipment/port ownership.
"""
import argparse,collections,csv,hashlib,json,math
from pathlib import Path
from confirm_crossview_paths import encode,load,sha
from crossview_route_diagnostics import _caption
from native_line_path_evidence import _on,LAYERS
from native_path_coverage_audit import audit as audit_paths
from native_junction_ray_evidence import collect as audit_junctions
from native_exploded_device_joint_evidence import collect as audit_joints
from native_nested_joint_evidence import fingerprint
from classify_device_anchor_spans import classify
from source_readability import read_source
from native_equipment_body import body_straight_segments

def index_graph(graph):
    nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']}
    if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']):raise ValueError('duplicate graph IDs')
    adjacent=collections.defaultdict(list)
    for edge in edges.values():
        for key in ('start_node_id','end_node_id'):
            if edge.get(key):
                if edge[key] not in nodes:raise ValueError('edge references missing node')
                adjacent[edge[key]].append(edge)
    return nodes,edges,adjacent

def unresolved_identity_candidates(doc,graph,equipment,floor):
    """Expose retained anonymous bodies without treating label candidates as IDs."""
    candidates=[]
    for node in graph['nodes']:
        if (node.get('node_type') not in ('equipment','physical_equipment') or node.get('floor')!=floor
            or equipment not in node.get('source_label_candidates',[])):continue
        insert=doc.entitydb.get(node.get('source_handle'))
        if not insert or insert not in doc.modelspace() or insert.dxftype()!='INSERT':continue
        segments,unsupported=body_straight_segments(insert)
        if not segments or unsupported:continue
        points=[p for a,b in segments for p in (a,b)]
        bounds=[min(p[0] for p in points),max(p[0] for p in points),min(p[1] for p in points),max(p[1] for p in points)]
        center=[(bounds[0]+bounds[1])/2,(bounds[2]+bounds[3])/2]
        if math.dist(center,[node['x'],node['y']])>.05:continue
        candidates.append(dict(node_id=node['node_id'],source_handle=insert.dxf.handle,native_body_bounds=bounds,
            label_candidates=node['source_label_candidates'],status='retained_native_body_identity_unresolved',
            equipment_identity_selected=False,ports_verified=False))
    return candidates

def service_route(graph,equipment,system,max_hops=12):
    nodes,edges,adj=index_graph(graph);current=equipment;visited={equipment};route=[]
    if system not in LAYERS or equipment not in nodes:raise ValueError('invalid equipment or service')
    floor=nodes[equipment].get('floor')
    for _ in range(max_hops):
        same=[e for e in adj[current] if e.get('system')==system and e['edge_id'] not in route]
        if len(same)!=1:return {'status':'missing_service' if not same else 'ambiguous_service','edges':route,'at_node':current}
        edge=same[0];route.append(edge['edge_id']);current=edge['end_node_id'] if current==edge.get('start_node_id') else edge.get('start_node_id')
        if current not in nodes:return {'status':'non_node_boundary','edges':route,'at_node':current}
        if current in visited:return {'status':'cycle','edges':route,'at_node':current}
        visited.add(current);node=nodes[current]
        if node.get('floor')!=floor:return {'status':'floor_change','edges':route,'at_node':current}
        if node.get('node_type') in ('tee','physical_junction'):
            incident=adj[current]
            good=len(incident)==3 and {e.get('system') for e in incident}=={system} and node.get('review_required') is not True
            return {'status':'unique_graph_service_to_T' if good else 'unresolved_or_non_tee_junction','edges':route,'tee':current}
        if node.get('node_type') in ('equipment','physical_equipment','virtual_equipment'):
            return {'status':'unresolved_interface_or_other_equipment','edges':route,'at_node':current}
        # A straight degree-two subdivision may be traversed; mixed contacts may not.
        if len(adj[current])!=2 or any(e.get('system')!=system for e in adj[current]):
            return {'status':'unsupported_intermediate_node','edges':route,'at_node':current}
    return {'status':'hop_limit','edges':route,'at_node':current}

def native_tee(doc,graph,node_id,source_hash,graph_hash):
    nodes,_,adj=index_graph(graph);node=nodes[node_id];point=[node['x'],node['y']];witnesses={}
    if any(e.get('source_sideview_equipment_interface') for e in adj[node_id]):
        from native_sideview_equipment_branch_evidence import collect
        return collect(doc,graph,node_id,source_hash,graph_hash)
    if node.get('source_confirmed_equipment_pair_circle'):
        from native_confirmed_equipment_pair_circle_evidence import collect
        return collect(doc,graph,node_id,source_hash,graph_hash)
    if node.get('source_reviewed_circle'):
        from source_reviewed_circle_branch_evidence import collect
        return collect(doc,graph,node_id,source_hash,graph_hash)
    if node.get('user_confirmed_circle'):
        from source_reviewed_circle_branch_evidence import collect_user
        return collect_user(doc,graph,node_id,source_hash,graph_hash)
    if any(e.get('source_circle_connection') for e in adj[node_id]):
        from native_circle_rim_junction_evidence import collect
        return collect(doc,graph,node_id,source_hash,graph_hash)
    for edge in adj[node_id]:
        rays=[]
        for path in edge.get('attribute_paths',[]):
            for a,b in zip(path,path[1:]):
                if math.dist(a,point)<=.05 and math.dist(b,point)>.05:rays.append((a,b))
                elif math.dist(b,point)<=.05 and math.dist(a,point)>.05:rays.append((b,a))
        if len(rays)!=1:raise ValueError('missing or ambiguous graph T ray')
        a,b=rays[0];hits=[]
        for line in doc.modelspace().query('LINE'):
            if line.dxf.layer!=LAYERS[edge['system']]:continue
            start=[line.dxf.start.x,line.dxf.start.y];end=[line.dxf.end.x,line.dxf.end.y]
            if _on(a,start,end,.05) and _on(b,start,end,.05):hits.append(line.dxf.handle)
        if len(hits)==1:witnesses[edge['edge_id']]=hits[0]
        elif not hits and edge.get('source_insert_handle'):
            # The shared collector independently checks this exact INSERT's
            # transformed LINE descendants, source layer and unique ray.  It
            # also retains opposing-system contacts without connecting them.
            witnesses[edge['edge_id']]={'scope':'decomposed_selected_insert','insert_handle':edge['source_insert_handle']}
        else:raise ValueError('native T ray is not uniquely witnessed')
    return audit_junctions(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,junctions=[dict(node_id=node_id,edge_witnesses=witnesses)]),source_hash,graph_hash)

def inspect_branch(doc,graph,equipment,system,hashes,view,inventory):
    trace=service_route(graph,equipment,system)
    result=dict(trace=trace,ready_for_mapping_comparison=False)
    if trace['status']!='unique_graph_service_to_T':return result
    try:
        result['junction_evidence']=native_tee(doc,graph,trace['tee'],hashes['source_sha256'],hashes['graph_sha256'])
        if view=='iso' and len(trace['edges'])==1:
            leaf=next(e for e in graph['edges'] if e['edge_id']==trace['edges'][0])
            rebuilt=leaf.get('source_native_block_branch')
            if rebuilt:
                from reconstruct_native_block_branches import projected_coverage
                root=graph.get('sourceNativeBlockBranchReconstruction',{});rows=[r for r in root.get('records',[]) if r.get('edge_id')==leaf['edge_id']]
                snapshot=rebuilt.get('endpoint_snapshot',{})
                if (len(rows)!=1 or rebuilt.get('equipment_id')!=equipment or rebuilt.get('system')!=system
                    or rebuilt.get('source_sha256')!=hashes['source_sha256'] or rebuilt.get('physical_port_verified') is not False
                    or rebuilt.get('human_accepted') is not False or rows[0].get('source_paths')!=leaf.get('attribute_paths')
                    or snapshot.get('start_node_id')!=leaf['start_node_id'] or snapshot.get('end_node_id')!=leaf['end_node_id']
                    or snapshot.get('attribute_paths')!=leaf.get('attribute_paths')):raise ValueError('rebuilt native block branch evidence differs')
                coverage=projected_coverage(doc,graph,leaf['edge_id'],hashes['source_sha256'])
                if any(s['status']!='single_source_line_covers' for p in coverage for s in p['coverage']['segments']):raise ValueError('rebuilt native block path lacks source coverage')
                # Logical discontinuities are explicitly witnessed omission and
                # inline glyph relations, not zero-length physical pipes.
                result.update(status='native_branch_checks_passed_comparison_pending',ready_for_mapping_comparison=True,
                    coverage=dict(status='native_path_projections_checked',paths=coverage),endpoint_joint_evidence=rows[0]['native_joint_evidence'],
                    omission_evidence=rows[0]['omission'],logical_ownership_basis='original_equipment_identity_with_native_block_chain',physical_ports_verified=False)
                return result
        legacy_circle=(view=='plan' and len(trace['edges'])==1 and index_graph(graph)[0][trace['tee']].get('source_reviewed_circle'))
        if legacy_circle:
            from source_reviewed_circle_branch_evidence import branch_coverage
            leaf=index_graph(graph)[1][trace['edges'][0]]
            result['reviewed_circle_path_evidence']=branch_coverage(doc,graph,leaf,hashes['source_sha256'],hashes['graph_sha256'])
            coverage=dict(edges=[p['coverage'] for p in result['reviewed_circle_path_evidence']['paths']])
        else:
            coverage=audit_paths(doc,graph,dict(hashes,edges=trace['edges']),hashes['source_sha256'],hashes['graph_sha256'])
        result['coverage']=coverage
        unknown={(e['edge_id'],s['index']) for e in coverage['edges'] for s in e['segments'] if s['status']!='single_source_line_covers'}
        if view=='plan':
            edges={e['edge_id']:e for e in graph['edges']};leaf=edges[trace['edges'][0]]
            attachment=leaf.get('confirmed_equipment_interface',{})
            calibrated=leaf.get('source_layout_equipment_interface')
            sideview=leaf.get('source_sideview_equipment_interface')
            if sideview:
                from native_sideview_equipment_branch_evidence import validate_owner
                validate_owner(graph,leaf,hashes['source_sha256'])
                result.update(logical_ownership_basis='source_calibrated_equipment_through_confirmed_sideview',physical_ports_verified=False,source_view_domain='detail_drawing_only_not_plan_metric_proof')
            elif calibrated:
                root=graph.get('sourceLayoutEquipmentOwnership',{});snapshot=calibrated.get('endpoint_snapshot',{})
                ownership_paths=leaf.get('attribute_paths')
                normalization=leaf.get('source_circle_path_normalization')
                if normalization:
                    from normalize_plan_circle_paths import snapshot as circle_snapshot
                    records=graph.get('sourceCirclePathNormalization',{}).get('records',[])
                    if records.count(normalization)!=1 or normalization.get('output_snapshot')!=circle_snapshot(leaf):raise ValueError('circle normalized ownership snapshot differs')
                    previous=normalization['input_snapshot']
                    if any(previous[k]!=leaf.get(k) for k in ('start_node_id','end_node_id','system')):raise ValueError('circle normalization changed logical ownership')
                    ownership_paths=previous['attribute_paths']
                if (calibrated.get('source_sha256')!=hashes['source_sha256'] or calibrated.get('equipment_id')!=equipment
                    or calibrated.get('system')!=system or calibrated.get('human_accepted') is not False
                    or root.get('status')!='native_calibrated_logical_ownership_source_checked'
                    or root.get('records',[]).count(calibrated)!=1
                    or snapshot.get('start_node_id')!=leaf['start_node_id'] or snapshot.get('end_node_id')!=leaf['end_node_id']
                    or snapshot.get('attribute_paths')!=ownership_paths):raise ValueError('plan calibrated logical ownership differs')
                result.update(logical_ownership_basis='source_calibrated_native_layout',physical_ports_verified=False)
            elif attachment.get('source_sha256')!=hashes['source_sha256'] or attachment.get('confirmation',{}).get('confirmed_by')!='user':
                raise ValueError('plan logical equipment ownership not source-confirmed')
            if unknown:raise ValueError('plan branch contains unverified native segments')
        else:
            if len(trace['edges'])!=1:raise ValueError('multi-edge axis chain needs a separate endpoint audit')
            edge=next(e for e in graph['edges'] if e['edge_id']==trace['edges'][0]);chain=edge.get('source_exploded_device_chain') or {}
            keys=('joint_handle','inner_line_handle','outer_line_handle','circle_handle')
            if not all(chain.get(k) for k in keys):raise ValueError('axis endpoint needs supported native joint-chain evidence')
            joint=doc.entitydb.get(chain['joint_handle'])
            if not joint or joint.dxftype()!='INSERT':raise ValueError('axis native joint missing')
            block=doc.blocks[joint.dxf.name]
            spec=dict(equipment_id=equipment,system=system,edge_id=edge['edge_id'],joint_handle=chain['joint_handle'],inner_line=chain['inner_line_handle'],outer_line=chain['outer_line_handle'],circle_handle=chain['circle_handle'])
            joints=audit_joints(doc,graph,inventory,dict(hashes,joint_block=joint.dxf.name,block_fingerprint_sha256=fingerprint(block),selections=[spec]),hashes)
            joints.update({k:hashes[k] for k in ('source_sha256','graph_sha256')})
            digest=lambda value:hashlib.sha256(encode(value)).hexdigest()
            identity=dict(hashes,coverage_sha256=digest(coverage),joints_sha256=digest(joints))
            anchors=classify(graph,coverage,joints,dict(identity,edge_ids=trace['edges']),identity)
            allowed={(r['edge_id'],r['unwitnessed_segment_index']) for r in anchors['records']}
            if unknown!=allowed:raise ValueError('axis has native gaps beyond the audited unknown equipment anchor')
            result.update(endpoint_joint_evidence=joints,unknown_equipment_anchor_evidence=anchors)
        result.update(status='native_branch_checks_passed_comparison_pending',ready_for_mapping_comparison=True)
    except (ValueError,KeyError,TypeError) as exc:result.update(status='source_check_pending',reason=str(exc))
    return result

def build(paths,policy):
    for key in ('plan_source','iso_source','plan_graph','iso_graph','iso_devices'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('stale scope input '+key)
    floor=policy.get('floor');prefix=policy.get('equipment_prefix')
    if isinstance(floor,bool) or not isinstance(floor,int) or not isinstance(prefix,str) or not prefix:raise ValueError('explicit floor and equipment prefix required')
    graphs={v:load(paths[v+'_graph']) for v in ('plan','iso')};docs={};preflight={};indices={};identities={}
    if graphs['iso'].get('sourceNativeBlockBranchReconstruction') or any(e.get('source_native_block_branch') for e in graphs['iso'].get('edges',[])):
        from reconstruct_native_block_branches import verify_output as verify_native_block_branches
        if verify_native_block_branches(Path(paths['iso_graph']).parent)['output_graph_sha256']!=sha(paths['iso_graph']):raise ValueError('native axis block branch stage differs')
    if graphs['plan'].get('sourceSideviewEquipmentOwnership') or any(e.get('source_sideview_equipment_interface') for e in graphs['plan'].get('edges',[])):
        from reconstruct_sideview_equipment_ownership import verify_output as verify_sideview_owner
        if verify_sideview_owner(Path(paths['plan_graph']).parent)['output_graph_sha256']!=sha(paths['plan_graph']):raise ValueError('plan sideview equipment ownership stage differs')
    elif 'sourceCirclePathNormalization' in graphs['plan'] or any('source_circle_path_normalization' in e for e in graphs['plan'].get('edges',[])):
        from normalize_plan_circle_paths import verify_output as verify_circle_paths
        if verify_circle_paths(Path(paths['plan_graph']).parent)['output_graph_sha256']!=sha(paths['plan_graph']):raise ValueError('circle normalized plan differs')
    elif graphs['plan'].get('sourceLayoutEquipmentOwnership') or any(e.get('source_layout_equipment_interface') for e in graphs['plan'].get('edges',[])):
        from calibrated_ownership_scope_composition import verify_ownership_output as verify_ownership
        if verify_ownership(Path(paths['plan_graph']).parent)['output_graph_sha256']!=sha(paths['plan_graph']):raise ValueError('plan calibrated ownership stage differs')
    for view in graphs:
        docs[view],preflight[view]=read_source(paths[view+'_source']);indices[view]=index_graph(graphs[view])[0]
        declared=graphs[view].get('metadata',{}).get('source_sha256')
        # Historical axis graphs omit this optional metadata. Their exact bytes
        # and native source are pinned independently by the policy and replay.
        if declared is not None and declared!=sha(paths[view+'_source']):raise ValueError('graph native source differs')
        identities[view]=dict(source_sha256=sha(paths[view+'_source']),graph_sha256=sha(paths[view+'_graph']),inventory_sha256=sha(paths['iso_devices']))
    with Path(paths['iso_devices']).open(encoding='utf-8-sig',newline='') as stream:inventory=list(csv.DictReader(stream))
    selected=sorted({n['node_id'] for graph in graphs.values() for n in graph['nodes'] if n.get('node_type') in ('equipment','physical_equipment') and n['node_id'].startswith(prefix) and n.get('floor')==floor})
    if not selected:raise ValueError('empty equipment scope')
    records=[]
    for equipment in selected:
        item=dict(equipment_id=equipment,floor=floor,views={},ready_for_mapping_comparison=False)
        for view in graphs:
            node=indices[view].get(equipment)
            captions=[e for e in docs[view].modelspace().query('TEXT MTEXT') if e.plain_text()==equipment]
            if len(captions)!=1:
                item['views'][view]={'status':'missing_or_ambiguous_native_caption'};continue
            caption=_caption(docs[view],captions[0].dxf.handle,equipment)
            if not node or node.get('node_type') not in ('equipment','physical_equipment') or node.get('floor')!=floor:
                candidates=unresolved_identity_candidates(docs[view],graphs[view],equipment,floor)
                item['views'][view]=dict(status='unresolved_equipment_identity_candidates' if candidates else 'missing_or_floor_conflicting_equipment',caption=caption,retained_native_equipment_candidates=candidates)
                continue
            hashes=identities[view]
            services={s:inspect_branch(docs[view],graphs[view],equipment,s,hashes,view,inventory) for s in ('supply','return')}
            item['views'][view]=dict(status='native_caption_read',caption=caption,services=services)
        item['ready_for_mapping_comparison']=all(item['views'][v].get('services',{}).get(s,{}).get('ready_for_mapping_comparison',False) for v in graphs for s in ('supply','return'))
        records.append(item)
    dependencies={name:sha(Path(__file__).with_name(name)) for name in ('native_sideview_equipment_branch_evidence.py','reconstruct_sideview_equipment_ownership.py','native_confirmed_equipment_pair_circle_evidence.py','source_reviewed_circle_branch_evidence.py','source_reviewed_circle_connections.py','correct_plan_crossover_lengths.py','native_circle_rim_junction_evidence.py','native_path_coverage_audit.py','native_line_path_evidence.py','cad_ceiling_native_rules.py','reconstruct_native_block_branches.py','source_readability.py')}
    return dict(status='source_comparison_inventory_not_mapping',records=records,source_preflight=preflight,source_evidence_implementation_sha256=dependencies,
        counts=dict(equipment=len(records),ready_for_mapping_comparison=sum(r['ready_for_mapping_comparison'] for r in records)),
        local_graphs_mutated=False,mapped_paths=0,human_accepted=False,hil_ready=False,
        limitations=['Native branch checks are prerequisites, not correspondence or DN/length acceptance.','Captions, floor and graph adjacency do not alone establish physical equipment ports.','Unsupported branches remain explicit; no nearest-equipment assignment or graph deletion.'])

def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'inventory-receipt.json')
    if receipt['implementation_sha256']!=sha(Path(__file__)):raise ValueError('stale inventory implementation')
    for key,item in receipt['inputs'].items():
        if sha(item['path'])!=item['sha256']:raise ValueError('stale inventory input '+key)
    paths={k:v['path'] for k,v in receipt['inputs'].items() if k!='policy'}
    result=build(paths,load(receipt['inputs']['policy']['path']))
    if encode(result)!=(directory/'inventory.json').read_bytes() or sha(directory/'inventory.json')!=receipt['output_sha256']:raise ValueError('native inventory replay differs')
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ('plan-source','iso-source','plan-graph','iso-graph','iso-devices','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args();paths={k:getattr(args,k) for k in ('plan_source','iso_source','plan_graph','iso_graph','iso_devices')}
    if args.output.exists():raise FileExistsError(args.output)
    result=build(paths,load(args.policy));args.output.mkdir(parents=True)
    (args.output/'inventory.json').write_bytes(encode(result));paths['policy']=args.policy
    receipt=dict(inputs={k:dict(path=str(Path(v).resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=sha(Path(__file__)),output_sha256=sha(args.output/'inventory.json'))
    (args.output/'inventory-receipt.json').write_bytes(encode(receipt));print(json.dumps(result['counts']))

if __name__=='__main__':main()
