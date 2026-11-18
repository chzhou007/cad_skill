"""Selected, source-bound DN candidates on individual witnessed graph segments.

Does not assign whole-edge diameter, establish physical direction or transition,
or mutate the graph. It is not a complete source-annotation recognition pass.
"""
import argparse,hashlib,json,math
from pathlib import Path
from source_readability import read_source
from native_dn_text_position import supported as supported_dn_text_position
from source_direct_dn_evidence import _projection,LAYERS
from pipe_annotation_attributes import source_texts,parse_dn_annotation,recognize_f_leaders
from ezdxf.disassemble import recursive_decompose

def collect(doc,graph,line_evidence,policy,source_hash,graph_hash,line_hash):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or policy.get('line_evidence_sha256')!=line_hash:raise ValueError('source, graph or line evidence hash mismatch')
 if line_evidence.get('source_sha256')!=source_hash or line_evidence.get('graph_sha256')!=graph_hash or line_evidence.get('status')!='geometry_evidence_unreviewed':raise ValueError('line evidence not bound to source graph')
 selections=policy.get('selections',[]);layers=set(policy.get('text_layers',[]))
 if not selections or not layers or len({s['text_handle'] for s in selections})!=len(selections):raise ValueError('invalid or duplicate selections')
 withheld=policy.get('withheld_candidates',[])
 if not isinstance(withheld,list) or any(not isinstance(x,dict) or not isinstance(x.get('text_handle'),str) or not x['text_handle'] or not isinstance(x.get('expected_text'),str) or not x['expected_text'] or not isinstance(x.get('reason'),str) or not x['reason'].strip() for x in withheld):raise ValueError('invalid withheld candidates')
 if len({x['text_handle'] for x in withheld})!=len(withheld) or {x['text_handle'] for x in withheld}&{x['text_handle'] for x in selections}:raise ValueError('duplicate or selected withheld candidate')
 edges={x['edge_id']:x for x in graph['edges']};witness={x['edge_id']:x for x in line_evidence['edges']}
 if len(edges)!=len(graph['edges']) or len(witness)!=len(line_evidence['edges']):raise ValueError('duplicate edge identity')
 texts=source_texts(doc,'source',source_hash);by_handle={t['handle']:t for t in texts}
 withheld_rows=[]
 for item in withheld:
  t=by_handle.get(item['text_handle']);native=doc.entitydb.get(item['text_handle'])
  if not t or not native or native not in doc.modelspace() or t['entity_type']!='TEXT' or t['layer'] not in layers or t['text']!=item['expected_text'] or not parse_dn_annotation(t['text']):raise ValueError('withheld source text mismatch')
  withheld_rows.append({'source_text':t,'reason':item['reason'],'status':'withheld_not_attributed'})
 frames=recognize_f_leaders(doc,texts,[],graph['edges'],layers);f_texts={t['handle'] for f in frames for t in f['texts']}
 # A graph-referenced device INSERT can contain a second eligible pipe LINE.
 # Ignore neither its transformed geometry nor its inherited source layer when
 # testing label ambiguity. Nested layer 0 is treated conservatively as a
 # competitor without assigning its inherited system; non-INSERT references
 # (such as omission glyphs)
 # are not decomposed and remain explicitly outside this scoped check.
 nested=[];non_insert=[]
 for root_handle in sorted({e.get('source_insert_handle') for e in graph['edges'] if e.get('source_insert_handle')}):
  root=doc.entitydb.get(root_handle)
  if root is None or root not in doc.modelspace():raise ValueError('missing referenced source entity')
  if root.dxftype()!='INSERT':non_insert.append(root_handle);continue
  try:
   nested.extend((line,root_handle) for line in recursive_decompose([root]) if line.dxftype()=='LINE' and (line.dxf.layer in LAYERS.values() or line.dxf.layer=='0'))
  except Exception as exc:raise ValueError('referenced insert decomposition failed') from exc
 rows=[]
 for selection in selections:
  handle=selection['text_handle'];eid=selection['edge_id'];idx=selection['segment_index'];t=by_handle.get(handle);edge=edges.get(eid);w=witness.get(eid)
  if not t or not edge or not w or t['text']!=selection['expected_text'] or t['layer'] not in layers or t['entity_type']!='TEXT' or handle in f_texts:raise ValueError('invalid text, edge or recognized F leader')
  native=doc.entitydb.get(handle)
  if native not in doc.modelspace() or not supported_dn_text_position(native):raise ValueError('unsupported text transform')
  parsed=parse_dn_annotation(t['text']);segments=w.get('segments',[])
  if not parsed or not isinstance(idx,int) or isinstance(idx,bool) or idx<0 or idx>=len(segments):raise ValueError('invalid DN or segment index')
  seg=segments[idx];paths=edge.get('attribute_paths',[])
  if len(paths)!=1 or idx+1>=len(paths[0]) or seg['segment_index']!=idx or seg['graph_start']!=paths[0][idx] or seg['graph_end']!=paths[0][idx+1] or w['system']!=edge['system']:raise ValueError('line witness and graph segment mismatch')
  angle=math.radians(t['rotation']);u=(math.cos(angle),math.sin(angle));hits=[]
  for line,root_handle in [(x,None) for x in doc.modelspace().query('LINE')]+nested:
   if line.dxf.layer not in LAYERS.values() and not (root_handle is not None and line.dxf.layer=='0'):continue
   a=(line.dxf.start.x,line.dxf.start.y);b=(line.dxf.end.x,line.dxf.end.y);dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
   if not length or abs(u[0]*dy-u[1]*dx)/length>math.sin(math.radians(2)):continue
   q=_projection(t['position'],a,b)
   if q and 0<q[0]<1 and q[1]<=2*t['height']:hits.append((q[1],0 if root_handle is None else 1,line.dxf.handle if root_handle is None else root_handle))
  hits.sort();graph_foot=_projection(t['position'],seg['graph_start'],seg['graph_end'])
  if not hits or hits[0][1]!=0 or hits[0][2]!=seg['source_handle'] or (len(hits)>1 and hits[1][0]-hits[0][0]<=.5*t['height']) or not graph_foot or not 0<graph_foot[0]<1:raise ValueError('native line or segment proximity is ambiguous')
  rows.append({'edge_id':eid,'segment_index':idx,'system':edge['system'],'source_line_handle':seg['source_handle'],'source_text':t,'nominal_mm_candidate':parsed['nominal_mm'],'parenthesized_source_value':parsed['parenthesized_source_value'],'graph_projection':list(graph_foot[2]),'native_line_candidates':[{'handle':h if kind==0 else None,'source_insert_handle':h if kind==1 else None,'distance':d} for d,kind,h in hits],'status':'segment_dn_candidate_not_accepted'})
 return {'status':'segment_candidates_not_accepted','source_sha256':source_hash,'graph_sha256':graph_hash,'line_evidence_sha256':line_hash,'observations':rows,'withheld_observations':withheld_rows,'graph_mutated':False,'hil_ready':False,'non_insert_source_references_not_decomposed':non_insert,'limitations':['Withheld items record selected source texts and stated reasons; this list is not a complete ambiguity inventory.','Only selected modelspace TEXT, modelspace LINE, and LINE descendants of graph-referenced INSERTs are scanned; other blocks, non-INSERT references and proxies are not inventoried. Nested layer 0 lines are conservative competitors without a resolved system.','Simple F-leader detector is incomplete; a non-detection does not prove absence of other leader forms.','Proximity is not confirmed label ownership; no whole-edge value, transition point, physical direction or physical length inferred.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','line-evidence','policy','output'):p.add_argument('--'+k,required=True,type=Path)
 a=p.parse_args();doc,proof=read_source(a.source);gb=a.graph.read_bytes();lb=a.line_evidence.read_bytes();pb=a.policy.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();r=collect(doc,json.loads(gb),json.loads(lb),json.loads(pb),proof['source_sha256'],sha(gb),sha(lb));r.update(policy_sha256=sha(pb),script_sha256=sha(Path(__file__).read_bytes()),text_guard_sha256=sha(Path(__file__).with_name('native_dn_text_position.py').read_bytes()),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'observations':len(r['observations'])}))
if __name__=='__main__':main()
