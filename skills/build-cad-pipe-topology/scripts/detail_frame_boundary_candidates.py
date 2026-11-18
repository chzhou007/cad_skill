"""Compare source-frame positions for scoped non-node boundary candidates."""
import argparse,hashlib,json,math
from pathlib import Path

def compare(frames,scope,boundaries,graph,hashes,tol=1.0):
 if not 0<tol<=1:raise ValueError('invalid tolerance')
 source=hashes['source_sha256'];gh=hashes['graph_sha256']
 if (frames.get('status')!='source_dashed_frame_context_not_mapping' or scope.get('status')!='scoped_coverage_not_mapping' or boundaries.get('status')!='ordered_candidates_not_mapping' or any(x.get('source_sha256')!=source or x.get('graph_sha256')!=gh for x in (frames,scope,boundaries)) or boundaries.get('scope_sha256')!=hashes['scope_sha256'] or any(x.get('mapping_ready') is not False or x.get('graph_mutated') is not False or x.get('human_accepted') is not False for x in (frames,scope,boundaries))):raise ValueError('stale frame or boundary evidence')
 fs=frames.get('frames',[]);upper=scope.get('upper',[]);anchors=boundaries.get('anchors',[]);rows=boundaries.get('rows',[])
 F={x['frame_id']:x for x in fs};U={x['node_id']:x for x in upper};A={x['boundary_id']:x for x in anchors};edges={e['edge_id']:e for e in graph['edges']}
 if len(F)!=len(fs) or len(U)!=len(upper) or len(A)!=len(anchors) or len(edges)!=len(graph['edges']) or not rows:raise ValueError('invalid or duplicate scope')
 def inside(p,b):return b[0]-tol<=p[0]<=b[2]+tol and b[1]-tol<=p[1]<=b[3]+tol
 output=[];seen=set()
 for row in rows:
  uid=row['upper_glyph'];aid=row['detail_boundary'];s=row['system'];key=(uid,aid)
  if key in seen:raise ValueError('duplicate boundary candidate')
  seen.add(key);u=U.get(uid);a=A.get(aid);e=edges.get(row['detail_edge'])
  if (s not in ('supply','return') or not u or not a or not e or u['system']!=s or a['system']!=s or e.get('system')!=s or a.get('edge_id')!=row['detail_edge'] or a.get('kind') not in ('expert_non_node_source_boundary','user_confirmed_non_node_source_boundary') or a.get('circle_handle')!=row.get('source_circle_handle') or a.get('pipe_handle')!=row.get('source_pipe_handle') or row.get('status') not in ('ordered_candidate_not_connection','offset_exception_not_connection')):raise ValueError('invalid boundary candidate')
  matches=[f for f in fs if inside(u['center'],f['upper_bounds']) and inside(a['center'],f['lower_bounds'])]
  if len(matches)!=1:raise ValueError('boundary candidate has no unique regional frame')
  f=matches[0];dx,dy=f['source_line_offset'];uc=u['center'];ac=a['center']
  if any(not math.isfinite(float(v)) for v in (uc[0],uc[1],ac[0],ac[1],dx,dy)):raise ValueError('invalid source position')
  output.append({'system':s,'upper_glyph':uid,'detail_boundary':aid,'detail_edge':row['detail_edge'],'boundary_kind':a['kind'],'frame_id':f['frame_id'],
                 'horizontal_residual_drawing_units':uc[0]-ac[0]-dx,'vertical_residual_drawing_units':uc[1]-ac[1]-dy,
                 'source_offset_status':row['status'],'status':'source_frame_boundary_context_not_mapping'})
 return {'status':'frame_boundary_candidates_not_mapping','source_sha256':source,'graph_sha256':gh,'frames_sha256':hashes['frames_sha256'],'scope_sha256':hashes['scope_sha256'],'boundaries_sha256':hashes['boundaries_sha256'],
         'records':output,'mapping_ready':False,'graph_mutated':False,'human_accepted':False,'hil_ready':False,
         'limitations':['Non-node boundary semantics are preserved; frame geometry does not create a node or pipe connection.',
                        'Ordered positional candidates are not independently confirmed one-to-one matches; drawing residuals are not physical lengths.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('frames','scope','boundaries','graph','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text(encoding='utf8'));g=read(a.graph)
 hashes={'source_sha256':g.get('metadata',{}).get('source_sha256'),'graph_sha256':sha(a.graph),'frames_sha256':sha(a.frames),'scope_sha256':sha(a.scope),'boundaries_sha256':sha(a.boundaries)}
 out=compare(read(a.frames),read(a.scope),read(a.boundaries),g,hashes);out['script_sha256']=sha(Path(__file__))
 with a.output.open('x',encoding='utf8') as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'records':len(out['records']),'mapping_ready':False}))
if __name__=='__main__':main()
