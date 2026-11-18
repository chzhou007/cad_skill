"""Source-bound two-dimensional endpoint contact audit for tower enclosure groups."""
import copy,math
from ezdxf.disassemble import recursive_decompose

def _line_distance(x,y,a,b):
 dx=b.x-a.x;dy=b.y-a.y;l=dx*dx+dy*dy;t=max(0,min(1,((x-a.x)*dx+(y-a.y)*dy)/l)) if l else 0
 return math.hypot(x-a.x-t*dx,y-a.y-t*dy)

def analyze(graph,doc,design_doc,source_sha,design_sha,graph_sha):
 if not all((source_sha,design_sha,graph_sha)) or graph.get('metadata',{}).get('original_dxf_sha256')!=source_sha:raise ValueError('source identity mismatch; caller must verify hashes and strict readability')
 note=design_doc.entitydb.get('143')
 if not note or note.dxftype() not in ('TEXT','MTEXT'):raise ValueError('source design note missing')
 text=note.plain_text() if note.dxftype()=='MTEXT' else note.dxf.text
 if '冷却塔与管道间采用软连接方式' not in text:raise ValueError('source design note changed')
 nodes={n['node_id']:n for n in graph['nodes']};lines=list(doc.modelspace().query('LINE'));circles=list(doc.modelspace().query('CIRCLE'));rows=[];seen=set()
 for tower in graph['nodes']:
  group=tower.get('source_enclosed_return_group')
  if not group:continue
  if group.get('source_sha256')!=source_sha or group.get('status')!='source_enclosure_group_candidate_not_bound':raise ValueError('group source identity or role mismatch')
  primitives=[]
  for handle in group['source_cell_handles']:
   entity=doc.entitydb.get(handle)
   if not entity or entity.dxftype()!='INSERT' or entity.dxf.name!='LT':raise ValueError('native tower cell missing')
   for e in recursive_decompose([entity]):
    if e.dxftype() in ('LINE','CIRCLE'):primitives.append((handle,e))
    elif e.dxftype()=='LWPOLYLINE':
     for v in e.virtual_entities():
      if v.dxftype() not in ('LINE','CIRCLE'):raise ValueError('unhandled tower polyline primitive')
      primitives.append((handle,v))
    else:raise ValueError('unhandled native tower primitive '+e.dxftype())
  members=[nodes.get(i) for i in group['node_ids']]
  if any(n is None for n in members):raise ValueError('group node missing')
  ends=[n for n in members if n['node_type']=='virtual_equipment']
  if len(ends)!=4:raise ValueError('unexpected endpoint count')
  for n in ends:
   nid=n['node_id'];x,y=n['x'],n['y'];incident=[e for e in graph['edges'] if nid in (e['start_node_id'],e['end_node_id'])]
   if nid in seen or len(incident)!=1 or incident[0]['edge_id'] not in group['edge_ids'] or incident[0]['system']!='cooling_return':raise ValueError('endpoint incidence changed')
   nearest=[]
   for handle,e in primitives:
    if e.dxftype()=='LINE':distance=_line_distance(x,y,e.dxf.start,e.dxf.end)
    else:distance=abs(math.hypot(x-e.dxf.center.x,y-e.dxf.center.y)-e.dxf.radius)
    nearest.append((distance,handle,e.dxftype()))
   if not nearest:raise ValueError('missing native equipment geometry')
   value,handle,kind=min(nearest);hits=[{'handle':e.dxf.handle,'layer':e.dxf.layer} for e in lines if _line_distance(x,y,e.dxf.start,e.dxf.end)<.1]
   if not hits or not any(h['handle'] in incident[0]['source_handles'] for h in hits):raise ValueError('pipe source contact missing')
   markers=[{'handle':c.dxf.handle,'layer':c.dxf.layer,'radius':c.dxf.radius,'center_distance_2d':math.hypot(x-c.dxf.center.x,y-c.dxf.center.y)} for c in circles if math.hypot(x-c.dxf.center.x,y-c.dxf.center.y)<.1]
   # Detect a distinct circle intersecting the endpoint whose center lies on an
   # incident native line.  Endpoint-only center matching misses this form.
   other=[]
   for c in circles:
    center=c.dxf.center;distance=math.hypot(x-center.x,y-center.y)
    if distance<.1 or distance>c.dxf.radius:continue
    witnesses=[h['handle'] for h in hits if h['handle'] in incident[0]['source_handles'] and h['layer']==c.dxf.layer and _line_distance(center.x,center.y,doc.entitydb[h['handle']].dxf.start,doc.entitydb[h['handle']].dxf.end)<.1]
    if witnesses:other.append({'handle':c.dxf.handle,'layer':c.dxf.layer,'radius':c.dxf.radius,'endpoint_to_center_2d':distance,'line_handles':witnesses,'meaning':'source_geometry_only_unresolved'})
   rows.append({'tower_id':tower['node_id'],'node_id':nid,'edge_id':incident[0]['edge_id'],'point':[x,y],'nearest_cell_handle':handle,'nearest_primitive_type':kind,'nearest_primitive_distance_2d':value,'source_line_contacts':hits,'source_centered_circles':markers,'source_overlapping_circle_line_witnesses':other,'source_design_note_handle':'143','source_design_sha256':design_sha,'source_sha256':source_sha,'source_graph_sha256':graph_sha,'status':'source_2d_comparison_no_port_binding','distance_scope':'2D drawing distance to displayed source cell primitives; not installed pipe length or elevation','remote_connection':'unconfirmed'});seen.add(nid)
 return rows

def attach(graph,rows):
 g=copy.deepcopy(graph);nodes={n['node_id']:n for n in g['nodes']}
 for r in rows:
  n=nodes.get(r['node_id'])
  if not n or n.get('source_tower_terminal_comparison'):raise ValueError('missing or duplicate endpoint')
  n['source_tower_terminal_comparison']=copy.deepcopy(r)
 for n in g['nodes']:
  if n.get('source_enclosed_return_group'):
   n['source_tower_design_requirement']={'source_handle':'143','text':'冷却塔与管道间采用软连接方式','status':'project_design_statement_not_port_binding','source_sha256':rows[0]['source_design_sha256']}
 g['metadata'].update(hil_ready=False,graph_complete=False,stage_status='source_tower_terminal_comparison_pending')
 return g
