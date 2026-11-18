"""Rebind a source terminal inventory after graph edge reconstruction."""
import collections

def rebind(records,graph):
    nodes={n['node_id']:n for n in graph['nodes']};adj=collections.defaultdict(list)
    for edge in graph['edges']:
        for node_id in (edge['start_node_id'],edge['end_node_id']):adj[node_id].append(edge)
    fixed=[];changes=[]
    for row in records:
        node=nodes.get(row['node_id']);matches=adj[row['node_id']]
        if node is None or node['node_type']!='virtual_equipment' or len(matches)!=1:
            raise ValueError('Terminal must still be a unique virtual degree-one source boundary: '+row['node_id'])
        edge=matches[0];evidence={r['handle']for r in row.get('source',[])} & set(edge.get('source_handles',[]))
        if not evidence:raise ValueError('Terminal and reconstructed edge lack matching native source handle: '+row['node_id'])
        record=dict(row,previous_edge_id=row['edge_id'],edge_id=edge['edge_id'],edge_length=edge['path_length'])
        fixed.append(record)
        if row['edge_id']!=edge['edge_id']:
            changes.append({'node_id':row['node_id'],'previous_edge_id':row['edge_id'],'current_edge_id':edge['edge_id'],'source_handles_matched':sorted(evidence)})
    return fixed,changes
