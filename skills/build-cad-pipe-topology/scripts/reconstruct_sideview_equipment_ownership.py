"""Bind logical equipment through confirmed view aliases; preserve native paths."""
import argparse,copy,hashlib,importlib,json,math,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from edge_endpoint_semantics import reconcile
from source_sideview_equipment_owner_evidence import collect
from calibrated_equipment_interface_ownership import calibration
from source_readability import read_source

MODE='source_calibrated_confirmed_sideview_equipment_ownership_v1'
SCOPE_FIELDS=('path_length_scope','drawing_path_length','physical_length_status','physical_length','path_length_complete')

def apply(graph,evidence,policy,source_hash,graph_hash):
    if (evidence.get('source_sha256')!=source_hash or evidence.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash
        or evidence.get('topology_mutated') is not False or evidence.get('human_accepted') is not False or graph.get('sourceSideviewEquipmentOwnership')):raise ValueError('sideview owner input/scope changed or already applied')
    selected=evidence['selected'];ids=[r['candidate_owner'] for r in selected]
    if (not selected or len(ids)!=len(set(ids)) or len(ids)!=policy.get('expected_equipment_bindings')
        or set(ids)!=set(policy.get('equipment_ids',[])) or len(ids)!=len(policy['equipment_ids'])):raise ValueError('explicit complete supported owner scope required; do not override competition')
    out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']};anchors={b['boundary_id']:b for b in out.get('boundary_anchors',[])}
    if len(nodes)!=len(out['nodes']) or len(edges)!=len(out['edges']) or len(anchors)!=len(out.get('boundary_anchors',[])):raise ValueError('duplicate sideview topology identities')
    root=graph['confirmedSideviewCanonicalization']
    if evidence.get('sideview_root_sha256')!=hashlib.sha256(encode(root)).hexdigest():raise ValueError('confirmed sideview alias history changed')
    retired_nodes={};retired_anchors={};records=[];node_aliases={};boundary_aliases={};claimed=set()
    for row in selected:
        if row not in evidence['records'] or row.get('status')!='calibrated_owner_through_confirmed_sideview_not_applied':raise ValueError('owner is not a globally supported candidate')
        did=row['candidate_owner'];owner=nodes[did];native_owner=row['native_layout_evidence']['proposed_owner']
        if owner.get('node_type')!='equipment' or owner.get('source_handle')!=native_owner['equipment_handle'] or any(did in (e.get('start_node_id'),e.get('end_node_id')) for e in graph['edges']):raise ValueError('existing equipment ownership requires reconciliation')
        bounds=native_owner['native_body_bounds']
        if isinstance(owner.get('floor'),bool) or not isinstance(owner.get('floor'),int) or math.dist([owner['x'],owner['y']],[(bounds[0]+bounds[1])/2,(bounds[2]+bounds[3])/2])>.05:raise ValueError('calibrated equipment body/floor changed')
        endpoints=row['canonical_endpoints']
        if len(endpoints)!=2 or {r['system'] for r in endpoints}!={'supply','return'}:raise ValueError('sideview equipment needs independent paired services')
        for endpoint in endpoints:
            eid=endpoint['canonical_edge'];nid=endpoint['canonical_interface'];kind=endpoint['canonical_interface_kind'];side=endpoint['canonical_side'];edge=edges[eid]
            if eid in claimed or any(edge.get(k) for k in ('source_layout_equipment_interface','source_sideview_equipment_interface','confirmed_equipment_interface','cross_view_attributes')):raise ValueError('sideview branch already owned or fused')
            claimed.add(eid)
            if edge['system']!=endpoint['system'] or owner.get('floor') not in (edge.get('start_floor'),edge.get('floor_start')) or owner.get('floor') not in (edge.get('end_floor'),edge.get('floor_end')):raise ValueError('sideview source service/floor changed')
            if edge.get('equipment_connector_length_mm') is not None or edge.get('physical_length') not in (None,'unknown'):raise ValueError('measured connector/length requires explicit reconciliation')
            if kind=='node':
                original=nodes[nid]
                if original.get('node_type')!='virtual_equipment' or edge.get(side+'_node_id')!=nid or sum(nid in (e.get('start_node_id'),e.get('end_node_id')) for e in edges.values())!=1 or nid in retired_nodes:raise ValueError('canonical interface is not a unique virtual endpoint')
                retired_nodes[nid]=copy.deepcopy(original);node_aliases[nid]=did
            elif kind=='non_node_boundary':
                original=anchors[nid]
                if edge.get(side+'_node_id') is not None or edge.get(side+'_boundary_id')!=nid or sum(nid in (e.get('start_boundary_id'),e.get('end_boundary_id')) for e in edges.values())!=1 or nid in retired_anchors:raise ValueError('canonical non-node boundary is not a unique endpoint')
                retired_anchors[nid]=copy.deepcopy(original);boundary_aliases[nid]=did
            else:raise ValueError('unsupported canonical endpoint role')
            direct_floor=original.get('floor');legacy_floor=original.get('legacy_node',{}).get('floor')
            if direct_floor is not None and legacy_floor is not None and direct_floor!=legacy_floor:raise ValueError('source boundary floor evidence conflicts')
            endpoint_floor=direct_floor if direct_floor is not None else legacy_floor
            if original.get('system')!=edge['system'] or endpoint_floor!=owner.get('floor'):raise ValueError('source alias endpoint service/floor differs')
            floor_evidence=dict(floor=endpoint_floor,source='canonical_endpoint' if direct_floor is not None else 'preserved_boundary_legacy_node',legacy_node_id=original.get('legacy_node',{}).get('node_id'))
            prior={k:copy.deepcopy(edge[k]) for k in SCOPE_FIELDS if k in edge}
            edge[side+'_node_id']=did;edge.pop(side+'_boundary_id',None);edge.pop(side+'_port_id',None)
            edge.update(physical_length='unknown',path_length_complete=False,equipment_connector_length_mm=None,equipment_connector_length_status='unshown_source_view_to_equipment_unknown')
            lineage=copy.deepcopy(edge.get('length_scope_evidence',[]))
            if not isinstance(lineage,list):raise ValueError('unknown previous length lineage schema')
            lineage.extend([dict(kind='inherited_sideview_edge_scope',source_graph_sha256=graph_hash,edge_id=eid,properties=prior),dict(kind='confirmed_sideview_logical_equipment_link',source_graph_sha256=graph_hash,edge_id=eid,equipment_id=did,physical_length_mm=None,physical_port_verified=False)])
            edge['length_scope_evidence']=lineage
            proof=dict(equipment_id=did,edge_id=eid,system=edge['system'],interface_side=side,original_canonical_interface_id=nid,original_canonical_interface_kind=kind,original_canonical_endpoint=copy.deepcopy(original),
                source_sha256=source_hash,input_graph_sha256=graph_hash,question_id=row['question_id'],pair_sha256=row['pair_sha256'],sideview_root_sha256=evidence['sideview_root_sha256'],calibration_sha256=evidence['calibration_sha256'],endpoint_floor_evidence=floor_evidence,
                body_evidence=copy.deepcopy(native_owner),source_alias=copy.deepcopy(endpoint),prior_edge_length_scope=prior,physical_port_verified=False,interface_to_equipment_length_known=False,human_accepted=False,
                endpoint_snapshot=dict(start_node_id=edge.get('start_node_id'),end_node_id=edge.get('end_node_id'),start_boundary_id=edge.get('start_boundary_id'),end_boundary_id=edge.get('end_boundary_id'),equipment_xy=[owner['x'],owner['y']],equipment_source_handle=owner['source_handle'],system=edge['system'],attribute_paths=copy.deepcopy(edge['attribute_paths'])))
            edge['source_sideview_equipment_interface']=proof;records.append(proof)
        owner.update(connection_status='source_calibrated_sideview_equipment_physical_ports_unknown',source_sideview_interface_ids=[r['canonical_interface'] for r in endpoints])
    # Mark all proved detail paths, including unresolved owners, as drawing
    # coordinates. Millimetre INSUNITS do not establish a detail's physical scale.
    detail_ids=set()
    for alias in root['records']:
        detail_ids.add(alias['canonical_edge']);detail_ids.update(alias['verified_detail_tee']['incident_edges'])
    for eid in sorted(detail_ids):
        if eid not in edges:raise ValueError('detail main changed and needs fresh source review')
        prior=edges[eid].get('source_view_context')
        if prior is not None:raise ValueError('existing source view role requires reconciliation')
        edges[eid]['source_view_context']=dict(kind='confirmed_detail_view',coordinate_domain='native_detail_drawing',source_sha256=source_hash,input_graph_sha256=graph_hash,confirmed_alias_root_sha256=evidence['sideview_root_sha256'],physical_length_from_drawing_span=False,metric_verified_by_this_stage=False)
    retired=set(retired_nodes)
    out['nodes']=[n for n in out['nodes'] if n['node_id'] not in retired];out['boundary_anchors']=[a for a in out.get('boundary_anchors',[]) if a['boundary_id'] not in retired_anchors]
    ports=[p for p in out.get('virtual_equipment_ports',[]) if p.get('virtual_equipment_id') in retired or p.get('node_id') in retired]
    out['virtual_equipment_ports']=[p for p in out.get('virtual_equipment_ports',[]) if p not in ports]
    glyphs=[p for p in out.get('sourceTerminalGlyphs',[]) if p.get('node_id') in retired]
    if 'sourceTerminalGlyphs' in out:out['sourceTerminalGlyphs']=[p for p in out['sourceTerminalGlyphs'] if p not in glyphs]
    out,changes=reconcile(out);after={e['edge_id']:e for e in out['edges']}
    for record in records:after[record['edge_id']]['source_sideview_equipment_interface']=record
    out['sourceSideviewEquipmentOwnership']=dict(mode=MODE,source_sha256=source_hash,input_graph_sha256=graph_hash,source_evidence_sha256=hashlib.sha256(encode(evidence)).hexdigest(),records=records,
        node_aliases=node_aliases,boundary_aliases=boundary_aliases,retired_interface_nodes=[retired_nodes[k] for k in sorted(retired_nodes)],retired_boundary_anchors=[retired_anchors[k] for k in sorted(retired_anchors)],retired_virtual_ports=ports,retired_display_glyphs=glyphs,
        detail_edge_ids=sorted(detail_ids),supply_return_independent=True,equipment_instances_conserved=True,physical_ports_verified=False,human_accepted=False)
    out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_confirmed_sideview_equipment_ownership')
    out['derivedEvidenceInvalidation']=dict(previous_invalidation=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),reason='confirmed view aliases and native calibration changed logical equipment endpoints; native paths preserved',recompute=['local_source_comparison','crossview_mapping','diameter_inheritance','length_fusion','human_acceptance'],historical_annotations_preserved=True)
    return out,dict(records=records,endpoint_type_changes=changes,retired_node_ids=sorted(retired_nodes),retired_non_node_boundaries=sorted(retired_anchors),detail_edge_ids=sorted(detail_ids))

def compute(paths,policy):
    for key in ('source','graph','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('sideview owner input changed '+key)
    from calibrated_ownership_scope_composition import verify_ownership_output
    parent=verify_ownership_output(Path(paths['graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['graph']) or parent['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('sideview owner parent/components differ')
    doc,preflight=read_source(paths['source']);graph=load(paths['graph']);model=calibration(doc,graph,policy['calibration']);evidence=collect(doc,graph,model,sha(paths['source']),sha(paths['graph']))
    out,proof=apply(graph,evidence,policy,sha(paths['source']),sha(paths['graph']))
    return out,dict(proof,source_preflight=preflight,calibration=model,source_evidence=evidence,parent_graph=dict(path=str(Path(paths['graph']).resolve()),sha256=sha(paths['graph'])))

def implementation_hashes():
    names=('reconstruct_sideview_equipment_ownership','source_sideview_equipment_owner_evidence','canonicalize_confirmed_sideviews','calibrated_equipment_interface_ownership','calibrated_ownership_scope_composition','edge_endpoint_semantics','source_readability')
    return {name+'.py':sha(Path(importlib.import_module(name).__file__)) for name in names}

def verify_output(directory):
    directory=Path(directory);audit=load(directory/'sideview-equipment-ownership-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('sideview owner implementation changed')
    for spec in audit['inputs'].values():
        if sha(spec['path'])!=spec['sha256']:raise ValueError('sideview owner dependency changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};graph,proof=compute(paths,load(paths['policy']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or any(audit.get(k)!=v for k,v in proof.items()):raise ValueError('sideview owner native replay differs')
    if (directory/'assigned_edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('sideview canonical component bytes changed')
    return audit

def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','devices','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();paths={k:getattr(a,k) for k in ('source','graph','devices','policy')}
    if a.output.exists():raise FileExistsError(a.output)
    graph,audit=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
    (a.output/'sideview-owner-source-evidence.json').write_bytes(encode(audit['source_evidence']))
    audit.update(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'sideview-equipment-ownership-audit.json').write_bytes(encode(audit));print(json.dumps(dict(equipment=len({r['equipment_id'] for r in audit['records']}),service_links=len(audit['records']),nodes=len(graph['nodes']),edges=len(graph['edges']),physical_ports_verified=False,human_accepted=False)))

if __name__=='__main__':main()
