"""Source-pinned non-connecting main/detail candidate comparison for SH16 09."""
from pathlib import Path
import argparse,copy,csv,hashlib,json,math,statistics,shutil,sys
if sys.flags.optimize:raise RuntimeError('Source evidence checks require assertions enabled')
from source_readability import read_source
ap=argparse.ArgumentParser()
for k in ('source','graph','devices','issue','policy','output'):ap.add_argument('--'+k,type=Path,required=True)
args=ap.parse_args();src=args.source;inp=args.graph;issue=args.issue;read=lambda p:json.loads(p.read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();policy=read(args.policy)
for k,p in [('source_sha256',src),('input_graph_sha256',inp),('devices_sha256',args.devices),('issue_sha256',issue)]:
 if sha(p)!=policy[k]:raise ValueError(k+' mismatch')
if policy.get('scope')!='SH16-09-detail-main-candidates-only':raise ValueError('invalid comparison scope')
g=read(inp);before=copy.deepcopy(g);it=read(issue);doc,proof=read_source(src)
if proof['source_sha256']!=g.get('metadata',{}).get('source_sha256') or proof['source_sha256']!=it['sourceHashes']['main_dxf'] or it['issue']['label']!='ERR-15B0E8' or it['issue']['note']!=policy['expert_note']:raise ValueError('source or expert issue mismatch')
circles=list(doc.modelspace().query('CIRCLE'));pairs=[]
for service,layer,mainh,y in [('supply','空调冷冻水供水','B791',35548.921),('return','空调冷冻水回水','B794',36148.921)]:
 low=sorted([n for n in g['nodes'] if n.get('system')==service and n['node_type']=='tee' and 2304000<n.get('x',0)<2330000 and abs(n.get('y',0)-y)<1],key=lambda n:n['x'])
 high=sorted([n for n in g['nodes'] if n.get('system')==service and n.get('subtype')=='unresolved_source_terminal' and 2322000<n.get('x',0)<2349000 and 53590<n.get('y',0)<53610],key=lambda n:n['x']);assert len(low)==len(high)==10
 offsets=[b['x']-a['x'] for a,b in zip(low,high)];baseline=statistics.median(offsets)
 for rank,(a,b) in enumerate(zip(low,high),1):
  branch=[h for h in a['source_handles'] if h!=mainh];assert len(branch)==1 and len(b['source_handles'])==1
  e1=doc.entitydb[branch[0]];e2=doc.entitydb[b['source_handles'][0]];assert e1.dxftype()==e2.dxftype()=='LINE' and e1.dxf.layer==e2.dxf.layer==layer
  witness=[c for c in circles if c.dxf.layer==layer and abs(c.dxf.radius-100)<.05 and math.hypot(c.dxf.center.x-a['x'],c.dxf.center.y-a['y'])<.05];assert len(witness)==1
  assert min(math.hypot(p.x-b['x'],p.y-b['y']) for p in (e2.dxf.start,e2.dxf.end))<.05
  assert abs(min(math.hypot(p.x-a['x'],p.y-a['y']) for p in (e1.dxf.start,e1.dxf.end))-100)<.05
  incident=[x for x in g['edges'] if a['node_id'] in (x['start_node_id'],x['end_node_id'])];assert len(incident)==3 and sum(branch[0] in e['source_handles'] for e in incident)==1
  upper=[e for e in g['edges'] if b['node_id'] in (e['start_node_id'],e['end_node_id'])];assert len(upper)==1 and b['source_handles'][0] in upper[0]['source_handles']
  residual=(b['x']-a['x'])-baseline
  pairs.append({'rank':rank,'system':service,'detail_tee':a['node_id'],'detail_circle':witness[0].dxf.handle,'detail_pipe':branch[0],'detail_xy':[a['x'],a['y']],'upper_terminal':b['node_id'],'upper_pipe':b['source_handles'][0],'upper_edge':upper[0]['edge_id'],'upper_xy':[b['x'],b['y']],'horizontal_offset':b['x']-a['x'],'offset_residual':residual,'pair_status':'candidate_not_confirmed','exception':'rightmost offset differs by 200 drawing units' if abs(residual)>1 else '','physical_equipment_correspondence':'unverified','hydraulic_link_created':False})
assert len(pairs)==20 and sum(bool(x['exception']) for x in pairs)==2
node_ids={n['node_id'] for n in g['nodes']};edge_ids={e['edge_id'] for e in g['edges']};assert all(x['upper_terminal'] in node_ids and x['detail_tee'] in node_ids and x['upper_edge'] in edge_ids for x in pairs)

g['sourceDetailComparison']={'expert_issue':'ERR-15B0E8','source_sha256':proof['source_sha256'],'source_graph_sha256':sha(inp),'expert_note':it['issue']['note'],'method':'same-service ordered correspondence with source-line and circle witnesses; no hydraulic links','pairs':pairs,'status':'candidate_mapping_equipment_and_boundaries_pending','hil_ready':False}
comparison=g.setdefault('preHilComparison',{'status':'pending','families':[]});comparison['status']='pending';families=comparison.setdefault('families',[]);families[:]=[f for f in families if f.get('id')!='SH16-09-detail-main-alternative'];families.append({'id':'SH16-09-detail-main-alternative','status':'algorithm_pending','disposition':'Deduplicate and replace only after proving equipment and boundary mapping; 20 branch candidates are comparison evidence, not links.'});g['metadata'].update(hil_ready=False,graph_complete=False,stage_status='detail_alternative_mapping_candidates_pending')
assert before['nodes']==g['nodes'] and before['edges']==g['edges']
length_audit=[]
if 'repair_source_branch_lengths' in policy and not isinstance(policy['repair_source_branch_lengths'],bool):raise ValueError('repair_source_branch_lengths must be boolean')
if policy.get('repair_source_branch_lengths',False):
 from source_detail_branch_lengths import repair as repair_detail_lengths
 g,length_audit=repair_detail_lengths(g,doc,proof['source_sha256'])
 if len(length_audit)!=20:raise ValueError('unexpected repaired detail branch count')
 assert before['nodes']==g['nodes']
out=args.output
if out.exists():raise ValueError('output exists')
out.mkdir(parents=True);target=out/'graph_with_edges.json';target.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(args.devices,out/'assigned_edge_device_instances.csv')
if length_audit:(out/'source-detail-branch-length-audit.json').write_text(json.dumps(length_audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
with (out/'支路候选对照.csv').open('w',encoding='utf-8-sig',newline='') as f:
 keys=['rank','system','detail_tee','detail_circle','detail_pipe','upper_terminal','upper_pipe','upper_edge','horizontal_offset','offset_residual','pair_status','exception','physical_equipment_correspondence'];writer=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');writer.writeheader();writer.writerows(pairs)
r={'source_sha256':sha(src),'input_graph_sha256':sha(inp),'devices_sha256':sha(args.devices),'issue_sha256':sha(issue),'policy_sha256':sha(args.policy),'output_graph_sha256':sha(target),'expert_issue':'ERR-15B0E8','candidate_pairs':len(pairs),'offset_exception':2,'existing_nodes':len(g['nodes']),'existing_edges':len(g['edges']),'hydraulic_links_created':0,'hil_ready':False,'expert_review':'unreviewed'};(out/'comparison-audit.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(r,ensure_ascii=False))
