"""Compare candidate interface positions relative to source annotation frames."""
import argparse,hashlib,json,math
from pathlib import Path


def compare(frames,glyphs,graph,hashes,tolerance=.1):
 from canonicalize_confirmed_sideviews import source_expression_context
 graph=source_expression_context(graph)
 if not 0<tolerance<=.1:raise ValueError('invalid tolerance')
 if (frames.get('status')!='source_dashed_frame_context_not_mapping' or frames.get('source_sha256')!=hashes['source_sha256'] or frames.get('graph_sha256')!=hashes['graph_sha256'] or frames.get('glyphs_sha256')!=hashes['glyphs_sha256'] or frames.get('mapping_ready') is not False or frames.get('human_accepted') is not False or glyphs.get('source_sha256')!=hashes['source_sha256'] or glyphs.get('graph_sha256')!=hashes['graph_sha256'] or glyphs.get('graph_mutated') is not False):raise ValueError('stale frame or glyph evidence')
 fs={x['frame_id']:x for x in frames['frames']};candidates=frames['candidate_rows'];rows=glyphs['rows'];edges={e['edge_id']:e for e in graph['edges']}
 def key(x):return (x['system'],x['rank'],x['upper_edge'],x['detail_edge'])
 if len(fs)!=len(frames['frames']) or len(candidates)!=len(rows) or len(edges)!=len(graph['edges']) or [key(x) for x in candidates]!=[key(x) for x in rows] or len({key(x) for x in rows})!=len(rows):raise ValueError('candidate scope mismatch')
 out=[]
 for f,row in zip(candidates,rows):
  system=row['system'];upper=edges.get(row['upper_edge']);detail=edges.get(row['detail_edge']);shared=f['shared_frame_candidates']
  if system not in ('supply','return') or not upper or not detail or upper.get('system')!=system or detail.get('system')!=system or f['status']!='source_frame_context_not_individual_mapping' or len(shared)!=1 or shared[0] not in fs:raise ValueError('invalid frame candidate')
  frame=fs[shared[0]];offset=frame['source_line_offset'];u=row['upper']['center'];d=row['detail']['center']
  if any(not math.isfinite(float(v)) for v in (u[0],u[1],d[0],d[1],offset[0],offset[1])):raise ValueError('invalid coordinates')
  projected_x=u[0]-offset[0]; pool=[]
  for cf,c in zip(candidates,rows):
   if c['system']==system and shared[0] in cf['shared_frame_candidates']:
    pool.append({'detail_edge':c['detail_edge'],'rank':c['rank'],'horizontal_residual_drawing_units':projected_x-c['detail']['center'][0]})
  if not pool:raise ValueError('empty regional candidate pool')
  minimum=min(abs(x['horizontal_residual_drawing_units']) for x in pool)
  closest=[x for x in pool if abs(abs(x['horizontal_residual_drawing_units'])-minimum)<=tolerance]
  out.append({'system':system,'rank':row['rank'],'upper_edge':row['upper_edge'],'proposed_detail_edge':row['detail_edge'],'frame_id':shared[0],
              'proposed_horizontal_residual_drawing_units':projected_x-d[0],
              'proposed_vertical_residual_drawing_units':u[1]-offset[1]-d[1],
              'closest_in_scoped_pool':closest,'proposed_is_closest':any(x['detail_edge']==row['detail_edge'] for x in closest),
              'status':'regional_position_evidence_not_mapping'})
 return {'status':'frame_relative_position_not_mapping','source_sha256':hashes['source_sha256'],'graph_sha256':hashes['graph_sha256'],'glyphs_sha256':hashes['glyphs_sha256'],'frames_sha256':hashes['frames_sha256'],
         'records':out,'mapping_ready':False,'graph_mutated':False,'human_accepted':False,'hil_ready':False,
         'limitations':['Relative drawing positions and nearest candidate do not prove individual interface identity, physical connection or equal length.',
                        'Candidate pool is limited to previously inventoried glyphs; vertical residual is descriptive, not a physical measurement.']}


def main():
 p=argparse.ArgumentParser()
 for k in ('frames','glyphs','graph','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text(encoding='utf8'))
 f=read(a.frames);g=read(a.graph);hashes={'source_sha256':g.get('metadata',{}).get('source_sha256'),'graph_sha256':sha(a.graph),'glyphs_sha256':sha(a.glyphs),'frames_sha256':sha(a.frames)}
 result=compare(f,read(a.glyphs),g,hashes);result['script_sha256']=sha(Path(__file__))
 with a.output.open('x',encoding='utf8') as out:json.dump(result,out,ensure_ascii=False,indent=2);out.write('\n')
 print(json.dumps({'records':len(result['records']),'mapping_ready':False}))
if __name__=='__main__':main()
