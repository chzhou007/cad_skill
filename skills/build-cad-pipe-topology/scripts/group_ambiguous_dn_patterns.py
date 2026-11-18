"""Group explicit repeated source-DN ambiguity signatures; do not select an owner."""
import argparse,hashlib,json,math
from pathlib import Path


def group(screen,policy,tol=.01):
 if screen.get('status')!='native_dn_bulk_screen_candidates_only' or screen.get('graph_mutated') is not False or screen.get('human_accepted') is not False or screen.get('hil_ready') is not False:raise ValueError('invalid source screen state')
 rows=screen.get('records');groups=policy.get('groups')
 if not isinstance(rows,list) or not isinstance(groups,list) or not groups:raise ValueError('invalid records or groups')
 by={r['text_handle']:r for r in rows}
 if len(by)!=len(rows):raise ValueError('duplicate text handle')
 used=set();output=[]
 def signature(row):
  if row.get('status')!='ambiguous_source_lines' or not isinstance(row.get('text'),str) or not row['text']:raise ValueError('not an ambiguous source text')
  height=row.get('height');angle=row.get('rotation_degrees');hits=row.get('native_line_candidates')
  if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (height,angle)) or height<=0 or not isinstance(hits,list) or len(hits)<2:raise ValueError('invalid ambiguity signature')
  result=[]
  for h in hits:
   distance=h.get('distance_drawing_units');system=h.get('system');scope=h.get('provenance',{}).get('scope')
   if isinstance(distance,bool) or not isinstance(distance,(int,float)) or not math.isfinite(distance) or distance<0 or system not in ('supply','return') or scope not in ('modelspace','graph_referenced_insert'):raise ValueError('invalid native line candidate')
   result.append((system,scope,distance))
  return row['text'],height,angle,result
 for selection in groups:
  handles=selection.get('text_handles')
  if not isinstance(handles,list) or len(handles)<2 or len(handles)!=len(set(handles)) or used.intersection(handles):raise ValueError('invalid or repeated group')
  used.update(handles);selected=[by.get(h) for h in handles]
  if any(r is None for r in selected):raise ValueError('missing source text')
  signatures=[signature(r) for r in selected];first=signatures[0]
  for s in signatures[1:]:
   if s[0]!=first[0] or abs(s[1]-first[1])>tol or abs(s[2]-first[2])>tol or len(s[3])!=len(first[3]) or any(a[:2]!=b[:2] or abs(a[2]-b[2])>tol for a,b in zip(s[3],first[3])):raise ValueError('candidate signatures differ')
  output.append({'text_handles':handles,'source_text':first[0],'candidate_signature':[{'system':s,'source_scope':k,'distance_drawing_units':v} for s,k,v in first[3]],'status':'repeated_ambiguity_not_attribution','selected_owner':None})
 return {'status':'repeated_dn_ambiguity_patterns_not_attribution','groups':output,'graph_mutated':False,'mapping_ready':False,'hil_ready':False,
         'limitations':['Groups compare selected text, rotation, height and ordered candidate distance/system/scope only; other source geometry and unselected labels remain outside this check.',
                        'Matching signatures do not prove identical semantics, source ownership, connectivity or cross-floor correspondence.',
                        'Original per-text ambiguity records remain pending.']}


def main():
 p=argparse.ArgumentParser()
 for name in ('bulk-screen','policy','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();screen=json.loads(a.bulk_screen.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'))
 if policy.get('bulk_screen_sha256')!=sha(a.bulk_screen) or policy.get('source_sha256')!=screen.get('source_sha256') or policy.get('graph_sha256')!=screen.get('graph_sha256'):raise ValueError('stale source screen')
 r=group(screen,policy);r.update(bulk_screen_sha256=sha(a.bulk_screen),source_sha256=screen['source_sha256'],graph_sha256=screen['graph_sha256'],policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'groups':len(r['groups'])}))
if __name__=='__main__':main()
