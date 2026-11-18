"""Inventory calibrated paired source terminal symbols near equipment bodies.

Geometric screening only. No terminal-to-device ownership or cross-system
connection is inferred, and no graph mutation is performed.
"""
import argparse,collections,hashlib,json,math
from pathlib import Path
from source_readability import read_source
from cad_ceiling_native_rules import match_out_of_plane_symbol
from native_equipment_body import body_straight_segments,point_segment_distance
LAYERS={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}

def candidate_pairs(interfaces,distance,tol):
 if not math.isfinite(distance) or distance<=0 or not math.isfinite(tol) or tol<=0:raise ValueError('invalid calibrated pair distance')
 supply=[x for x in interfaces if x['system']=='supply'];ret=[x for x in interfaces if x['system']=='return'];pairs=[]
 for a in ret:
  for b in supply:
   spacing=math.dist((a['x'],a['y']),(b['x'],b['y']))
   if abs(spacing-distance)<=tol:pairs.append({'return_node':a['node_id'],'supply_node':b['node_id'],'spacing_drawing_units':spacing,'return_xy':[a['x'],a['y']],'supply_xy':[b['x'],b['y']],'status':'geometry_pair_not_a_connection'})
 frequency=collections.Counter(k for p in pairs for k in (p['return_node'],p['supply_node']))
 for p in pairs:p['terminal_pairing_ambiguous']=frequency[p['return_node']]>1 or frequency[p['supply_node']]>1
 return pairs

def scan(doc,graph,policy,source_hash,graph_hash):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('source or graph identity mismatch')
 spacing=policy['pair_spacing'];tol=policy['pair_tolerance'];radius=policy['body_search_radius']
 if not math.isfinite(radius) or radius<=0:raise ValueError('invalid search radius')
 nodes=graph['nodes'];ids={n['node_id']:n for n in nodes}
 if len(ids)!=len(nodes):raise ValueError('duplicate node id')
 interfaces=[n for n in nodes if n.get('subtype')=='out_of_plane_interface'];degrees=collections.Counter(n for e in graph['edges'] for n in (e.get('start_node_id'),e.get('end_node_id')) if n)
 for n in interfaces:
  h=n.get('source_handle');circle=doc.entitydb.get(h);handles=n.get('source_handles',[])
  if n.get('system') not in LAYERS or not circle or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace() or circle.dxf.layer!=LAYERS[n['system']] or len(handles)!=5 or len(set(handles))!=5 or h not in handles or degrees[n['node_id']]!=1:raise ValueError('invalid terminal source or degree')
  center=(circle.dxf.center.x,circle.dxf.center.y)
  if math.dist(center,(n['x'],n['y']))>.05:raise ValueError('terminal center mismatch')
  lines=[]
  for k in handles:
   if k==h:continue
   e=doc.entitydb.get(k)
   if not e or e.dxftype()!='LINE' or e not in doc.modelspace() or e.dxf.layer!='空调立管、水平支管':raise ValueError('terminal source glyph mismatch')
   lines.append({'handle':k,'a':(e.dxf.start.x,e.dxf.start.y),'b':(e.dxf.end.x,e.dxf.end.y)})
  matched=match_out_of_plane_symbol({'center':center,'radius':circle.dxf.radius},lines)
  if not matched or {x['handle'] for group in matched for x in group}!={x['handle'] for x in lines}:raise ValueError('unrecognized complete native glyph')
 pairs=candidate_pairs(interfaces,spacing,tol);devices=[]
 for node in nodes:
  if node.get('node_type')!='equipment':continue
  e=doc.entitydb.get(node.get('source_handle'))
  if not e or e.dxftype()!='INSERT' or e not in doc.modelspace():raise ValueError('equipment source insert mismatch')
  segments,unsupported=body_straight_segments(e)
  if not segments or unsupported:
   devices.append({'node_id':node['node_id'],'source_handle':e.dxf.handle,'geometry_status':'incomplete','unsupported':unsupported,'pair_candidates':[]});continue
  hits=[]
  for pair in pairs:
   da=min(point_segment_distance(pair['return_xy'],a,b) for a,b in segments);db=min(point_segment_distance(pair['supply_xy'],a,b) for a,b in segments)
   if max(da,db)<=radius:hits.append({'return_node':pair['return_node'],'supply_node':pair['supply_node'],'return_body_distance':da,'supply_body_distance':db,'terminal_pairing_ambiguous':pair['terminal_pairing_ambiguous'],'status':'nearby_pair_not_bound'})
  devices.append({'node_id':node['node_id'],'source_handle':e.dxf.handle,'geometry_status':'straight_body_only','pair_candidates':hits,'connection_status':node.get('connection_status')})
 return {'status':'geometry_inventory_not_device_binding','source_sha256':source_hash,'graph_sha256':graph_hash,'pair_spacing':spacing,'pair_tolerance':tol,'body_search_radius':radius,'source_terminal_count':len(interfaces),'pairs':pairs,'equipment':devices,'graph_mutated':False,'hil_ready':False,'limitations':['Pair spacing and body distance are caller-calibrated search parameters, not equipment-port or ownership evidence.','Equipment body scan covers native LINE and straight LWPOLYLINE only; incomplete shapes stay unassigned.','Other terminal families and unmatched interface symbols are outside this paired-glyph screen.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);gb=a.graph.read_bytes();pb=a.policy.read_bytes();sha=lambda x:hashlib.sha256(x).hexdigest();r=scan(doc,json.loads(gb),json.loads(pb),proof['source_sha256'],sha(gb));r.update(policy_sha256=sha(pb),script_sha256=sha(Path(__file__).read_bytes()),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'pairs':len(r['pairs']),'equipment_with_candidates':sum(bool(x['pair_candidates']) for x in r['equipment']),'status':r['status']}))
if __name__=='__main__':main()
