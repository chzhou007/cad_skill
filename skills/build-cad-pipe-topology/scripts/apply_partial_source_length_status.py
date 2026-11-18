"""Derive a graph with unknown physical lengths for incompletely witnessed paths."""
import argparse,copy,hashlib,json,math
from pathlib import Path

def apply(graph,coverage,source_hash,graph_hash,coverage_hash,policy):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or policy.get('coverage_sha256')!=coverage_hash:raise ValueError('policy hash mismatch')
 if coverage.get('source_sha256')!=source_hash or coverage.get('graph_sha256')!=graph_hash or coverage.get('status')!='partial_source_coverage_not_physical_length':raise ValueError('coverage identity mismatch')
 g=copy.deepcopy(graph);edges={e['edge_id']:e for e in g['edges']};reports={e['edge_id']:e for e in coverage['edges']};selected=policy.get('edge_ids',[])
 if len(edges)!=len(g['edges']) or len(reports)!=len(coverage['edges']) or not selected or len(set(selected))!=len(selected):raise ValueError('invalid selections or duplicate edges')
 audit=[]
 for id in selected:
  e=edges.get(id);r=reports.get(id)
  if not e or not r or e.get('system')!=r.get('system') or len(e.get('attribute_paths',[]))!=1:raise ValueError('edge evidence mismatch')
  path=e['attribute_paths'][0];segments=r['segments']
  if len(segments)!=len(path)-1:raise ValueError('segment count mismatch')
  source_sum=0.;unknown_sum=0.
  for i,(a,b,part) in enumerate(zip(path,path[1:],segments)):
   length=math.dist(a,b)
   if part['index']!=i or part['start']!=a or part['end']!=b or abs(part['drawing_length']-length)>.001:raise ValueError('segment geometry mismatch')
   if part['status']=='single_source_line_covers' and len(part.get('witnesses',[]))==1:source_sum+=length
   else:unknown_sum+=length
  if unknown_sum<=0 or source_sum<=0:raise ValueError('edge requires both witnessed and unverified portions')
  if abs(source_sum-r['source_covered_drawing_length'])>.001 or abs(unknown_sum-r['unverified_drawing_length'])>.001:raise ValueError('coverage totals mismatch')
  old=e.get('path_length')
  if not isinstance(old,(int,float)) or isinstance(old,bool) or not math.isfinite(old) or abs(old-(source_sum+unknown_sum))>.001:raise ValueError('drawing length mismatch')
  e['drawing_path_length']=old;e['path_length']=source_sum;e['source_path_length']=source_sum;e['path_length_complete']=False;e['path_length_scope']='source_drawn_pipe_only_unverified_segments_excluded';e['physical_length']='unknown';e['source_path_coverage']={'coverage_sha256':coverage_hash,'source_sha256':source_hash,'input_graph_sha256':graph_hash,'unverified_drawing_length':unknown_sum,'unverified_segment_indices':[s['index'] for s in segments if s['status']!='single_source_line_covers']}
  audit.append({'edge_id':id,'drawing_path_length':old,'source_covered_drawing_length':source_sum,'unverified_drawing_length':unknown_sum,'physical_length':'unknown'})
 omissions=policy.get('unverified_omission_edge_ids',[]);nodes={n['node_id']:n for n in g.get('nodes',[])}
 if not isinstance(omissions,list) or len(set(omissions))!=len(omissions) or set(omissions)&set(selected):raise ValueError('invalid omission selections')
 omission_audit=[]
 for id in omissions:
  e=edges.get(id)
  if not e or e.get('connection_mode')!='omission_pair_stitched_at_main_marker' or len(e.get('attribute_paths',[]))!=2 or e.get('path_length_complete') is not None:raise ValueError('unsupported omission edge')
  endpoints=[nodes.get(e.get(k),{}) for k in ('start_node_id','end_node_id')]
  if sum(n.get('node_type')=='equipment' for n in endpoints)!=1:raise ValueError('omission edge must have one equipment endpoint')
  a,b=e['attribute_paths']
  if len(a)<2 or len(b)<2 or min(math.dist(x,y) for x in (a[0],a[-1]) for y in (b[0],b[-1]))<=.05:raise ValueError('omission paths are not separately expressed')
  drawn=sum(math.dist(x,y) for path in (a,b) for x,y in zip(path,path[1:]))
  old=e.get('path_length')
  if not isinstance(old,(int,float)) or isinstance(old,bool) or not math.isfinite(old) or abs(old-drawn)>.001:raise ValueError('omission drawing length mismatch')
  e['drawing_path_length']=old;e['path_length_complete']=False;e['path_length_scope']='drawing_paths_omission_connection_unverified';e['physical_length']='unknown'
  e['source_omission_length_status']={'source_sha256':source_hash,'input_graph_sha256':graph_hash,'scope':'two disjoint drawing paths; physical omission and equipment connection not measured'}
  omission_audit.append({'edge_id':id,'drawing_path_length':old,'physical_length':'unknown'})
 g.setdefault('metadata',{}).update(hil_ready=False,review_status='unreviewed')
 return g,{'status':'partial_source_lengths_physical_unknown','source_sha256':source_hash,'input_graph_sha256':graph_hash,'coverage_sha256':coverage_hash,'edges':audit,'omission_edges':omission_audit,'review_inherited':False,'hil_ready':False}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','coverage','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();gb=a.graph.read_bytes();cb=a.coverage.read_bytes();pb=a.policy.read_bytes();sha=lambda x:hashlib.sha256(x).hexdigest();g,r=apply(json.loads(gb),json.loads(cb),sha(a.source.read_bytes()),sha(gb),sha(cb),json.loads(pb));a.output.mkdir(parents=True,exist_ok=False)
 out=a.output/'graph_with_edges.json';out.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8');r.update(output_graph_sha256=sha(out.read_bytes()),policy_sha256=sha(pb),script_sha256=sha(Path(__file__).read_bytes()));(a.output/'source_length_status_audit.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':r['status'],'edges':len(r['edges']),'output_graph_sha256':r['output_graph_sha256']}))
if __name__=='__main__':main()
