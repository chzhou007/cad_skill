"""Classify an existing source frontier from independently replayed cap evidence.

Node IDs, equipment, edges and all source geometry survive. This is a source
interface role, not a newly connected device, pipe span or human acceptance.
"""
import copy
from edge_endpoint_semantics import reconcile

MODE='source_declared_capped_branch_roles_v1'


def apply(graph,inventory,graph_sha256,inventory_sha256):
    if (inventory.get('mode')!='native_capped_branch_annotation_witness_v1' or inventory.get('graph_sha256')!=graph_sha256
        or inventory.get('source_sha256')!=graph.get('metadata',{}).get('source_sha256') or inventory.get('graph_mutated') is not False
        or inventory.get('connections_added')!=0 or inventory.get('physical_lengths_assigned')!=0):raise ValueError('current native caption evidence required')
    records=inventory.get('records')
    if not records or len({r['node_id'] for r in records})!=len(records):raise ValueError('empty or duplicate source roles')
    g=copy.deepcopy(graph);nodes={n['node_id']:n for n in g['nodes']};edges={e['edge_id']:e for e in g['edges']};changes=[]
    if len(nodes)!=len(g['nodes']) or len(edges)!=len(g['edges']):raise ValueError('duplicate source graph identities')
    if 'sourceDeclaredCappedBranchInterfaces' in g:raise ValueError('source cap roles already present')
    for record in records:
        node=nodes.get(record['node_id']);edge=edges.get(record['edge_id'])
        if (not node or node.get('node_type')!='virtual_equipment' or node.get('subtype')!='unresolved_source_terminal'
            or node.get('boundary_type')!='unresolved_source_terminal' or node.get('resolution_state')
            or node.get('source_endpoint_annotation') or node.get('source_declared_connection') or node.get('ports')):
            raise ValueError('frontier already has conflicting source role, route or ports')
        incident=[e for e in g['edges'] if node['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))]
        if len(incident)!=1 or edge is not incident[0] or node.get('system')!=record['system'] or edge.get('system')!=record['system']:
            raise ValueError('source cap is not the uniquely witnessed same-system leaf')
        geometry=record['source_geometry'];pipe=geometry['source_pipe_handle'];p=geometry['source_pipe_endpoints'][0]
        if pipe not in node.get('source_handles',[]) or pipe not in edge.get('source_handles',[]) or abs(node['x']-p[0])>.05 or abs(node['y']-p[1])>.05:
            raise ValueError('source cap frontier geometry differs')
        side='start' if edge.get('start_node_id')==node['node_id'] else 'end'
        if edge.get(side+'_port_id') or any(p.get('node_id')==node['node_id'] for p in g.get('virtual_equipment_ports',[])):
            raise ValueError('explicit port requires a separate reconciliation')
        if (record.get('status')!='native_caption_leader_marker_frontier_witness_only' or record.get('role')!='reserved_capped_branch_annotation'
            or record.get('physical_connection_assigned') is not False or record.get('physical_length_mm') is not None
            or record.get('quantity_expanded_into_ports') is not False or record['qualifier'].get('text')!='盲板封堵'):
            raise ValueError('unsupported source declaration or physical claim')
        before=copy.deepcopy(node)
        node.update(previous_boundary_type=node['boundary_type'],boundary_type='source_declared_capped_branch_interface',
            subtype='source_declared_capped_branch_interface',resolution_state='native_reserved_capped_interface_role',
            label='预留接口（盲板封堵）',review_required=False,connection_status='source_declared_capped_interface_no_remote_route_assigned',
            source_declared_capped_branch=copy.deepcopy(record),human_accepted=False)
        changes.append(dict(node_id=node['node_id'],edge_id=edge['edge_id'],parent_node_snapshot=before,
            source_role='reserved_capped_branch_interface',role_evidence='explicit_native_caption_leader_marker_frontier',
            remote_equipment_or_port_identity='unknown',physical_length_mm=None,human_accepted=False))
    g,endpoint_changes=reconcile(g)
    if [n['node_id'] for n in g['nodes']]!=[n['node_id'] for n in graph['nodes']] or len(g['edges'])!=len(graph['edges']):raise ValueError('source role stage changed graph identities')
    selected={r['node_id'] for r in records};selected_edges={r['edge_id'] for r in records}
    if any(n!=nodes[n['node_id']] for n in g['nodes']):raise ValueError('unexpected reconciliation changed nodes')
    before_nodes={n['node_id']:n for n in graph['nodes']}
    if any(n!=before_nodes[n['node_id']] for n in g['nodes'] if n['node_id'] not in selected):raise ValueError('unselected node changed')
    for before,after in zip(graph['edges'],g['edges']):
        allowed={'endpoint_semantics'} if before['edge_id'] in selected_edges else set()
        if {k:v for k,v in before.items() if k not in allowed}!={k:v for k,v in after.items() if k not in allowed}:raise ValueError('source interface role changed physical edges or unrelated endpoint semantics')
    g['sourceDeclaredCappedBranchInterfaces']=dict(mode=MODE,source_sha256=inventory['source_sha256'],input_graph_sha256=graph_sha256,
        annotation_inventory_sha256=inventory_sha256,records=changes,nodes_retired=0,connections_added=0,physical_lengths_assigned=0,
        equipment_or_ports_created=0,human_accepted=False)
    g['derivedEvidenceInvalidation']=dict(previous=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),
        reason='native source declared capped interface role; no geometric or connectivity change',affected_nodes=sorted(selected),affected_edges=sorted(selected_edges),
        recompute=['source_comparison','graph_bound_mapping_receipts','graph_bound_attribute_receipts','human_acceptance'])
    g['metadata'].update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_source_capped_interface_role')
    return g,dict(classified_interfaces=len(changes),node_ids_retained=True,source_geometry_retained=True,connections_added=0,
        nodes_retired=0,physical_lengths_assigned=0,endpoint_type_changes=endpoint_changes,human_accepted=False)
