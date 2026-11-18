"""Attach native dimension to an exactly witnessed path segment, not whole edge."""
import argparse,copy,hashlib,json,math,re,shutil
from pathlib import Path
from source_readability import read_source
from source_direct_dn_evidence import collect as collect_direct_dn
from infer_local_dn_candidates import collect_evidence
from native_line_path_evidence import _on

LAYERS={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}
def collect(doc,graph,policy,source_hash,graph_hash,tol=.05):
 if graph.get('metadata',{}).get('source_sha256')!=source_hash or policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash:raise ValueError('source or graph mismatch')
 if doc.header.get('$INSUNITS')!=4:raise ValueError('source drawing does not declare millimetres')
 rows=policy.get('dimensions');edges={e['edge_id']:e for e in graph['edges']}
 if len(edges)!=len(graph['edges']) or not isinstance(rows,list) or not rows or len({r['dimension_handle'] for r in rows})!=len(rows):raise ValueError('invalid selection')
 found=[];owned=set()
 for r in rows:
  e=edges.get(r['edge_id']);dim=doc.entitydb.get(r['dimension_handle']);idx=r['segment_index'];expected=r['expected_value_mm'];line=doc.entitydb.get(r['source_line_handle'])
  if not e or e.get('system') not in LAYERS or not dim or dim not in doc.modelspace() or dim.dxftype()!='DIMENSION' or dim.dxf.layer!=r['dimension_layer']:raise ValueError('dimension source or edge mismatch')
  if isinstance(expected,bool) or not isinstance(expected,(int,float)) or not math.isfinite(expected) or expected<=0 or isinstance(idx,bool) or not isinstance(idx,int) or idx<0:raise ValueError('invalid selected dimension')
  if dim.dxf.dimtype & 7 !=0 or tuple(dim.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.) or dim.dxf.get('text','') not in ('','<>'):raise ValueError('unsupported dimension type or text override')
  style=doc.dimstyles.get(dim.dxf.dimstyle);overrides=dim.get_acad_dstyle(style)
  factor=overrides.get('dimlfac',style.dxf.get('dimlfac',1.0))
  if factor is None:factor=1.0
  if not isinstance(factor,(int,float)) or not math.isfinite(factor) or abs(factor-1)>1e-9:raise ValueError('dimension scale factor unsupported')
  paths=e.get('attribute_paths',[])
  if len(paths)!=1 or idx>=len(paths[0])-1:raise ValueError('segment index mismatch')
  a,b=paths[0][idx:idx+2];p=dim.dxf.get('defpoint2');q=dim.dxf.get('defpoint3')
  if p is None or q is None or not all(math.isfinite(v) for v in list(a)+list(b)+[p.x,p.y,q.x,q.y]):raise ValueError('invalid dimension coordinates')
  ends=[(p.x,p.y),(q.x,q.y)]
  if not ((math.dist(a,ends[0])<=tol and math.dist(b,ends[1])<=tol) or (math.dist(a,ends[1])<=tol and math.dist(b,ends[0])<=tol)):raise ValueError('dimension points do not match graph segment')
  distance=math.dist(a,b);measured=float(dim.get_measurement())
  if not math.isfinite(measured) or max(abs(distance-expected),abs(measured-expected))>tol:raise ValueError('dimension value mismatch')
  if not line or line not in doc.modelspace() or line.dxftype()!='LINE' or line.dxf.layer!=LAYERS[e['system']] or line.dxf.handle not in e.get('source_handles',[]):raise ValueError('source pipe line mismatch')
  native=[(line.dxf.start.x,line.dxf.start.y),(line.dxf.end.x,line.dxf.end.y)]
  if not ((math.dist(a,native[0])<=tol and math.dist(b,native[1])<=tol) or (math.dist(a,native[1])<=tol and math.dist(b,native[0])<=tol)):raise ValueError('source line endpoints differ from graph segment')
  native_matches=[]
  for other in doc.modelspace().query('LINE'):
   if other.dxf.layer!=line.dxf.layer:continue
   u=(other.dxf.start.x,other.dxf.start.y);v=(other.dxf.end.x,other.dxf.end.y)
   if _on(a,u,v,tol) and _on(b,u,v,tol):native_matches.append(other.dxf.handle)
  if native_matches!=[line.dxf.handle]:raise ValueError('dimension source line is not unique')
  competitors=[]
  for other in graph['edges']:
   for pi,path in enumerate(other.get('attribute_paths',[])):
    for si,(u,v) in enumerate(zip(path,path[1:])):
     if (math.dist(u,a)<=tol and math.dist(v,b)<=tol) or (math.dist(u,b)<=tol and math.dist(v,a)<=tol):competitors.append((other['edge_id'],pi,si))
  if competitors!=[(e['edge_id'],0,idx)] or (e['edge_id'],idx) in owned:raise ValueError('dimension segment ownership ambiguous')
  geometry=dim.dxf.get('geometry')
  if not geometry or geometry not in doc.blocks:raise ValueError('dimension display block missing')
  texts=[x for x in doc.blocks[geometry] if x.dxftype() in ('TEXT','MTEXT')]
  if len(texts)!=1 or texts[0].dxf.handle!=r['text_handle'] or texts[0].plain_text()!=r['expected_text'] or not re.fullmatch(r'\d+(?:\.\d+)?',r['expected_text']) or abs(float(r['expected_text'])-expected)>tol:raise ValueError('dimension rendered text mismatch')
  display=[x for x in dim.virtual_entities() if x.dxftype() in ('TEXT','MTEXT')]
  if len(display)!=1 or display[0].plain_text()!=r['expected_text']:raise ValueError('dimension display transformation mismatch')
  owned.add((e['edge_id'],idx));found.append({'edge_id':e['edge_id'],'segment_index':idx,'system':e['system'],'dimension_handle':dim.dxf.handle,'dimension_text_handle':texts[0].dxf.handle,'dimension_text':r['expected_text'],'source_line_handle':line.dxf.handle,'dimension_value_mm':float(expected),'segment_points':[a,b],'source_units':'DXF INSUNITS=4 (mm)','status':'source_dimension_for_drawn_segment_pending_review','edge_total_length_known':False})
 return found

def attach(graph,observations,source_hash,graph_hash):
 out=copy.deepcopy(graph);edges={e['edge_id']:e for e in out['edges']}
 groups={}
 for row in observations:groups.setdefault(row['edge_id'],[]).append(copy.deepcopy(row))
 for edge_id,items in groups.items():
  e=edges[edge_id]
  if e.get('source_dimensioned_segments'):raise ValueError('existing dimension segments need reconciliation')
  e['source_dimensioned_segments']=items;e['physical_edge_length_status']='unknown_other_segments_or_geometry'
 out['preHilComparison']={'status':'pending','previous_comparison':copy.deepcopy(graph.get('preHilComparison')),'reason':'segment dimension evidence added; graph-bound comparisons and review must be repeated'}
 out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_attribute_change')
 out['sourceSegmentDimensions']={'source_sha256':source_hash,'input_graph_sha256':graph_hash,'observations':copy.deepcopy(observations),'whole_edge_length_assigned':False,'status':'source_evidence_pending_review'}
 return out

def validate_dn_dependencies(graph,direct,inheritance,source_hash,graph_hash):
 candidate=graph.get('diameterInheritanceCandidates',{})
 if direct.get('source_sha256')!=source_hash or direct.get('graph_sha256')!=graph_hash or inheritance.get('source_sha256')!=source_hash:raise ValueError('stale prior DN evidence policy')
 if candidate.get('source_sha256')!=source_hash or candidate.get('input_graph_sha256')!=inheritance.get('graph_sha256') or candidate.get('status')!='candidate_not_accepted' or candidate.get('edgewide_values_assigned') is not False:raise ValueError('inherited candidate lineage mismatch')
 expected=inheritance.get('edges',[]);changes=candidate.get('changes',[])
 if not expected or len(expected)!=len(set(expected)) or len(changes)!=len(expected) or {x.get('edge_id') for x in changes}!=set(expected):raise ValueError('inherited candidate coverage mismatch')

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','devices','policy','dn-inheritance-policy','direct-dn-policy','output'):p.add_argument('--'+k,required=True,type=Path)
 a=p.parse_args()
 if a.output.exists():raise ValueError('refusing to overwrite output')
 doc,proof=read_source(a.source);gb=a.graph.read_bytes();pb=a.policy.read_bytes();db=a.direct_dn_policy.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();graph=json.loads(gb);policy=json.loads(pb);direct=json.loads(db);inheritance=json.loads(a.dn_inheritance_policy.read_bytes());h=sha(gb)
 validate_dn_dependencies(graph,direct,inheritance,proof['source_sha256'],h)
 observations=collect(doc,graph,policy,proof['source_sha256'],h);out=attach(graph,observations,proof['source_sha256'],h);a.output.mkdir(parents=True);dest=a.output/'graph_with_source_segment_dimensions.json';dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv');newhash=sha(dest.read_bytes())
 # Recheck all graph-bound DN evidence, source paths and junctions on the new graph.
 dp=copy.deepcopy(direct);dp['prior_graph_sha256']=h;dp['graph_sha256']=newhash;dp['rechecked_from_policy_sha256']=sha(db);dp_path=a.output/'direct_dn_recheck_policy.json';dp_path.write_text(json.dumps(dp,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 dn=collect_direct_dn(doc,out,dp,proof['source_sha256'],newhash);dn.update(source_preflight=proof,policy_sha256=sha(dp_path.read_bytes()));paths,rays,risks,nested=collect_evidence(doc,out,inheritance,proof['source_sha256'],newhash,a.source.stem)
 for name,data in [('source-direct-dn-candidates.json',dn),('source-path-evidence.json',paths),('source-junction-evidence.json',rays),('source-dn-risk-evidence.json',risks),('source-nested-dn-evidence.json',nested)]:
  (a.output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 audit={'source_sha256':proof['source_sha256'],'input_graph_sha256':h,'output_graph_sha256':newhash,'policy_sha256':sha(pb),'implementation_sha256':sha(Path(__file__).read_bytes()),'dn_inheritance_policy_sha256':sha(a.dn_inheritance_policy.read_bytes()),'direct_dn_policy_sha256':sha(db),'regenerated_evidence_sha256':{name:sha((a.output/name).read_bytes()) for name in ('source-direct-dn-candidates.json','source-path-evidence.json','source-junction-evidence.json','source-dn-risk-evidence.json','source-nested-dn-evidence.json')},'component_table_sha256':sha(a.devices.read_bytes()),'observations':observations,'whole_edge_length_assigned':False,'hil_ready':False,'source_preflight':proof}
 (a.output/'source-segment-dimension-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'segments':len(observations),'graph_sha256':newhash,'hil_ready':False}))
if __name__=='__main__':main()
