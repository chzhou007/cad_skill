"""Source-bound DN text inventory around selected graph paths; never binds a diameter."""
import argparse,hashlib,json,math,re
from pathlib import Path
from ezdxf import bbox
from ezdxf.disassemble import recursive_decompose
from source_readability import read_source
from pipe_annotation_attributes import parse_named_dn_annotation

def proxy_inventory(doc):
 """Count opaque entities by DXF section without decoding or inferring impact."""
 def count(items):
  result={}
  for entity in items:
   typ=entity.dxftype()
   if 'PROXY' in typ:result[typ]=result.get(typ,0)+1
  return result
 blocks=[]
 for block in doc.blocks:
  types=count(block)
  if types:blocks.append({'block':block.name,'direct_proxy_types':types})
 return {'modelspace_direct_types':count(doc.modelspace()),'block_definitions_with_direct_proxy_entities':blocks,'objects_section_types':count(doc.objects),'scope':'Whole DXF sections, direct entity types only; proxy contents and references are opaque and impact is unverified.'}

def inventory(doc,graph,policy,source_hash,graph_hash,source_binding=None):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash:raise ValueError('stale source or graph')
 metadata_source=graph.get('metadata',{}).get('source_sha256')
 if metadata_source and metadata_source!=source_hash:raise ValueError('stale source or graph')
 if not metadata_source:
  if not isinstance(source_binding,dict) or source_binding.get('inputs',{}).get('dxf')!=source_hash or source_binding.get('final_graph_sha256')!=graph_hash:raise ValueError('missing or stale graph source receipt')
 ids=policy.get('edge_ids');margin=policy.get('margin_native_units')
 if not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)) or not isinstance(margin,(int,float)) or isinstance(margin,bool) or not math.isfinite(margin) or margin<0:raise ValueError('invalid scope')
 edges={e['edge_id']:e for e in graph['edges']}
 if not set(ids)<=edges.keys():raise ValueError('missing selected edge')
 pts=[p for eid in ids for p in (edges[eid].get('path') or edges[eid].get('path_points') or [])]
 if not pts or any(len(p)<2 or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in p[:2]) for p in pts):raise ValueError('invalid selected paths')
 bounds=[min(p[0] for p in pts)-margin,max(p[0] for p in pts)+margin,min(p[1] for p in pts)-margin,max(p[1] for p in pts)+margin];rows=[];roots=[];failures=[];proxies=[]
 def inside(p):return p is not None and bounds[0]<=p.x<=bounds[1] and bounds[2]<=p.y<=bounds[3]
 def record(e,root,scope):
  if e.dxftype() not in ('TEXT','MTEXT','ATTRIB'):return
  p=e.dxf.get('insert',None)
  if not inside(p):return
  text=e.plain_text() if e.dxftype()=='MTEXT' else e.dxf.text
  if re.search(r'DN\s*\d+',text,re.I):rows.append({'root_handle':root,'entity_handle':e.dxf.handle,'scope':scope,'type':e.dxftype(),'text':text,'xy':[p.x,p.y],'layer':e.dxf.layer,'named_dn_candidate':parse_named_dn_annotation(text)})
 def proxy_blocks(name,seen):
  if name in seen:return []
  block=doc.blocks.get(name)
  if block is None:return [{'block':name,'reason':'missing_block'}]
  found=[]
  for e in block:
   if 'PROXY' in e.dxftype():found.append({'block':name,'handle':e.dxf.handle,'type':e.dxftype()})
   if e.dxftype()=='INSERT':found.extend(proxy_blocks(e.dxf.name,seen|{name}))
  return found
 for e in doc.modelspace():
  if e.dxftype()!='INSERT':record(e,e.dxf.handle,'modelspace');continue
  try:
   box=bbox.extents([e])
   if not box.has_data:failures.append({'handle':e.dxf.handle,'reason':'empty_visible_bounds'});continue
   if box.extmax.x<bounds[0] or box.extmin.x>bounds[1] or box.extmax.y<bounds[2] or box.extmin.y>bounds[3]:continue
   roots.append(e.dxf.handle);proxies.extend({'root':e.dxf.handle,**x} for x in proxy_blocks(e.dxf.name,set()))
   for v in e.attribs:record(v,e.dxf.handle,'insert_attribute')
   for v in recursive_decompose([e]):record(v,e.dxf.handle,'decomposed_insert')
  except Exception as exc:failures.append({'handle':e.dxf.handle,'reason':str(exc)})
 # Report the representation that the historical F recognizer can see.
 # Modelspace LINE proximity is a clue only, never an F-shape match.
 layers={t['layer'] for t in rows};polylines=[]
 for e in doc.modelspace().query('LWPOLYLINE'):
  if e.dxf.layer not in layers:continue
  pts=list(e.vertices_in_wcs())
  if not pts or max(p.x for p in pts)<bounds[0] or min(p.x for p in pts)>bounds[1] or max(p.y for p in pts)<bounds[2] or min(p.y for p in pts)>bounds[3]:continue
  polylines.append({'handle':e.dxf.handle,'layer':e.dxf.layer,'vertices':len(pts),'closed':bool(e.closed),'bulged':any(abs(p[4])>1e-9 for p in e.get_points())})
 line_clues=[]
 for row in rows:
  if row['scope']!='modelspace' or row['type']!='TEXT':continue
  entity=doc.entitydb.get(row['entity_handle']);h=abs(float(entity.dxf.height));p=entity.ocs().to_wcs(entity.dxf.insert);near=[]
  if h<=0 or not math.isfinite(h):continue
  for line in doc.modelspace().query('LINE'):
   if line.dxf.layer!=row['layer']:continue
   a,b=line.dxf.start,line.dxf.end;dx,dy=b.x-a.x,b.y-a.y;den=dx*dx+dy*dy
   if not den:continue
   t=max(0,min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/den));distance=math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy)
   if distance<=3*h:near.append({'handle':line.dxf.handle,'distance':distance})
  line_clues.append({'text_handle':row['entity_handle'],'radius_text_heights':3,'same_layer_modelspace_lines':near,'status':'geometric_clue_not_F_recognition'})
 representation={'status':'representation_inventory_not_absence_proof','matching_text_layers':sorted(layers),'modelspace_lwpolylines':polylines,'open_straight_two_or_three_vertex_count':sum(not p['closed'] and not p['bulged'] and p['vertices'] in (2,3) for p in polylines),'near_text_line_clues':line_clues,'limitations':['The historical F recognizer requires compatible open two- or three-vertex LWPOLYLINE legs on text layers; the count alone is not a recognition result.','Exploded LINE, different-layer, nested, proxy and outside-window leaders are not excluded.']}
 return {'status':'bounded_text_inventory_not_absence_proof','source_sha256':source_hash,'graph_sha256':graph_hash,'edge_ids':ids,'margin_native_units':margin,'bounds':bounds,'intersecting_insert_roots':roots,'texts':rows,'bbox_or_decomposition_failures':failures,'opaque_proxy_references_in_selected_roots':proxies,'global_proxy_inventory':proxy_inventory(doc),'f_leader_representation':representation,'mapping_ready':False,'hil_ready':False,'limitations':['Only TEXT, MTEXT and ATTRIB insertion points within the bounded rectangle are recorded.','Nested geometry outside visible insert bounds, proxy content, F-shaped geometry and other formats may be missed. Proxy counts by section do not prove whether opaque objects affect these results.','Text proximity does not establish diameter ownership or cross-view correspondence.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--source-binding-receipt',type=Path)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);g=json.loads(a.graph.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'));binding=None
 if a.source_binding_receipt:
  if policy.get('source_binding_receipt_sha256')!=sha(a.source_binding_receipt):raise ValueError('source receipt hash mismatch')
  binding=json.loads(a.source_binding_receipt.read_text(encoding='utf8'))
 elif policy.get('source_binding_receipt_sha256'):raise ValueError('source receipt required')
 result=inventory(doc,g,policy,proof['source_sha256'],sha(a.graph),binding);result.update(source_preflight=proof['status'],policy_sha256=sha(a.policy),source_binding_receipt_sha256=sha(a.source_binding_receipt) if a.source_binding_receipt else None);
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':result['status'],'texts':len(result['texts']),'failures':len(result['bbox_or_decomposition_failures']),'proxy_references':len(result['opaque_proxy_references_in_selected_roots'])}))
if __name__=='__main__':main()
