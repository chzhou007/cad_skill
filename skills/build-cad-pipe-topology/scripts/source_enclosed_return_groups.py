"""Attach source-enclosure graph groups without asserting device ownership or new connections."""
import copy,math,collections
from ezdxf import bbox
from ezdxf.disassemble import recursive_decompose

def attach(graph,doc,devices,records,source_sha,graph_sha):
 g=copy.deepcopy(graph);nodes={n['node_id']:n for n in g['nodes']};edges={e['edge_id']:e for e in g['edges']}
 if not source_sha or not graph_sha or g.get('metadata',{}).get('original_dxf_sha256')!=source_sha:raise ValueError('source identity mismatch; caller must independently verify the graph hash and strict source readability')
 if len(nodes)!=len(g['nodes']) or len(edges)!=len(g['edges']) or not records:raise ValueError('duplicate graph IDs or missing source evidence')
 used_nodes=set();used_edges=set();used_devices=set();groups=[]
 for r in records:
  tower=nodes.get(r['tower_id']);cells=r['original_02_cell_handles'];tag=doc.entitydb.get(r['original_02_tag_handle'])
  if not tower or tower.get('node_type')!='equipment' or tower.get('source_tag_handle')!=r['original_02_tag_handle'] or not tag or tag.dxftype()!='TEXT' or tag.dxf.text!=tower['node_id'] or len(cells)!=2 or len(set(cells))!=2:raise ValueError('source equipment identity mismatch')
  boxes=[]
  for handle in cells:
   e=doc.entitydb.get(handle)
   if not e or e.dxftype()!='INSERT' or e.dxf.name!='LT':raise ValueError('source cell mismatch')
   box=bbox.extents(list(recursive_decompose([e])))
   if not box.has_data:raise ValueError('missing native cell extent')
   boxes.append([box.extmin.x,box.extmin.y,box.extmax.x,box.extmax.y])
  bounds=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
  if len(tower.get('source_bounds',[]))!=4 or any(abs(a-b)>.01 for a,b in zip(tower['source_bounds'],bounds)):raise ValueError('source enclosure mismatch')
  x1,y1,x2,y2=bounds;inside={nid for nid,n in nodes.items() if nid!=tower['node_id'] and x1<n['x']<x2 and y1<n['y']<y2 and n.get('system')=='cooling_return'}
  group_edges=[e for e in g['edges'] if e.get('system')=='cooling_return' and e['start_node_id'] in inside and e['end_node_id'] in inside];eids={e['edge_id'] for e in group_edges}
  if len(inside)!=9 or len(eids)!=9 or r['internal_junction_id'] not in inside or len([n for n in inside if nodes[n]['node_type']=='tee'])!=5 or len([n for n in inside if nodes[n]['node_type']=='virtual_equipment'])!=4:raise ValueError('return graph signature mismatch')
  for e in group_edges:
   if not e.get('source_handles') or any((doc.entitydb.get(h) is None or doc.entitydb[h].dxftype()!='LINE' or doc.entitydb[h].dxf.layer!='HVAC-D-CWR') for h in e['source_handles']):raise ValueError('return source path mismatch')
   if not e.get('path_points') or any(not(x1-.01<=p[0]<=x2+.01 and y1-.01<=p[1]<=y2+.01) for p in e['path_points']):raise ValueError('return edge leaves native enclosure')
  adj=collections.defaultdict(set)
  for e in group_edges:adj[e['start_node_id']].add(e['end_node_id']);adj[e['end_node_id']].add(e['start_node_id'])
  stack=[r['internal_junction_id']];reached=set()
  while stack:
   nid=stack.pop()
   if nid in reached:continue
   reached.add(nid);stack.extend(adj[nid]-reached)
  if reached!=inside:raise ValueError('source enclosure return group is disconnected')
  external=[e for e in g['edges'] if (e['start_node_id'] in inside)!=(e['end_node_id'] in inside)]
  if len(external)!=1 or external[0]['edge_id']!=r['current_edge_id'] or external[0]['system']!='cooling_return':raise ValueError('external return boundary mismatch')
  members=[x for x in devices if x['edge_id'] in eids];names={d['device_name'] for d in members}
  if len(names)!=8 or len(members)!=8 or collections.Counter(d['equipment_type'] for d in members)!={'Butterfly Valve':4,'Metal Flexible Joint':4}:raise ValueError('component group mismatch')
  if used_nodes&inside or used_edges&eids or used_devices&names:raise ValueError('overlapping candidate groups')
  used_nodes.update(inside);used_edges.update(eids);used_devices.update(names)
  group={'group_id':'ENCLOSED-RETURN-'+tower['node_id'],'tower_node_id':tower['node_id'],'entry_edge_id':external[0]['edge_id'],'node_ids':sorted(inside),'edge_ids':sorted(eids),'component_names':sorted(names),'source_cell_handles':cells,'source_tag_handle':r['original_02_tag_handle'],'source_enclosure':bounds,'source_sha256':source_sha,'source_graph_sha256':graph_sha,'status':'source_enclosure_group_candidate_not_bound','semantics':'Drawing containment and existing same-service connectivity only; equipment ownership, physical ports and remote terminal connections remain unverified.','expert_review':'unreviewed'}
  tower['source_enclosed_return_group']=group;groups.append(group)
 if len(groups)!=len(records):raise ValueError('incomplete groups')
 g['metadata'].update(hil_ready=False,graph_complete=False,stage_status='source_enclosed_return_groups_pending_ownership')
 return g,groups
