"""Group same-text endpoint DN leads while retaining both system assignments."""
import argparse,hashlib,json,math
from pathlib import Path


def group(screen,policy):
 if screen.get('status')!='native_dn_bulk_screen_candidates_only' or screen.get('graph_mutated') is not False or screen.get('hil_ready') is not False or screen.get('human_accepted') is not False:raise ValueError('invalid source screen state')
 rows=screen.get('records');groups=policy.get('groups')
 if not isinstance(rows,list) or not isinstance(groups,list) or not groups:raise ValueError('invalid records or groups')
 by={r['text_handle']:r for r in rows}
 if len(by)!=len(rows):raise ValueError('duplicate source text')
 used=set();out=[]
 for selection in groups:
  handles=selection.get('text_handles')
  if not isinstance(handles,list) or len(handles)!=2 or len(set(handles))!=2 or used.intersection(handles):raise ValueError('duplicate or malformed pair')
  used.update(handles);pair=[by.get(h) for h in handles]
  if any(r is None or r.get('status')!='no_source_line_in_local_scope' for r in pair) or pair[0].get('text')!=pair[1].get('text') or pair[0].get('nominal_mm_candidate')!=pair[1].get('nominal_mm_candidate'):raise ValueError('not a matching unresolved text pair')
  value=pair[0].get('nominal_mm_candidate')
  if not isinstance(pair[0].get('text'),str) or not pair[0]['text'] or isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError('invalid paired DN text')
  contexts=[]
  for row in pair:
   hits=row.get('endpoint_context_candidates',[])
   if len(hits)!=2 or {h.get('system') for h in hits}!={'supply','return'}:raise ValueError('endpoint alternatives not exactly two systems')
   parsed={}
   for h in hits:
    witness=h.get('provenance',{});edges=h.get('graph_segment_candidates',[]);dist=h.get('distance_drawing_units')
    if witness.get('scope')!='modelspace' or not witness.get('handle') or len(edges)!=1 or not edges[0].get('edge_id') or isinstance(dist,bool) or not isinstance(dist,(int,float)) or not math.isfinite(dist) or dist<0:raise ValueError('endpoint source evidence not unique')
    parsed[h['system']]={'source_line_handle':witness['handle'],'edge_id':edges[0]['edge_id'],'distance_drawing_units':dist}
   contexts.append(parsed)
  if any(contexts[0][s][k]!=contexts[1][s][k] for s in ('supply','return') for k in ('source_line_handle','edge_id')):raise ValueError('pair does not share source alternatives')
  alternatives=[]
  for first_system,second_system in [('supply','return'),('return','supply')]:
   alternatives.append({'assignments':[{'text_handle':handles[0],'system':first_system,**contexts[0][first_system]},{'text_handle':handles[1],'system':second_system,**contexts[1][second_system]}],
                        'sum_distance_drawing_units':contexts[0][first_system]['distance_drawing_units']+contexts[1][second_system]['distance_drawing_units']})
  out.append({'text_handles':handles,'source_text':pair[0]['text'],'nominal_mm_candidate':pair[0]['nominal_mm_candidate'],
              'alternatives':alternatives,'status':'paired_context_not_attribution','selected_alternative':None})
 return {'status':'paired_endpoint_dn_context_not_attribution','groups':out,'graph_mutated':False,'mapping_ready':False,'hil_ready':False,
         'limitations':['Explicit selected labels only; grouping does not imply all source labels were screened.',
                        'Both one-per-system assignments remain possible; distance sums are geometric context, not a selection rule.',
                        'Text baseline beyond a line endpoint is not proof of ownership or a physical diameter.']}


def main():
 p=argparse.ArgumentParser()
 for name in ('bulk-screen','policy','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();screen=json.loads(a.bulk_screen.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'))
 if policy.get('bulk_screen_sha256')!=sha(a.bulk_screen) or policy.get('source_sha256')!=screen.get('source_sha256') or policy.get('graph_sha256')!=screen.get('graph_sha256'):raise ValueError('stale source screen')
 result=group(screen,policy);result.update(bulk_screen_sha256=sha(a.bulk_screen),source_sha256=screen['source_sha256'],graph_sha256=screen['graph_sha256'],policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':result['status'],'groups':len(result['groups'])}))
if __name__=='__main__':main()
