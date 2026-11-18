"""Scoped native named-DN leader candidate screen; never mutates a graph."""
import argparse,hashlib,json,math
from pathlib import Path
from ezdxf import bbox
from pipe_annotation_attributes import parse_named_dn_annotation
from source_readability import read_source

def screen(doc,graph,policy,source_sha,graph_sha):
 if policy.get('source_sha256')!=source_sha or policy.get('graph_sha256')!=graph_sha or graph.get('metadata',{}).get('source_sha256')!=source_sha:raise ValueError('stale source or graph')
 tolerance=policy.get('endpoint_tolerance');ratio=policy.get('max_text_height_gap');records=policy.get('selections')
 if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0 for v in (tolerance,ratio)) or not isinstance(records,list) or not records:raise ValueError('invalid scope')
 nodes={n['node_id']:n for n in graph['nodes']};rows=[];used=set()
 for r in records:
  key=(r['node_id'],r['leader_handle'],r['text_handle'])
  if any(k in used for k in key):raise ValueError('duplicate selected identity')
  used.update(key);n=nodes.get(key[0]);line=doc.entitydb.get(key[1]);text=doc.entitydb.get(key[2]);pipe=doc.entitydb.get(r['pipe_handle'])
  if not n or n.get('boundary_type')!='unresolved_source_terminal' or not line or line.dxftype()!='LINE' or not text or text.dxftype()!='TEXT' or not pipe or pipe.dxftype()!='LINE':raise ValueError('unsupported source entities or boundary')
  if any(e.dxf.owner!=doc.modelspace().block_record_handle for e in (line,text,pipe)):raise ValueError('source not modelspace')
  if line.dxf.layer!=r['leader_layer'] or text.dxf.layer!=r['text_layer'] or pipe.dxf.layer!=r['pipe_layer'] or r['pipe_handle'] not in n.get('source_handles',[]):raise ValueError('source identity or layer mismatch')
  label=parse_named_dn_annotation(text.dxf.text)
  if not label or label['original_text']!=r['expected_text'] or label['system']!=n.get('system'):raise ValueError('label or system mismatch')
  xy=(n['x'],n['y']);ends=[(line.dxf.start.x,line.dxf.start.y),(line.dxf.end.x,line.dxf.end.y)];ds=[math.dist(p,xy) for p in ends]
  if min(ds)>tolerance or abs(ds[0]-ds[1])<=tolerance:raise ValueError('ambiguous leader endpoint')
  pipeends=[(pipe.dxf.start.x,pipe.dxf.start.y),(pipe.dxf.end.x,pipe.dxf.end.y)]
  if min(math.dist(p,xy) for p in pipeends)>tolerance:raise ValueError('pipe misses endpoint')
  anchor=ends[1 if ds[0]<ds[1] else 0];h=float(text.dxf.height)
  if not math.isfinite(h) or h<=0:raise ValueError('invalid text height')
  matches=[]
  for candidate in doc.modelspace().query('TEXT'):
   parsed=parse_named_dn_annotation(candidate.dxf.text)
   if not parsed:continue
   bb=bbox.extents([candidate])
   if not bb.has_data:continue
   gap=math.hypot(max(bb.extmin.x-anchor[0],0,anchor[0]-bb.extmax.x),max(bb.extmin.y-anchor[1],0,anchor[1]-bb.extmax.y))
   if gap<=ratio*h:matches.append({'handle':candidate.dxf.handle,'text':candidate.dxf.text,'bbox_gap':gap})
  if len(matches)!=1 or matches[0]['handle']!=text.dxf.handle:raise ValueError('ambiguous or missing text near leader')
  rows.append({'node_id':n['node_id'],'system':n['system'],'pipe_handle':r['pipe_handle'],'leader_handle':key[1],'text_handle':key[2],'leader_layer':line.dxf.layer,'text_layer':text.dxf.layer,'endpoint_distance':min(ds),'text_bbox_gap':matches[0]['bbox_gap'],'text_height':h,'label':label,'status':'source_geometry_candidate_not_binding'})
 return {'status':'scoped_leader_candidates_not_binding','source_sha256':source_sha,'graph_sha256':graph_sha,'selections':rows,'graph_mutated':False,'mapping_ready':False,'hil_ready':False,'limitations':['TEXT bounding boxes depend on available CAD font metrics; inspect rendered original.','Only selected modelspace LINE, TEXT and named-DN competitors are checked; nested and proxy content is outside scope.','Geometry does not establish physical remote connectivity or cross-view mapping.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);g=json.loads(a.graph.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'));result=screen(doc,g,policy,proof['source_sha256'],sha(a.graph));result.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':result['status'],'selections':len(result['selections'])}))
if __name__=='__main__':main()
