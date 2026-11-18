"""Screen near-centre circle contacts within native equipment instances, read-only."""
import argparse,hashlib,json,math
from pathlib import Path
from ezdxf.disassemble import recursive_decompose
from native_line_path_evidence import LAYERS
from source_readability import read_source

def collect(doc,graph,policy,source_hash,graph_hash,tol=.05):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash:raise ValueError('input hash mismatch')
 ratio=policy.get('max_radius_ratio')
 if not isinstance(ratio,(int,float)) or not 0<ratio<=.2 or not 0<tol<=.05:raise ValueError('invalid distance bounds')
 edges={e['edge_id']:e for e in graph['edges']};ids=policy.get('edges',[])
 if len(edges)!=len(graph['edges']) or not ids or len(ids)!=len(set(ids)):raise ValueError('invalid edge selection')
 result=[]
 for eid in ids:
  edge=edges.get(eid);root=doc.entitydb.get(edge.get('source_insert_handle')) if edge else None
  if not edge or edge.get('system') not in LAYERS or not root or root.dxftype()!='INSERT' or root not in doc.modelspace():raise ValueError('unsupported source instance')
  owner=doc.blocks[root.dxf.name].block_record_handle;entities=[]
  for e in recursive_decompose([root]):
   orig=getattr(e,'source_of_copy',None)
   if orig is not None and orig.dxf.owner==owner and e.dxftype() in ('LINE','CIRCLE'):entities.append((e,orig.dxf.handle))
  circles=[(e,h) for e,h in entities if e.dxftype()=='CIRCLE'];lines=[(e,h) for e,h in entities if e.dxftype()=='LINE' and e.dxf.layer==LAYERS[edge['system']]];matches=[]
  for line,lh in lines:
   for circle,ch in circles:
    c=circle.ocs().to_wcs(circle.dxf.center);radius=circle.dxf.radius
    if not math.isfinite(radius) or radius<=0:continue
    for n,p in enumerate((line.dxf.start,line.dxf.end)):
     offset=math.hypot(p.x-c.x,p.y-c.y)
     if tol<offset<=radius*ratio and abs(p.z-c.z)<=tol:
      matches.append({'source_line_chain':[root.dxf.handle,lh],'source_circle_chain':[root.dxf.handle,ch],'endpoint_index':n,'offset':offset,'radius':radius,'offset_radius_ratio':offset/radius,'line_endpoint':list(p),'circle_center':list(c),'source_layer':line.dxf.layer})
  result.append({'edge_id':eid,'system':edge['system'],'device_label':edge.get('device_label'),'candidates':matches,'status':'unique_offset_candidate' if len(matches)==1 else 'ambiguous_or_no_candidate'})
 return {'status':'offset_geometry_candidates_only','source_sha256':source_hash,'graph_sha256':graph_hash,'edges':result,'graph_mutated':False,'hil_ready':False,'limitations':['Endpoint inside a circle is a candidate, not proof of a physical connection or port.','Only direct child LINE and CIRCLE entities are considered; other evidence and conflicting geometry need review.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();res=collect(doc,json.loads(a.graph.read_text(encoding='utf8')),json.loads(a.policy.read_text(encoding='utf8')),proof['source_sha256'],sha(a.graph));res.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(res,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'edges':len(res['edges']),'unique':sum(x['status']=='unique_offset_candidate' for x in res['edges'])}))
if __name__=='__main__':main()
