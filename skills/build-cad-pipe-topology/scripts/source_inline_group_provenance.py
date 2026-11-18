"""Attach primary-line and reference-symbol provenance to existing source groups."""
import copy

def attach(graph,evidence,source_sha256,graph_sha256):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256 or evidence.get('source_sha256')!=source_sha256 or evidence.get('graph_sha256')!=graph_sha256:raise ValueError('Stale provenance evidence')
 if not evidence.get('primary_dxf_sha256') or not evidence.get('reference_dxf_sha256'):raise ValueError('Missing source identity')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']};records={r['group_id']:r for r in evidence['records']};groups=out.get('sourceInlineEndpointGroups',[])
 if len(records)!=len(evidence['records']) or len(records)!=len(groups):raise ValueError('Incomplete or duplicate evidence')
 for group in groups:
  r=records.get(group['group_id']);e=edges.get(group['edge_id'])
  if not r or not e or r['edge_id']!=group['edge_id'] or r['normalized_insert_handle']!=group['source_insert_handle'] or sorted(r['endpoint_node_ids'])!=sorted(group['endpoint_node_ids']):raise ValueError('Group identity changed')
  lines=r['primary_source_lines']
  if sorted(x['normalized_handle'] for x in lines)!=sorted(e.get('source_handles',[])) or any(not x.get('primary_polyline_handle') for x in lines) or r.get('individual_primary_proxy_identity')!='not_established':raise ValueError('Line provenance or proxy status mismatch')
  prov={'primary_dxf_sha256':evidence['primary_dxf_sha256'],'primary_line_handles':sorted({x['primary_polyline_handle'] for x in lines}),'reference_dxf_sha256':evidence['reference_dxf_sha256'],'reference_insert_handle':r['reference_insert_handle'],'reference_block_name':r['reference_block_name'],'reference_geometry_matches':True,'individual_primary_proxy_identity':'not_established'}
  group['source_provenance']=copy.deepcopy(prov)
  for nid in group['endpoint_node_ids']:
   if nodes[nid].get('source_inline_endpoint_group',{}).get('group_id')!=group['group_id']:raise ValueError('Node group changed')
   nodes[nid]['source_inline_endpoint_group']['source_provenance']=copy.deepcopy(prov)
  if e.get('source_inline_endpoint_group',{}).get('group_id')!=group['group_id']:raise ValueError('Edge group changed')
  e['source_inline_endpoint_group']['source_provenance']=copy.deepcopy(prov)
 return out,{'groups':len(groups),'reference_component_groups':len(groups),'primary_pipe_groups':len(groups),'proxy_individual_mappings_proven':0,'physical_edges_created':0}
