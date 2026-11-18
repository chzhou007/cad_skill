"""Revalidate tangent-circle evidence against a later graph without linking systems."""
import copy
from source_tangent_circle_candidates import attach

NODE_FIELDS=('node_id','node_type','boundary_type','system','floor','x','y','ports','source_terminal_glyph_ids')
EDGE_FIELDS=('edge_id','system','start_node_id','end_node_id','source_handles','path_points','attribute_paths')

def apply(graph, inventory, reference, evidence, doc, policy, *, source_sha256,
          graph_sha256, inventory_sha256, reference_sha256, evidence_sha256):
 checks={'graph source':graph.get('metadata',{}).get('source_sha256')==source_sha256,
         'reference source':reference.get('metadata',{}).get('source_sha256')==source_sha256,
         'inventory source':inventory.get('source_sha256')==source_sha256,
         'inventory graph':inventory.get('graph_sha256')==graph_sha256,
         'evidence source':evidence.get('source_sha256')==source_sha256,
         'evidence reference':evidence.get('graph_sha256')==reference_sha256,
         'policy source':policy.get('source_sha256')==source_sha256,
         'policy target':policy.get('target_graph_sha256')==graph_sha256,
         'policy reference':policy.get('reference_graph_sha256')==reference_sha256,
         'policy evidence':policy.get('evidence_sha256')==evidence_sha256,
         'policy inventory':policy.get('inventory_sha256')==inventory_sha256}
 failed=[k for k,v in checks.items() if not v]
 if failed:raise ValueError('Source, graph, inventory or evidence hash mismatch: '+', '.join(failed)+
                            '; target='+str(graph_sha256)+'; inventory='+str(inventory_sha256))
 def index(rows,key):
  result={r[key]:r for r in rows}
  if len(result)!=len(rows):raise ValueError('Duplicate graph identity')
  return result
 n=index(graph['nodes'],'node_id');oldn=index(reference['nodes'],'node_id')
 e=index(graph['edges'],'edge_id');olde=index(reference['edges'],'edge_id')
 records=evidence.get('records',[]);ids=[];edge_ids=[]
 for record in records:
  for system in ('supply','return'):
   item=record[system];nid=item['node_id'];eid=item['edge_id'];ids.append(nid);edge_ids.append(eid)
   if nid not in n or nid not in oldn or eid not in e or eid not in olde:
    raise ValueError('Recorded tangent witness missing from graph')
   if any(n[nid].get(k)!=oldn[nid].get(k) for k in NODE_FIELDS):raise ValueError('Tangent node witness changed: '+nid)
   if any(e[eid].get(k)!=olde[eid].get(k) for k in EDGE_FIELDS):raise ValueError('Tangent edge witness changed: '+eid)
 if not ids or len(ids)!=len(set(ids)) or len(edge_ids)!=len(set(edge_ids)):
  raise ValueError('Empty or duplicated tangent witnesses')
 rows=inventory.get('records',[]);byid={}
 for row in rows:byid.setdefault(row.get('node_id'),[]).append(row)
 for nid,eid in zip(ids,edge_ids):
  if len(byid.get(nid,[]))!=1 or byid[nid][0].get('edge_id')!=eid:
   raise ValueError('Tangent terminal inventory witness mismatch: '+nid)
 rebased=copy.deepcopy(evidence);rebased['graph_sha256']=graph_sha256
 out,audit=attach(graph,rebased,doc,source_sha256,graph_sha256)
 inv=copy.deepcopy(inventory);out_nodes=index(out['nodes'],'node_id')
 for row in inv['records']:
  if row['node_id'] in ids:
   row['source_tangent_circle_candidate']=copy.deepcopy(out_nodes[row['node_id']]['source_tangent_circle_candidate'])
 out['metadata'].update(hil_ready=False,stage_status='f2_tangent_source_geometry_recorded_remote_semantics_pending')
 gate=out.setdefault('preHilComparison',{'status':'pending','families':[]});gate['status']='pending'
 gate.setdefault('families',[]).append({'id':'f2-tangent-circle-source-pairs','status':'algorithm_pending',
  'source_handles':[h for pair in out['sourceTangentCircleCandidates'] for h in pair['source_circle_handles']],
  'disposition':'Source tangent pairs are separately recorded; tangency does not connect systems and remote routes remain unresolved.'})
 audit.update(source_sha256=source_sha256,input_graph_sha256=graph_sha256,reference_graph_sha256=reference_sha256,
              evidence_sha256=evidence_sha256,input_inventory_sha256=inventory_sha256,hil_ready=False)
 return out,inv,audit
