"""Expose both source-scoped pair label candidates without assigning identities."""
import argparse,copy,hashlib,json,shutil
from pathlib import Path
from source_readability import read_source
from screen_equipment_label_pairs import screen

def attach(graph,evidence,source_hash,graph_hash):
 if graph.get('metadata',{}).get('source_sha256')!=source_hash or evidence.get('plan_source_sha256')!=source_hash or evidence.get('plan_graph_sha256')!=graph_hash or evidence.get('status')!='equipment_label_pair_candidates_not_mapping' or evidence.get('graph_mutated') is not False or evidence.get('mapping_ready') is not False or evidence.get('human_accepted') is not False:raise ValueError('stale pair evidence')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};groups=evidence.get('groups');used=set()
 if len(nodes)!=len(out['nodes']) or not isinstance(groups,list) or not groups:raise ValueError('invalid pair groups')
 for group in groups:
  options=group.get('candidates');gid=group.get('group_id')
  if not isinstance(gid,str) or not gid or group.get('status')!='pair_identity_not_confirmed' or group.get('selected_candidate') is not None or not isinstance(options,list) or len(options)!=2:raise ValueError('invalid pair evidence')
  per=[]
  for option in options:
   rows=option.get('assignments')
   if not isinstance(rows,list) or len(rows)!=2 or len({r['plan_node_id'] for r in rows})!=2 or len({r['label'] for r in rows})!=2:raise ValueError('invalid pair assignment')
   per.append({r['plan_node_id']:r for r in rows})
  if set(per[0])!=set(per[1]) or {r['label'] for r in per[0].values()}!={r['label'] for r in per[1].values()}:raise ValueError('pair options mismatch')
  for nid in per[0]:
   node=nodes.get(nid);labels=sorted({x[nid]['label'] for x in per})
   if nid in used or len(labels)!=2 or not node or node.get('node_type')!='equipment' or node.get('identity_status')!='unresolved' or any(x not in labels for x in node.get('source_label_candidates',[])):raise ValueError('equipment candidate mismatch')
   used.add(nid);previous=copy.deepcopy(node.get('source_label_candidates',[]));node['source_label_candidate_history']={'candidates':previous,'status':'bounded_search_incomplete_superseded'};node['source_label_candidates']=labels
   node['source_label_pair_evidence']={'group_id':gid,'plan_source_sha256':source_hash,'input_graph_sha256':graph_hash,'axis_source_sha256':evidence['axis_source_sha256'],'axis_graph_sha256':evidence['axis_graph_sha256'],'alternatives':[{'label':x[nid]['label'],'plan_text_handle':x[nid]['plan_text_handle'],'axis_text_handle':x[nid]['axis_text_handle']} for x in per],'identity_confirmed':False}
 out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_label_candidate_expansion')
 out['preHilComparison']={'status':'pending','previous_comparison':copy.deepcopy(graph.get('preHilComparison')),'families':[{'id':'equipment-label-pairs','status':'algorithm_pending','disposition':'按源图逐组确认设备编号；相邻配对和轴测同名均不构成确认。'}]}
 return out

def main():
 p=argparse.ArgumentParser()
 for k in ('plan-source','axis-source','plan-graph','axis-graph','axis-receipt','devices','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));pd,pp=read_source(a.plan_source);ad,ap=read_source(a.axis_source);h={'plan_source_sha256':pp['source_sha256'],'axis_source_sha256':ap['source_sha256'],'plan_graph_sha256':sha(a.plan_graph),'axis_graph_sha256':sha(a.axis_graph),'axis_receipt_sha256':sha(a.axis_receipt)}
 g=load(a.plan_graph);e=screen(pd,ad,g,load(a.axis_graph),load(a.axis_receipt),load(a.policy),h);out=attach(g,e,h['plan_source_sha256'],h['plan_graph_sha256']);a.output.mkdir(parents=True,exist_ok=False);dest=a.output/'graph_with_equipment_pair_candidates.json';dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
 e.update(output_graph_sha256=sha(dest),policy_sha256=sha(a.policy),axis_receipt_sha256=sha(a.axis_receipt),screen_script_sha256=sha(Path(__file__).with_name('screen_equipment_label_pairs.py')),text_guard_sha256=sha(Path(__file__).with_name('native_dn_text_position.py')),script_sha256=sha(Path(__file__)));(a.output/'pair-candidate-audit.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':'equipment_candidates_expanded_unreviewed','groups':len(e['groups'])}))
if __name__=='__main__':main()
