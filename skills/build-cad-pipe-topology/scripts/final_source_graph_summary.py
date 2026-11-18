"""Refresh final graph counts while preserving explicitly scoped extraction metrics."""
import copy,csv,hashlib,io,json
from collections import Counter
from pathlib import Path
from edge_endpoint_semantics import reconcile

BASE_FIELDS=('nodes','edges','tee_nodes','equipment_nodes','virtual_equipment_nodes','unresolved_degree1_network_vertices',
             'inline_components_detected','inline_components_assigned','inline_components_unresolved',
             'source_line_length','accepted_edge_covered_length','accepted_edge_length_coverage')
def digest(raw):return hashlib.sha256(raw).hexdigest()


def refresh(summary,graph_path):
    graph_path=Path(graph_path).resolve();devices=graph_path.parent/'assigned_edge_device_instances.csv'
    graph_raw=graph_path.read_bytes();csv_raw=devices.read_bytes();graph=json.loads(graph_raw.decode('utf-8-sig'))
    nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']}
    if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']):raise ValueError('final summary graph has duplicate IDs')
    try:reconcile(graph)
    except ValueError as error:raise ValueError('final summary endpoint semantics invalid or dangling: '+str(error)) from error
    source_hash=graph.get('metadata',{}).get('source_sha256')
    if summary.get('source_sha256') is not None and source_hash!=summary['source_sha256']:raise ValueError('final summary source differs from extraction')
    degree=Counter()
    for edge in edges.values():
        for key in ('start_node_id','end_node_id'):
            if edge.get(key) is not None:degree[edge[key]]+=1
    rows=list(csv.DictReader(io.StringIO(csv_raw.decode('utf-8-sig'),newline='')))
    if any(not r.get('device_name') or r.get('edge_id') not in edges for r in rows) or len({r['device_name'] for r in rows})!=len(rows):
        raise ValueError('final summary canonical components are orphaned or duplicated')
    types=Counter(n.get('node_type') or 'unknown' for n in nodes.values())
    unresolved=[nid for nid,n in nodes.items() if n.get('subtype')=='unresolved_source_terminal' or n.get('boundary_type')=='unresolved_source_terminal']
    counts=dict(nodes=len(nodes),edges=len(edges),tee_nodes=types['tee']+types['physical_junction'],equipment_nodes=types['equipment']+types['physical_equipment'],
        virtual_equipment_nodes=types['virtual_equipment']+types['virtual_interface'],
        unresolved_degree1_network_vertices=sum(degree[nid]==1 for nid in unresolved))
    result=copy.deepcopy(summary)
    result.setdefault('base_extraction_summary',{key:copy.deepcopy(summary[key]) for key in BASE_FIELDS if key in summary})
    result.update(counts)
    result.update(final_graph=str(graph_path),final_graph_sha256=digest(graph_raw),final_canonical_components=len(rows),
        final_graph_counts=dict(counts,unresolved_source_terminal_nodes=len(unresolved),boundary_anchors=len(graph.get('boundary_anchors',[])),canonical_components=len(rows),node_types=dict(types)),
        final_component_table_sha256=digest(csv_raw),final_summary_entry_sha256=digest(Path(__file__).read_bytes()),
        final_hil_ready=graph.get('metadata',{}).get('hil_ready'),source_coverage_scope='base_extraction_summary_only_not_final_edge_coverage',
        inline_extraction_counts_scope='base_extraction_summary')
    if graph_path.read_bytes()!=graph_raw or devices.read_bytes()!=csv_raw:raise ValueError('final summary inputs changed during reading')
    return result
