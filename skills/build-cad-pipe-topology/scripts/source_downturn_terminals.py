"""Attach a locally calibrated, labelled circle-centre downturn boundary.

The native drawing and legend must already have passed strict readability and
per-contact audit. This records a local symbol only, never a remote hydraulic
connection, floor assignment or physical elevation.
"""
import collections,copy,math

def reconcile(graph,evidence,source_sha256,graph_sha256,legend_sha256):
    if (evidence.get('source_sha256'),evidence.get('graph_sha256'),evidence.get('legend_sha256'))!=(source_sha256,graph_sha256,legend_sha256):
        raise ValueError('Stale source, graph or legend evidence')
    legend=evidence.get('legend',{})
    if legend.get('text')!='向下转弯' or not all(legend.get(k) for k in ('text_handle','circle_handle','line_handle')):
        raise ValueError('A readable labelled native project legend is required')
    records=evidence.get('records',[])
    if len(records)!=evidence.get('total') or sum(bool(r.get('matches_complete_local_legend_signature')) for r in records)!=evidence.get('local_signature_pass'):
        raise ValueError('Incomplete source audit')
    if len({r['node_id'] for r in records})!=len(records) or len({r['circle_handle']for r in records})!=len(records):
        raise ValueError('Competing or duplicate source owners')
    out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']};adj=collections.defaultdict(list)
    for edge in out['edges']:
        for nid in (edge['start_node_id'],edge['end_node_id']):adj[nid].append(edge)
    applied=[];glyphs=out.setdefault('sourceTerminalGlyphs',[])
    owned_handles={h for glyph in glyphs for h in glyph.get('source_handles',[])}
    for row in records:
        if not row.get('matches_complete_local_legend_signature'):continue
        n=nodes.get(row['node_id']);e=edges.get(row['edge_id']);hits=row.get('pipe_hits',[])
        if not n or not e or n.get('node_type')!='virtual_equipment' or len(adj[n['node_id']])!=1 or adj[n['node_id']][0]['edge_id']!=e['edge_id']:
            raise ValueError('Native local boundary is not a unique current graph endpoint')
        if n.get('interface_destination') or n.get('source_glyph_evidence') or n.get('source_terminal_glyph_ids'):
            raise ValueError('Existing semantic or glyph ownership must be preserved')
        if row['circle_handle'] in owned_handles:raise ValueError('Source circle is already owned')
        if len(hits)!=1 or hits[0]['handle'] not in e.get('source_handles',[]) or row.get('other_same_layer_overlapping_entities'):
            raise ValueError('Incomplete or competing local source line evidence')
        radius=row.get('radius_native',25.) # v12 audited a single explicit 25-unit family
        if not isinstance(radius,(int,float)) or not math.isfinite(radius) or radius<=0:
            raise ValueError('A positive calibrated native radius is required')
        if min(hits[0]['endpoint_distances'])>=.01 or max(hits[0]['endpoint_distances'])<=radius:
            raise ValueError('Source line must terminate at circle center and extend outside')
        n.update(subtype='native_downturn_interface',boundary_type='source_native_downturn_terminal',
                 label='Original drawing downturn '+n['node_id'],interface_kind_zh='原图向下转弯符号',
                 resolution_state='local_symbol_identified_remote_continuation_not_shown',review_queue='source_boundary_inventory',
                 review_required=False,remote_continuation_confirmed=False,
                 source_downturn_evidence={'circle_handle':row['circle_handle'],'source_layer':row['source_layer'],
                   'pipe_handle':hits[0]['handle'],'radius_native':radius,'legend_text':legend['text'],'legend_text_handle':legend['text_handle'],
                   'legend_circle_handle':legend['circle_handle'],'legend_line_handle':legend['line_handle'],
                   'source_sha256':source_sha256,'source_graph_sha256':graph_sha256,'legend_sha256':legend_sha256,
                   'scope':'Native symbol role only; actual remote identity and physical elevation unverified.'})
        glyphid='DOWNTURN-'+row['circle_handle'];n['source_terminal_glyph_ids']=[glyphid]
        glyphs.append({'id':glyphid,'source_handles':[row['circle_handle']],'node_id':n['node_id'],'edge_id':e['edge_id'],
                       'floor':n['floor'],'system':e['system'],'kind':'native_downturn_terminal',
                       'role':'Project legend downward bend symbol at a source boundary; remote identity is unconfirmed.',
                       'remote_continuation_confirmed':False})
        owned_handles.add(row['circle_handle'])
        applied.append(n['node_id'])
    return out,{'applied_count':len(applied),'node_ids':applied,'edges_unchanged':out['edges']==graph['edges'],
                'remote_connections_inferred':0,'source_sha256':source_sha256,'source_graph_sha256':graph_sha256,'legend_sha256':legend_sha256}
