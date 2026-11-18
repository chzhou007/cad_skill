"""Bind source-pinned expert wave INSERTs to existing one-edge boundaries."""
import math
from ezdxf import bbox

def attach(doc,nodes,edges,policy,source_sha256):
 if not policy:return [],[]
 if policy.get('source_sha256')!=source_sha256 or not policy.get('expert_issue'):raise ValueError('wave source hash or expert evidence mismatch')
 specs=policy.get('terminals',[]);handles=[x['insert_handle'] for x in specs]
 if not handles or len(set(handles))!=len(handles):raise ValueError('duplicate or missing wave scope')
 glyphs=[];audit=[]
 for spec in specs:
  ins=doc.entitydb.get(spec['insert_handle']);line=doc.entitydb.get(spec['line_handle']);system=spec['system'];tol=float(policy['contact_tolerance'])
  if not 0<tol<=.5 or ins is None or ins.dxftype()!='INSERT' or ins.dxf.name!=policy['block_name'] or ins.dxf.owner!=doc.modelspace().block_record_handle:raise ValueError('wave insert identity mismatch')
  if line is None or line.dxftype()!='LINE' or line.dxf.layer!=spec['line_layer']:raise ValueError('wave source line mismatch')
  virtual=list(ins.virtual_entities())
  if len(virtual)!=1 or virtual[0].dxftype()!='LWPOLYLINE':raise ValueError('wave native geometry mismatch')
  box=bbox.extents(virtual)
  hits=[n for n in nodes if n.get('subtype')=='unresolved_source_terminal' and n.get('system')==system and spec['line_handle'] in n.get('source_handles',[]) and min(math.hypot(p.x-n['x'],p.y-n['y']) for p in (line.dxf.start,line.dxf.end))<=tol and box.extmin.x-tol<=n['x']<=box.extmax.x+tol and box.extmin.y-tol<=n['y']<=box.extmax.y+tol]
  if len(hits)!=1:raise ValueError('wave terminal missing or ambiguous')
  n=hits[0];nid=n['node_id'];adj=[e for e in edges if nid in (e['start_node_id'],e['end_node_id'])]
  if len(adj)!=1 or adj[0]['system']!=system or spec['line_handle'] not in adj[0]['source_handles']:raise ValueError('wave terminal not uniquely attached')
  edge=adj[0];side='start' if edge['start_node_id']==nid else 'end';port=nid+'-P1'
  if edge.get(side+'_port_id'):raise ValueError('wave endpoint already has a port')
  edge[side+'_port_id']=port;gid='WAVE-INSERT-'+spec['insert_handle']
  n.update(subtype='native_transverse_wave_interface',boundary_type='source_native_wave_terminal',label='Source wavy end-mark interface '+nid,interface_kind_zh='原图横向波形管端标识',resolution_state='source_boundary_identified_remote_continuation_not_shown',review_queue='source_boundary_inventory',review_required=False,remote_continuation_confirmed=False,ports=[{'port_id':port,'system':system,'x':n['x'],'y':n['y'],'source_marker_handle':spec['insert_handle']}],source_terminal_glyph_ids=[gid],source_wave_insert_evidence={'source_handle':spec['insert_handle'],'block_name':ins.dxf.name,'source_line_handle':spec['line_handle'],'contact_tolerance':tol,'source_sha256':source_sha256,'expert_issue':policy['expert_issue'],'remote_continuation_confirmed':False})
  glyphs.append({'id':gid,'kind':'native_insert_wave_terminal','source_handles':[spec['insert_handle']],'node_id':nid,'edge_id':edge['edge_id'],'floor':n['floor'],'system':system,'remote_continuation_confirmed':False})
  audit.append({'node_id':nid,'edge_id':edge['edge_id'],'system':system,'source_line_handle':spec['line_handle'],'source_wave_insert':spec['insert_handle'],'remote_continuation_confirmed':False})
 return glyphs,audit
