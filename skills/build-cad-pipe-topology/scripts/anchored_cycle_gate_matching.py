"""Match cycle attachment Ts using independent known boundary identities.

Partition at known Ts, retaining every edge in the original graphs. Simple
unknown cycle blocks may have different numbers of internal branches. Only
unique attachment gates are paired; cycle interiors remain unassigned.
"""
from collections import Counter, defaultdict
from crossview_equipment_branch_inventory import index_graph

TYPES = {'tee', 'physical_junction'}


def cycle_blocks(adj):
    depth, low, stack, found = {}, {}, [], []
    def visit(n, parent=None):
        depth[n] = low[n] = len(depth)
        for v, eid in sorted(adj[n]):
            if eid == parent:
                continue
            if v not in depth:
                stack.append((n, v, eid)); visit(v, eid)
                low[n] = min(low[n], low[v])
                if low[v] >= depth[n]:
                    block = []
                    while stack:
                        item = stack.pop(); block.append(item)
                        if item[2] == eid:
                            break
                    degrees = Counter(x for a, b, _ in block for x in (a, b))
                    if len(block) >= 3 and all(d == 2 for d in degrees.values()):
                        found.append(block)
            elif depth[v] < depth[n]:
                stack.append((n, v, eid)); low[n] = min(low[n], depth[v])
    for n in sorted(adj):
        if n not in depth:
            visit(n)
    return found


def collect(graph, mapping, floor, system):
    nodes, edges, full = index_graph(graph)
    eligible = {n for n, row in nodes.items()
                if row.get('floor') == floor and row['node_type'] in TYPES
                and row.get('review_required') is not True and len(full[n]) == 3
                and {e['system'] for e in full[n]} == {system}}
    adj, unknown = defaultdict(list), defaultdict(list)
    for eid, edge in edges.items():
        a, b = edge['start_node_id'], edge['end_node_id']
        if edge['system'] != system or not {a, b} <= eligible or a == b:
            continue
        adj[a].append((b, eid)); adj[b].append((a, eid))
        if a not in mapping and b not in mapping:
            unknown[a].append((b, eid)); unknown[b].append((a, eid))
    results = []
    for cycle in cycle_blocks(unknown):
        cn = {n for a, b, _ in cycle for n in (a, b)}
        ce = {eid for _, _, eid in cycle}
        gates = {}
        for gate in sorted(cn):
            q, seen, labels = [gate], {gate}, set()
            for current in q:
                if current in mapping:
                    labels.add(mapping[current]); continue
                for peer, eid in adj[current]:
                    if eid not in ce and peer not in seen and peer not in cn:
                        seen.add(peer); q.append(peer)
            if labels:
                gates[gate] = sorted(labels)
        signature = sorted({v for labels in gates.values() for v in labels})
        if len(signature) >= 2:
            results.append(dict(signature=signature, gates=gates,
                                cycle_nodes=sorted(cn), cycle_edges=sorted(ce)))
    return sorted(results, key=lambda r: r['cycle_edges'])


def discover(graphs, mapping, floor):
    if set(graphs) != {'plan', 'iso'} or type(floor) is not int:
        raise ValueError('explicit two-view integer floor required')
    indexes = {v:index_graph(g) for v, g in graphs.items()}
    if len(mapping) != len(set(mapping.values())):
        raise ValueError('independent anchors collapse')
    if any(p not in indexes['plan'][0] or a not in indexes['iso'][0] for p,a in mapping.items()):
        raise ValueError('independent anchor absent from current graph')
    groups, pending, pairs, inverse = [], [], {}, {}
    for system in ('supply', 'return'):
        cycles = {v:collect(g, mapping if v=='plan' else {a:a for a in mapping.values()}, floor, system)
                  for v,g in graphs.items()}
        for plan in cycles['plan']:
            pp = [c for c in cycles['plan'] if c['signature']==plan['signature']]
            aa = [c for c in cycles['iso'] if c['signature']==plan['signature']]
            if len(pp)!=1 or len(aa)!=1:
                pending.append(dict(floor=floor,system=system,reason='missing_or_multiple_anchor_cycle_blocks',plan=plan,axis_candidates=aa)); continue
            axis = aa[0]; new = {}
            for pn, signature in plan['gates'].items():
                ps = [n for n,s in plan['gates'].items() if s==signature]
                ans = [n for n,s in axis['gates'].items() if s==signature]
                if len(ps)!=1 or len(ans)!=1:
                    pending.append(dict(floor=floor,system=system,reason='nonunique_cycle_gate_signature',signature=signature)); continue
                an=ans[0]
                if pn in mapping or an in mapping.values():
                    raise ValueError('cycle gate competes with independent anchor')
                if pn in pairs and pairs[pn]!=an or an in inverse and inverse[an]!=pn:
                    raise ValueError('cycle gate identities compete')
                pairs[pn]=an; inverse[an]=pn; new[pn]=an
            groups.append(dict(floor=floor,system=system,plan=plan,iso=axis,new_junction_mapping=new,
                               interior_branch_counts_equal=len(plan['cycle_nodes'])==len(axis['cycle_nodes']),
                               interior_node_identities_assigned=False))
    return dict(groups=groups,pending=pending,new_junction_mapping=dict(sorted(pairs.items())),
                graph_mutated=False,DN_used_for_matching=False,coordinates_used_for_matching=False,
                shortest_path_used=False,interior_node_identities_assigned=False,human_accepted=False)
