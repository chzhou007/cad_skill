"""Convert explicitly user-confirmed source glyph leaf endpoints to typed boundaries."""
import argparse,copy,csv,hashlib,json,math,shutil
from pathlib import Path
from edge_endpoint_semantics import reconcile
from source_readability import read_source

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def convert(doc,graph,manifest,signatures,confirmation,policy):
 if confirmation.get('answer')!='都是非节点边界，类似于管道变径，连接着末端空调':raise ValueError('confirmation mismatch')
 if manifest.get('source_sha256')!=policy['source_sha256'] or manifest.get('graph_sha256')!=policy['graph_sha256'] or signatures.get('source_sha256')!=policy['source_sha256'] or signatures.get('graph_sha256')!=policy['graph_sha256']:raise ValueError('source evidence is stale')
 if signatures.get('review_manifest_sha256')!=policy['manifest_sha256']:raise ValueError('signature evidence is stale')
 specs=signatures['rows']; scopes=policy['circle_handles']
 if len(scopes)!=len(set(scopes)) or set(scopes)!={x['circle_handle'] for x in specs} or len(specs)!=len(scopes):raise ValueError('scope mismatch')
 m={x['circle_handle']:x for x in manifest['rows']};g=copy.deepcopy(graph);nodes={x['node_id']:x for x in g['nodes']};anchors={x['boundary_id']:x for x in g.get('boundary_anchors',[])};edges={x['edge_id']:x for x in g['edges']};retired=set();changes=[]
 if len(nodes)!=len(g['nodes']) or len(edges)!=len(g['edges']) or len(anchors)!=len(g.get('boundary_anchors',[])):raise ValueError('duplicate IDs')
 for s in specs:
  old=m.get(s['circle_handle']); circle=doc.entitydb.get(s['circle_handle']);edge=edges.get(s['edge_id']);gid=s['graph_id'];obj=nodes.get(gid) or anchors.get(gid)
  if not old or old['graph_id']!=gid or old['edge_id']!=s['edge_id'] or not obj or not edge or not circle or circle.dxftype()!='CIRCLE' or circle.dxf.layer!=old['source_layer'] or abs(circle.dxf.radius-s['radius'])>.01:raise ValueError('source/graph mismatch')
  if edge.get('system')!=s['system'] or obj.get('system')!=s['system']:raise ValueError('system mismatch')
  c=circle.dxf.center
  for l in s['symbol_lines']:
   entity=doc.entitydb.get(l['handle'])
   if not entity or entity.dxftype()!='LINE' or entity.dxf.layer!='空调立管、水平支管':raise ValueError('glyph source mismatch')
   actual=[[round(v.x-c.x,3),round(v.y-c.y,3),round(v.z-c.z,3)] for v in (entity.dxf.start,entity.dxf.end)]
   if actual!=l['relative_xyz']:raise ValueError('glyph geometry changed')
  pipe=doc.entitydb.get(s['connected_native_pipe']['handle'])
  if not pipe or pipe.dxftype()!='LINE' or pipe.dxf.layer!=old['source_layer'] or pipe.dxf.handle not in edge.get('source_handles',[]):raise ValueError('pipe evidence mismatch')
  near=min((pipe.dxf.start,pipe.dxf.end),key=lambda v:math.hypot(v.x-c.x,v.y-c.y))
  if abs(math.hypot(near.x-c.x,near.y-c.y)-s['connected_native_pipe']['xy_offset'])>.00001 or abs(near.z-c.z-s['connected_native_pipe']['relative_z'])>.00001:raise ValueError('pipe/glyph offsets changed')
  if gid in anchors:
   if obj.get('source_circle_handle')!=s['circle_handle'] or obj.get('source_pipe_handle')!=pipe.dxf.handle:raise ValueError('existing boundary mismatch')
   obj.update(destination_kind='terminal_air_conditioning_equipment',destination_instance='unknown',destination_port='unknown',destination_evidence='user_confirmed_terminal_air_conditioner',user_confirmation_sha256=policy['confirmation_sha256']);changes.append({'circle_handle':s['circle_handle'],'boundary_id':gid,'action':'destination_clarified'});continue
  incident=[e for e in edges.values() if gid in (e.get('start_node_id'),e.get('end_node_id'))]
  if len(incident)!=1 or incident[0] is not edge or obj.get('node_type')!='virtual_equipment' or obj.get('subtype') not in ('out_of_plane_interface','unresolved_source_terminal'):raise ValueError('not a unique supported leaf')
  side='start' if edge.get('start_node_id')==gid else 'end';pid=edge.get(side+'_port_id');ports=obj.get('ports',[])
  if pid and (len(ports)!=1 or ports[0].get('port_id')!=pid or ports[0].get('system')!=edge['system']):raise ValueError('port mapping inconsistent')
  if not pid and ports:raise ValueError('unbound node port')
  if any(p.get('node_id')==gid for p in g.get('virtual_equipment_ports',[])):raise ValueError('external port mapping requires separate handling')
  if any(gid in json.dumps(pair,ensure_ascii=False) for pair in g.get('sourceDetailComparison',{}).get('pairs',[])):raise ValueError('candidate mapping requires separate rebase')
  aid='A-'+gid
  if aid in nodes or aid in anchors:raise ValueError('boundary collision')
  edge[side+'_node_id']=None;edge[side+'_boundary_id']=aid
  if pid:edge.pop(side+'_port_id')
  anchor={'boundary_id':aid,'kind':'user_confirmed_non_node_source_boundary','system':s['system'],'x':obj['x'],'y':obj['y'],'source_pipe_handle':pipe.dxf.handle,'source_circle_handle':s['circle_handle'],'source_glyph_handles':[x['handle'] for x in s['symbol_lines']],'legacy_node':copy.deepcopy(obj),'legacy_edge_port_id':pid,'destination_kind':'terminal_air_conditioning_equipment','destination_instance':'unknown','destination_port':'unknown','destination_evidence':'user_confirmed_terminal_air_conditioner','user_confirmation_sha256':policy['confirmation_sha256'],'human_acceptance':'scope_confirmed_not_full_graph_review'}
  g.setdefault('boundary_anchors',[]).append(anchor);anchors[aid]=anchor;retired.add(gid);changes.append({'circle_handle':s['circle_handle'],'input_node_id':gid,'boundary_id':aid,'edge_id':edge['edge_id'],'legacy_port_id':pid,'action':'node_to_non_node_boundary'})
 g['nodes']=[n for n in g['nodes'] if n['node_id'] not in retired];g,semantic_changes=reconcile(g)
 g['userConfirmedTerminalBoundaryRepair']={'source_sha256':policy['source_sha256'],'input_graph_sha256':policy['graph_sha256'],'confirmation_sha256':policy['confirmation_sha256'],'review_manifest_sha256':policy['manifest_sha256'],'changes':changes,'scope':'selected source boundaries only; terminal equipment identity remains unknown','hil_ready':False}
 return g,changes,semantic_changes

def main():
 p=argparse.ArgumentParser()
 for x in ('source','graph','devices','manifest','signatures','confirmation','policy','output'):p.add_argument('--'+x,type=Path,required=True)
 a=p.parse_args();policy=json.loads(a.policy.read_text(encoding='utf8'))
 for name,path in [('source_sha256',a.source),('graph_sha256',a.graph),('devices_sha256',a.devices),('manifest_sha256',a.manifest),('signatures_sha256',a.signatures),('confirmation_sha256',a.confirmation)]:
  if sha(path)!=policy[name]:raise ValueError(name+' mismatch')
 manifest=json.loads(a.manifest.read_text(encoding='utf8'))
 for image in manifest['images']:
  if sha(image['path'])!=image['sha256']:raise ValueError('review image changed')
 doc,proof=read_source(a.source);g,changes,sem=convert(doc,json.loads(a.graph.read_text(encoding='utf8')),manifest,json.loads(a.signatures.read_text(encoding='utf8')),json.loads(a.confirmation.read_text(encoding='utf8')),policy)
 a.output.mkdir(parents=True,exist_ok=False);target=a.output/'graph_with_typed_boundaries.json';target.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv');audit={'source_sha256':sha(a.source),'input_graph_sha256':sha(a.graph),'output_graph_sha256':sha(target),'devices_sha256':sha(a.devices),'policy_sha256':sha(a.policy),'confirmation_sha256':sha(a.confirmation),'changes':changes,'semantic_changes':sem,'source_preflight':proof,'human_acceptance':'selected_boundary_semantics_only','hil_ready':False};(a.output/'boundary-stage.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'changed':len(changes),'converted':sum(x['action']=='node_to_non_node_boundary' for x in changes),'hil_ready':False}))
if __name__=='__main__':main()
