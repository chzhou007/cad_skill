"""Audit scoped excluded-detail DN texts without inferring view correspondence."""
import argparse,dataclasses,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'legacy_v17'))
import analyze_graph as geometry
from source_readability import read_source


def classify(doc,screen,policy,source_hash,graph_hash,bulk_hash):
 if (policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or policy.get('bulk_screen_sha256')!=bulk_hash
     or screen.get('source_sha256')!=source_hash or screen.get('graph_sha256')!=graph_hash
     or screen.get('status')!='native_dn_bulk_screen_candidates_only' or screen.get('graph_mutated') is not False or screen.get('hil_ready') is not False):raise ValueError('source, graph or bulk screen mismatch')
 scopes=policy.get('scopes')
 if scopes is None:scopes=[{'scope_id':'left','side':'left','title':policy.get('title',{}),'text_handles':policy.get('text_handles')}]
 if not isinstance(scopes,list) or not scopes or any(not isinstance(x,dict) or not isinstance(x.get('scope_id'),str) or not x['scope_id'] or x.get('side') not in ('left','right') for x in scopes) or len({x['scope_id'] for x in scopes})!=len(scopes):raise ValueError('invalid scope list')
 rows=screen.get('records',[]);by={r['text_handle']:r for r in rows}
 if len(by)!=len(rows):raise ValueError('invalid selected labels')
 layout=geometry.infer_drawing_layout(geometry.equipment_labels(doc));result=[];titles=[];seen=set()
 for scope in scopes:
  title=scope.get('title',{});t=doc.entitydb.get(title.get('handle'))
  if not t or t.dxftype()!='TEXT' or t not in doc.modelspace() or t.plain_text()!=title.get('text') or t.dxf.layer!=title.get('layer'):raise ValueError('native title mismatch')
  titles.append({'scope_id':scope['scope_id'],'handle':t.dxf.handle,'text':t.plain_text(),'position':[t.dxf.insert.x,t.dxf.insert.y],'layer':t.dxf.layer})
  labels=scope.get('text_handles')
  if not isinstance(labels,list) or not labels or len(labels)!=len(set(labels)) or seen.intersection(labels):raise ValueError('invalid selected labels')
  seen.update(labels)
  for handle in labels:
   r=by.get(handle);text=doc.entitydb.get(handle)
   if (not r or r.get('status')!='no_source_line_in_local_scope' or not text or text.dxftype()!='TEXT' or text not in doc.modelspace()
       or text.plain_text()!=r.get('text') or text.dxf.layer!=r.get('layer')):raise ValueError('selected source text mismatch')
   p=text.dxf.insert;pos=r.get('position')
   if not isinstance(pos,list) or len(pos)!=2 or abs(p.x-pos[0])>.05 or abs(p.y-pos[1])>.05:raise ValueError('source text position mismatch')
   inside=geometry.is_excluded_detail_point(p.x,p.y,layout) if scope['side']=='left' else p.x>layout.right_detail_x_min and p.y<layout.right_detail_y_max
   if not inside:raise ValueError('selected text is not in excluded '+scope['side']+' scope')
   result.append({'scope_id':scope['scope_id'],'side':scope['side'],'text_handle':handle,'text':text.plain_text(),'position':[p.x,p.y],'status':'excluded_'+scope['side']+'_scope_detail_correspondence_pending'})
 return {'status':'excluded_scope_not_main_assignment','source_sha256':source_hash,'graph_sha256':graph_hash,'bulk_screen_sha256':bulk_hash,
         'legacy_layout':dataclasses.asdict(layout),'titles':titles,
         'records':result,'graph_mutated':False,'detail_mapping_ready':False,'human_accepted':False,'hil_ready':False,
         'limitations':['Scope follows current SH16 legacy layout anchor and exclusion rule; a title insertion point is not a proven view boundary.',
                        'Excluded texts are retained as detail-scope evidence; their pipe ownership and relationship to the main system remain unresolved.',
                        'No graph edge, diameter, physical length or cross-view mapping is assigned.']}


def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','bulk-screen','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));doc,proof=read_source(a.source)
 r=classify(doc,load(a.bulk_screen),load(a.policy),proof['source_sha256'],sha(a.graph),sha(a.bulk_screen));r.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),legacy_geometry_sha256=sha(Path(geometry.__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'records':len(r['records'])}))
if __name__=='__main__':main()
