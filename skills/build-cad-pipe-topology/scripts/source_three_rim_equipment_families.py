"""Group calibrated same-service three-rim source shapes without merging pipes."""
import copy,math

def attach(graph,doc,evidence,source_sha256,graph_sha256):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256 or evidence.get('source_sha256')!=source_sha256 or evidence.get('graph_sha256')!=graph_sha256:raise ValueError('Stale source or graph')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};used=set();groups=[];adj={k:[] for k in nodes}
 for e in out['edges']:
  for nid in (e['start_node_id'],e['end_node_id']):adj[nid].append(e)
 for r in evidence['records']:
  circle=doc.entitydb.get(r['circle_handle']);supply=doc.entitydb.get(r['supply_tangent_circles'][0]['handle']) if len(r['supply_tangent_circles'])==1 else None
  if not circle or circle.dxftype()!='CIRCLE' or not supply or supply.dxftype()!='CIRCLE' or circle.dxf.layer!='暖通-冷冻水回水管' or supply.dxf.layer!='暖通-冷冻水供水管':raise ValueError('Source circle mismatch')
  a=circle.ocs().to_wcs(circle.dxf.center);b=supply.ocs().to_wcs(supply.dxf.center)
  if abs(circle.dxf.radius-85)>.01 or abs(supply.dxf.radius-85)>.01 or abs(math.dist((a.x,a.y),(b.x,b.y))-170)>.01:raise ValueError('Source circle geometry mismatch')
  ids=sorted(x['node_id'] for x in r['rim_nodes']);actual=sorted(n['node_id'] for n in out['nodes'] if abs(math.dist((n['x'],n['y']),(a.x,a.y))-circle.dxf.radius)<.01)
  if len(ids)!=3 or ids!=actual or used.intersection(ids):raise ValueError('Circle rim membership is not unique')
  equipment=[];edge_ids=[]
  for nid in ids:
   n=nodes[nid];inc=adj[nid]
   if n.get('boundary_type')!='unresolved_source_terminal' or n.get('system')!='return' or len(inc)!=1 or inc[0]['system']!='return':raise ValueError('Rim node system or degree mismatch')
   edge=inc[0];other=edge['end_node_id'] if edge['start_node_id']==nid else edge['start_node_id'];edge_ids.append(edge['edge_id'])
   if nodes[other].get('node_type')=='equipment':equipment.append(other)
   hit=[]
   for h in edge.get('source_handles',[]):
    line=doc.entitydb.get(h)
    if not line or line.dxftype()!='LINE' or line.dxf.layer!=circle.dxf.layer:continue
    p=line.ocs().to_wcs(line.dxf.start);q=line.ocs().to_wcs(line.dxf.end)
    if min(math.dist((n['x'],n['y']),(z.x,z.y)) for z in (p,q))<.01:hit.append(h)
   if len(hit)!=1:raise ValueError('No unique native source pipe endpoint')
  if len(equipment)!=1:raise ValueError('Equipment connection not unique')
  group={'group_id':'F1-RETURN-CIRCLE-'+r['circle_handle'],'return_circle_handle':r['circle_handle'],'tangent_supply_circle_handle':supply.dxf.handle,'rim_node_ids':ids,'edge_ids':sorted(edge_ids),'equipment_id':equipment[0],'status':'source_three_rim_semantics_pending','hydraulic_connection_confirmed':False,'cross_system_connection_confirmed':False}
  for nid in ids:nodes[nid]['source_three_rim_family']=copy.deepcopy(group)
  nodes[equipment[0]].setdefault('source_three_rim_families',[]).append(copy.deepcopy(group));used.update(ids);groups.append(group)
 if out['edges']!=graph['edges']:raise ValueError('Hydraulic edges changed')
 out['sourceThreeRimEquipmentFamilies']=groups
 return out,{'groups':len(groups),'return_rim_endpoints':len(used),'equipment_nodes':len(groups),'hydraulic_edges_created':0}
