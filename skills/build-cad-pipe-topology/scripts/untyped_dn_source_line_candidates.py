"""Source-pinned nearby untyped lines for unmatched DN text, without recovery."""
import argparse,hashlib,json,math
from pathlib import Path
from source_direct_dn_evidence import _projection,LAYERS
from pipe_annotation_attributes import parse_dn_annotation
from source_readability import read_source


def scan(doc,bulk,policy,source_hash,graph_hash,bulk_hash,tol=.05):
 if (policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or policy.get('bulk_screen_sha256')!=bulk_hash
     or bulk.get('source_sha256')!=source_hash or bulk.get('graph_sha256')!=graph_hash or bulk.get('status')!='native_dn_bulk_screen_candidates_only'
     or bulk.get('graph_mutated') is not False or bulk.get('hil_ready') is not False):raise ValueError('stale source evidence')
 selected=policy.get('selections');rows=bulk.get('records',[]);records={r['text_handle']:r for r in rows}
 if not isinstance(selected,list) or not selected or len(records)!=len(rows) or len({x['text_handle'] for x in selected})!=len(selected) or len({x['line_handle'] for x in selected})!=len(selected):raise ValueError('invalid selection')
 result=[]
 for item in selected:
  t=doc.entitydb.get(item['text_handle']);line=doc.entitydb.get(item['line_handle']);row=records.get(item['text_handle'])
  if (not t or t.dxftype()!='TEXT' or t not in doc.modelspace() or t.plain_text()!=item['expected_text'] or not parse_dn_annotation(t.plain_text())
      or not row or row.get('status')!='no_source_line_in_local_scope' or row.get('text')!=t.plain_text()
      or not line or line.dxftype()!='LINE' or line not in doc.modelspace() or line.dxf.layer!=item['expected_layer'] or line.dxf.layer in LAYERS.values()):raise ValueError('selected source entities mismatch')
  a=(line.dxf.start.x,line.dxf.start.y);b=(line.dxf.end.x,line.dxf.end.y);p=(t.dxf.insert.x,t.dxf.insert.y);length=math.dist(a,b);height=float(t.dxf.height);angle=math.radians(t.dxf.rotation)
  if not isinstance(row.get('position'),list) or len(row['position'])!=2 or math.dist(p,row['position'])>tol:raise ValueError('bulk text position mismatch')
  if not all(math.isfinite(x) for x in (*a,*b,*p,length,height,angle)) or length<=tol or height<=0:raise ValueError('invalid source geometry')
  if abs(math.cos(angle)*(b[1]-a[1])-math.sin(angle)*(b[0]-a[0]))/length>math.sin(math.radians(2)):raise ValueError('text and line not parallel')
  q=_projection(p,a,b)
  if q is None or not -.2<=q[0]<=1.2 or q[1]>2*height:raise ValueError('text and untyped line not locally aligned')
  contacts=[]
  for side,point in [('start',a),('end',b)]:
   for candidate in doc.modelspace().query('LINE'):
    if candidate.dxf.layer not in LAYERS.values():continue
    x=(candidate.dxf.start.x,candidate.dxf.start.y);y=(candidate.dxf.end.x,candidate.dxf.end.y);v=_projection(point,x,y)
    if v and -.000001<=v[0]<=1.000001 and v[1]<=tol:contacts.append({'side':side,'source_handle':candidate.dxf.handle,'layer':candidate.dxf.layer})
  result.append({'text_handle':t.dxf.handle,'text':t.plain_text(),'line_handle':line.dxf.handle,'line_layer':line.dxf.layer,'line_endpoints':[list(a),list(b)],'text_position':list(p),'projection_fraction':q[0],'distance_drawing_units':q[1],'typed_modelspace_endpoint_contacts':contacts,'status':'untyped_source_line_semantics_unresolved'})
 return {'status':'untyped_source_lines_not_pipe_assignment','source_sha256':source_hash,'graph_sha256':graph_hash,'bulk_screen_sha256':bulk_hash,'records':result,'graph_mutated':False,'pipe_system_selected':False,'hil_ready':False,
         'limitations':['Only explicitly selected modelspace TEXT and untyped LINEs are examined; other entities, nested lines and proxies are not a complete search.',
                        'Parallel geometry does not prove the line is a pipe or a leader, nor does it establish pipe system, connection or DN applicability.',
                        'No typed modelspace endpoint contact is not proof of no nested, curved or off-scope connection.']}


def main():
 p=argparse.ArgumentParser()
 for name in ('source','graph','bulk-screen','policy','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));doc,proof=read_source(a.source)
 r=scan(doc,load(a.bulk_screen),load(a.policy),proof['source_sha256'],sha(a.graph),sha(a.bulk_screen));r.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'records':len(r['records'])}))
if __name__=='__main__':main()
