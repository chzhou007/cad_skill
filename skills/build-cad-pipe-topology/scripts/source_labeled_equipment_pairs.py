"""Group two label-linked service endpoints at one already verified equipment."""
import copy

def attach(graph,source_sha256):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256:raise ValueError('Source identity mismatch')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};used=set();groups=[]
 for r in out.get('sourceAnnotationReferenceGroups',[]):
  endpoints=r.get('endpoint_node_ids',[])
  if len(endpoints)!=2 or len(set(endpoints))!=2:raise ValueError('Expected two distinct local endpoints')
  services={};equipment_ids=set();target_edges=set()
  for nid in endpoints:
   n=nodes.get(nid);ref=n.get('source_annotation_reference',{}) if n else {};adj=[e for e in out['edges'] if nid in (e['start_node_id'],e['end_node_id'])]
   if not n or nid in used or len(adj)!=1 or ref.get('label')!=r['label'] or ref.get('hydraulic_connection_confirmed') is not False:raise ValueError('Invalid source endpoint reference')
   edge=adj[0];system=edge.get('system');other=edge['end_node_id'] if edge['start_node_id']==nid else edge['start_node_id'];eq=nodes.get(other,{})
   if system not in ('supply','return') or system in services or eq.get('node_type')!='equipment' or ref.get('system')!=system:raise ValueError('Equipment or service mismatch')
   ports=[p for p in eq.get('source_ports',[]) if p.get('edge_id')==edge['edge_id'] and p.get('system')==system and p.get('status')=='applied']
   if len(ports)!=1:raise ValueError('Equipment port is not uniquely source bound')
   services[system]={'endpoint_node_id':nid,'equipment_edge_id':edge['edge_id'],'equipment_port_id':ports[0].get('port_id'),'annotated_target_edge_id':ref['target_edge_id']};equipment_ids.add(other);target_edges.add(ref['target_edge_id']);used.add(nid)
  if len(equipment_ids)!=1 or set(services)!={'supply','return'} or target_edges!=set(r.get('target_edge_ids',[])):raise ValueError('Group endpoints or targets inconsistent')
  eid=next(iter(equipment_ids));group={'group_id':'SOURCE-LABEL-'+r['label'],'label':r['label'],'equipment_id':eid,'source_note_handle':r['source_note_handle'],'services':services,'status':'source_annotated_pair_route_pending','hydraulic_connection_confirmed':False}
  if nodes[eid].get('source_labeled_equipment_pair'):raise ValueError('Equipment claimed by multiple label groups')
  for nid in [eid]+endpoints:nodes[nid]['source_labeled_equipment_pair']=copy.deepcopy(group)
  groups.append(group)
 if out['edges']!=graph['edges']:raise ValueError('Edges changed')
 out['sourceLabeledEquipmentGroups']=groups
 return out,{'groups':len(groups),'endpoint_nodes':len(used),'equipment_nodes':len(groups),'hydraulic_edges_created':0}
