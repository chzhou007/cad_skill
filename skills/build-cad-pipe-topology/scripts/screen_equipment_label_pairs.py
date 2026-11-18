"""Compare two-instance label assignments without selecting an identity."""
import argparse,hashlib,itertools,json,math
from pathlib import Path
from native_equipment_body import body_straight_segments
from native_dn_text_position import supported
from source_readability import read_source

def screen(plan_doc,axis_doc,plan,axis,receipt,policy,hashes):
 for k in ('plan_source_sha256','axis_source_sha256','plan_graph_sha256','axis_graph_sha256','axis_receipt_sha256'):
  if not hashes.get(k) or policy.get(k)!=hashes[k]:raise ValueError('stale '+k)
 if plan.get('metadata',{}).get('source_sha256')!=hashes['plan_source_sha256']:raise ValueError('plan source mismatch')
 if receipt.get('inputs',{}).get('dxf')!=hashes['axis_source_sha256'] or receipt.get('final_graph_sha256')!=hashes['axis_graph_sha256'] or receipt.get('hil_ready') is not False:raise ValueError('axis receipt mismatch')
 nodes={n['node_id']:n for n in plan['nodes']};axis_nodes={n['node_id']:n for n in axis['nodes']};groups=policy.get('groups');out=[];used=set()
 if not isinstance(groups,list) or not groups or len(nodes)!=len(plan['nodes']) or len(axis_nodes)!=len(axis['nodes']):raise ValueError('invalid graph or groups')
 for group in groups:
  nh=group.get('node_ids');lh=group.get('label_handles')
  if not isinstance(nh,list) or not isinstance(lh,list) or len(nh)!=2 or len(lh)!=2 or len(set(nh+lh))!=4 or used.intersection(nh+lh):raise ValueError('invalid pair scope')
  used.update(nh+lh);equipment=[];labels=[]
  for nid in nh:
   n=nodes.get(nid);handle=n.get('source_handle') if n else None;ent=plan_doc.entitydb.get(handle) if handle else None
   if not n or n.get('identity_status')!='unresolved' or n.get('node_type')!='equipment' or not ent or ent.dxftype()!='INSERT' or ent not in plan_doc.modelspace() or ent.dxf.name!=n.get('source_block'):raise ValueError('equipment source mismatch')
   body,unsupported=body_straight_segments(ent)
   if not body or unsupported:raise ValueError('unsupported equipment geometry')
   bounds=[[min(p[i] for seg in body for p in seg) for i in (0,1)],[max(p[i] for seg in body for p in seg) for i in (0,1)]];center=[(bounds[0][i]+bounds[1][i])/2 for i in (0,1)]
   if math.dist(center,[n['x'],n['y']])>.05:raise ValueError('equipment position mismatch')
   equipment.append({'node_id':nid,'source_handle':handle,'center':center})
  for h in lh:
   ent=plan_doc.entitydb.get(h)
   if not ent or ent not in plan_doc.modelspace() or not supported(ent) or ent.dxf.layer!='空调编号':raise ValueError('label source mismatch')
   text=ent.plain_text();axis_matches=[n for n in axis['nodes'] if n.get('node_id')==text and n.get('node_type')=='equipment'];source_matches=[e for e in axis_doc.modelspace().query('TEXT MTEXT') if e.plain_text()==text]
   if not text or len(axis_matches)!=1 or len(source_matches)!=1 or text in nodes:raise ValueError('label identity not uniquely scoped')
   labels.append({'handle':h,'text':text,'position':[ent.dxf.insert.x,ent.dxf.insert.y],'rotation':float(ent.dxf.get('rotation',0)),'axis_node_id':text,'axis_text_handle':source_matches[0].dxf.handle})
  if len({x['text'] for x in labels})!=2 or any(abs(x['rotation']-90)>1e-6 for x in labels):raise ValueError('unsupported label pattern')
  max_distance=group.get('maximum_distance')
  if not isinstance(max_distance,(float,int)) or isinstance(max_distance,bool) or not 0<max_distance<=5000:raise ValueError('invalid distance scope')
  options=[]
  for perm in itertools.permutations(labels):
   assignments=[]
   for n,t in zip(equipment,perm):
    dist=math.dist(n['center'],t['position'])
    if dist>max_distance:raise ValueError('candidate exceeds scoped distance')
    assignments.append({'plan_node_id':n['node_id'],'label':t['text'],'plan_text_handle':t['handle'],'axis_node_id':t['axis_node_id'],'axis_text_handle':t['axis_text_handle'],'offset':[t['position'][i]-n['center'][i] for i in (0,1)],'distance_drawing_units':dist})
   options.append({'assignments':assignments,'same_vertical_order':(equipment[0]['center'][1]-equipment[1]['center'][1])*(perm[0]['position'][1]-perm[1]['position'][1])>0})
  out.append({'group_id':group['id'],'candidates':options,'selected_candidate':None,'status':'pair_identity_not_confirmed'})
 return {'status':'equipment_label_pair_candidates_not_mapping','plan_source_sha256':hashes['plan_source_sha256'],'axis_source_sha256':hashes['axis_source_sha256'],'plan_graph_sha256':hashes['plan_graph_sha256'],'axis_graph_sha256':hashes['axis_graph_sha256'],'groups':out,'graph_mutated':False,'mapping_ready':False,'human_accepted':False,'hil_ready':False,'limitations':['Explicit two-instance source scopes only; no full drawing search.','Ordering, proximity and a matching axis label do not establish identity, port ownership or cross-view connectivity.','Both one-to-one assignments remain possible and require source review.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('plan-source','axis-source','plan-graph','axis-graph','axis-receipt','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));pd,pp=read_source(a.plan_source);ad,ap=read_source(a.axis_source)
 hashes={'plan_source_sha256':pp['source_sha256'],'axis_source_sha256':ap['source_sha256'],'plan_graph_sha256':sha(a.plan_graph),'axis_graph_sha256':sha(a.axis_graph),'axis_receipt_sha256':sha(a.axis_receipt)};r=screen(pd,ad,load(a.plan_graph),load(a.axis_graph),load(a.axis_receipt),load(a.policy),hashes);r.update(axis_receipt_sha256=hashes['axis_receipt_sha256'],policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),text_guard_sha256=sha(Path(__file__).with_name('native_dn_text_position.py')))
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'groups':len(r['groups'])}))
if __name__=='__main__':main()
