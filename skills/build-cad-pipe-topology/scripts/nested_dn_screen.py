"""Screen nested source DN text near selected paths; never assign diameter.

Unsupported proxies, external references and insertion forms remain explicit
coverage limitations. Native text is strictly read and transformed by ezdxf.
"""
import argparse,collections,hashlib,json,logging,math,re
from pathlib import Path
from ezdxf.disassemble import recursive_decompose
from source_readability import read_source
from native_equipment_body import point_segment_distance
from pipe_annotation_attributes import parse_dn_annotation

class _Capture(logging.Handler):
 def __init__(self):super().__init__();self.count=0;self.examples=[]
 def emit(self,record):
  self.count+=1
  if len(self.examples)<5:self.examples.append(record.getMessage())

def screen(doc,graph,policy,source_hash,graph_hash):
 if graph.get('metadata',{}).get('source_sha256')!=source_hash or policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash:raise ValueError('source or graph mismatch')
 ids=policy.get('edges');radius=policy.get('nested_search_radius')
 if not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)) or isinstance(radius,bool) or not isinstance(radius,(int,float)) or not math.isfinite(radius) or radius<=0:raise ValueError('invalid nested DN screen scope')
 edges={e['edge_id']:e for e in graph['edges']}
 if len(edges)!=len(graph['edges']) or not set(ids)<=edges.keys():raise ValueError('invalid edge IDs')
 segments=[]
 for eid in ids:
  for path in edges[eid].get('attribute_paths',[]):
   for a,b in zip(path,path[1:]):
    if len(a)!=2 or len(b)!=2 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in a+b) or math.dist(a,b)<=1e-8:raise ValueError('invalid edge geometry')
    segments.append((eid,a,b))
 if not segments:raise ValueError('empty edge geometry')
 seen=set();active=set();missing=set();xrefs=set();proxy_entities=[];arrays=[];cycles=set()
 def walk(name):
  if name in active:cycles.add(name);return
  if name in seen:return
  seen.add(name)
  if name not in doc.blocks:missing.add(name);return
  active.add(name);block=doc.blocks[name];flags=block.block.dxf.get('flags',0)
  if flags & (4|8|16):xrefs.add(name)
  for e in block:
   if e.dxftype()=='ACAD_PROXY_ENTITY':proxy_entities.append({'block':name,'handle':e.dxf.handle})
   if e.dxftype()=='INSERT':
    if e.mcount>1:arrays.append({'owner':name,'handle':e.dxf.handle,'count':e.mcount})
    walk(e.dxf.name)
  active.remove(name)
 tops=list(doc.modelspace().query('INSERT'))
 for ins in tops:
  if ins.mcount>1:arrays.append({'owner':'modelspace','handle':ins.dxf.handle,'count':ins.mcount})
  walk(ins.dxf.name)
 model_proxies=[e.dxf.handle for e in doc.modelspace() if e.dxftype()=='ACAD_PROXY_ENTITY']
 logger=logging.getLogger('ezdxf');handler=_Capture();oldprop=logger.propagate;logger.addHandler(handler);logger.propagate=False
 found=[];text_count=0;dn_count=0
 try:
  for top in tops:
   for e in recursive_decompose([top]):
    if e.dxftype() not in ('TEXT','MTEXT','ATTRIB'):continue
    text=e.plain_text();text_count+=1
    if not isinstance(text,str) or '\ufffd' in text or any(0xd800<=ord(c)<=0xdfff for c in text):raise ValueError('unreadable nested native text')
    if not re.search(r'DN',text,re.I):continue
    dn_count+=1;p=e.ocs().to_wcs(e.dxf.insert) if e.dxftype() in ('TEXT','ATTRIB') else e.dxf.insert
    height=float(e.dxf.height if e.dxftype() in ('TEXT','ATTRIB') else e.dxf.char_height)
    if not all(math.isfinite(v) for v in (p.x,p.y,height)) or height<=0:raise ValueError('invalid nested DN transform')
    hits=[]
    for eid,a,b in segments:
     distance=point_segment_distance((p.x,p.y),a,b)
     if distance<=max(radius,2*height):hits.append((distance,eid))
    if not hits:continue
    origin=e.origin_of_copy or e
    if not origin.dxf.handle or doc.entitydb.get(origin.dxf.handle) is not origin:raise ValueError('nested DN missing native leaf identity')
    best={}
    for distance,eid in hits:best[eid]=min(best.get(eid,float('inf')),distance)
    found.append({'top_insert_handle':top.dxf.handle,'top_block_name':top.dxf.name,'leaf_handle':origin.dxf.handle,'entity_type':e.dxftype(),'layer':e.dxf.layer,'text':text,'position':[p.x,p.y],'height':height,'distances':[{ 'edge_id':eid,'drawing_distance':best[eid]} for eid in sorted(best)],'parsed_single_dn':parse_dn_annotation(text),'status':'nearby_nested_text_not_assigned'})
 finally:
  logger.removeHandler(handler);logger.propagate=oldprop
 found.sort(key=lambda x:(x['top_insert_handle'],x['leaf_handle'],x['position']))
 proxies=sum(1 for e in doc.objects if e.dxftype()=='ACAD_PROXY_OBJECT')
 return {'status':'screening_only_not_exhaustive','source_sha256':source_hash,'graph_sha256':graph_hash,'selected_edges':ids,'nested_search_radius':radius,'modelspace_inserts':len(tops),'reachable_block_definitions':len(seen),'flattened_text_entities':text_count,'flattened_dn_text_entities':dn_count,'nearby_nested_dn':found,'missing_blocks':sorted(missing),'xref_blocks':sorted(xrefs),'proxy_entities_in_blocks':proxy_entities,'proxy_entities_modelspace':model_proxies,'array_inserts':arrays,'cyclic_block_names':sorted(cycles),'proxy_objects_in_document':proxies,'flatten_warnings':{'count':handler.count,'examples':handler.examples},'graph_mutated':False,'hil_ready':False,'limitations':['Only expandable INSERT content and readable TEXT/MTEXT/ATTRIB are screened; DIMENSION, unsupported objects and opaque proxy payloads can contain further information.','Radius is a screening bound, not proof of annotation association or absence of longer leaders.','Proxy objects are counted document-wide; their locations and meaning are not inferred.','No diameter, connection or engineering review is established.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,required=True,type=Path)
 a=p.parse_args();doc,proof=read_source(a.source);gb=a.graph.read_bytes();pb=a.policy.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();r=screen(doc,json.loads(gb),json.loads(pb),proof['source_sha256'],sha(gb));r.update(policy_sha256=sha(pb),script_sha256=sha(Path(__file__).read_bytes()),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'nearby_nested_dn':len(r['nearby_nested_dn']),'proxy_objects':r['proxy_objects_in_document'],'flatten_warnings':r['flatten_warnings']['count'],'status':r['status']}))
if __name__=='__main__':main()
