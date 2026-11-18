"""Compare source-witnessed cross-floor drawing segments with source datum offsets.

This is a diagnostic only. It does not assign physical orientation or length.
"""
import argparse,hashlib,json,math
from decimal import Decimal
from pathlib import Path
from source_readability import read_source
from native_line_path_evidence import collect as collect_lines
from native_level_evidence import verify as verify_levels

def diagnose(graph,line_evidence,datums,tol=.05):
 if not math.isfinite(tol) or not 0<tol<=.05:raise ValueError('invalid tolerance')
 levels={x['floor_number']:x for x in datums['levels']};witnesses={x['edge_id']:x for x in line_evidence['edges']};rows=[]
 if len(levels)!=len(datums['levels']) or len(witnesses)!=len(line_evidence['edges']):raise ValueError('duplicate source evidence')
 for e in graph['edges']:
  f1=e.get('floor_start');f2=e.get('floor_end')
  if f1==f2:continue
  row={'edge_id':e['edge_id'],'system':e.get('system'),'floor_start':f1,'floor_end':f2,'connection_mode':e.get('connection_mode'),'segments':[],'status':'source_path_not_witnessed'}
  if f1 not in levels or f2 not in levels:row['status']='floor_datum_missing';rows.append(row);continue
  y1=levels[f1]['datum_y_drawing_units'];y2=levels[f2]['datum_y_drawing_units'];expected=abs(y2-y1);delta=abs(Decimal(levels[f2]['elevation_numeric_decimal'])-Decimal(levels[f1]['elevation_numeric_decimal']))
  row['source_datum_difference']=str(delta);row['source_datum_unit']=datums['source_level_unit'];row['source_datum_drawing_delta']=expected
  witness=witnesses.get(e['edge_id'])
  if witness is None:rows.append(row);continue
  paths=e.get('attribute_paths',[]);segs=witness['segments']
  if len(paths)!=1 or len(segs)!=len(paths[0])-1 or witness.get('system')!=e.get('system'):raise ValueError('source segment evidence inconsistent')
  for index,(a,b) in enumerate(zip(paths[0],paths[0][1:])):
   s=segs[index]
   if s['graph_start']!=a or s['graph_end']!=b:raise ValueError('source segment sequence changed')
   dx=b[0]-a[0];dy=b[1]-a[1];vertical=abs(dx)<=tol and abs(dy)>tol;matches=vertical and abs(abs(dy)-expected)<=tol
   row['segments'].append({'segment_index':index,'source_handle':s['source_handle'],'drawing_direction':'vertical' if vertical else 'nonvertical','drawing_length':math.dist(a,b),'matches_datum_drawing_delta':matches,'interpretation':'datum_difference_candidate_only' if matches else 'no_datum_length_inference'})
  row['status']='datum_aligned_vertical_candidate' if any(s['matches_datum_drawing_delta'] for s in row['segments']) else 'no_datum_aligned_vertical_segment'
  rows.append(row)
 return {'status':'candidate_diagnostics_not_physical_length','edges':rows,'graph_mutated':False,'hil_ready':False,'limitations':['Graph floor labels and connectivity remain independently unverified.','Vertical direction in the drawing does not alone establish a physical vertical segment.','Equal drawing offsets do not prove actual pipe end elevations; source datum unit requires project-note verification.','Datum differences are candidate values, not edge lengths or accepted fusion.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','line-evidence','line-policy','datum-evidence','datum-policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);g=json.loads(a.graph.read_text(encoding='utf8'));le=json.loads(a.line_evidence.read_text(encoding='utf8'));lp=json.loads(a.line_policy.read_text(encoding='utf8'));de=json.loads(a.datum_evidence.read_text(encoding='utf8'));dp=json.loads(a.datum_policy.read_text(encoding='utf8'))
 checked=collect_lines(doc,g,lp,proof['source_sha256'],sha(a.graph));datum=verify_levels(doc,dp,proof['source_sha256'])
 if le.get('graph_sha256')!=sha(a.graph) or le.get('source_sha256')!=proof['source_sha256'] or le['edges']!=checked['edges']:raise ValueError('line evidence stale')
 if de.get('source_sha256')!=proof['source_sha256'] or de['levels']!=datum['levels'] or de['consecutive_datum_differences']!=datum['consecutive_datum_differences']:raise ValueError('datum evidence stale')
 out=diagnose(g,le,datum);out.update(source_sha256=proof['source_sha256'],graph_sha256=sha(a.graph),line_evidence_sha256=sha(a.line_evidence),line_policy_sha256=sha(a.line_policy),datum_evidence_sha256=sha(a.datum_evidence),datum_policy_sha256=sha(a.datum_policy),script_sha256=sha(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'cross_floor_edges':len(out['edges']),'candidates':sum(x['status']=='datum_aligned_vertical_candidate' for x in out['edges'])}))
if __name__=='__main__':main()
