"""Preserve unreviewed normalized-tee status in the canonical graph."""
import argparse,copy,hashlib,json,shutil
from pathlib import Path
from source_readability import read_source
from screen_applied_near_tees import screen

def attach(graph,evidence,source_hash,graph_hash):
 if graph.get('metadata',{}).get('source_sha256')!=source_hash or evidence.get('source_sha256')!=source_hash or evidence.get('graph_sha256')!=graph_hash or evidence.get('status')!='applied_near_tees_pending_review' or evidence.get('human_accepted') is not False or evidence.get('graph_mutated') is not False:raise ValueError('stale near-tee evidence')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};records=evidence.get('records')
 if len(nodes)!=len(out['nodes']) or not isinstance(records,list) or not records or len({x['node_id'] for x in records})!=len(records):raise ValueError('invalid near-tee records')
 for item in records:
  node=nodes.get(item['node_id']);incident=[e for e in out['edges'] if item['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))]
  if not node or node.get('node_type')!='tee' or node.get('resolution_state') is not None or item.get('status')!='source_normalized_tee_not_human_accepted' or sorted(e['edge_id'] for e in incident)!=item['incident_edge_ids'] or len(incident)!=3 or any(e.get('system')!=item['system'] for e in incident):raise ValueError('near-tee graph mismatch')
  node.update(resolution_state='source_contact_reconstructed_pending_comparison',review_required=True,source_near_tee_evidence={'source_sha256':source_hash,'input_graph_sha256':graph_hash,'branch_handle':item['branch_handle'],'main_handle':item['main_handle'],'incident_edge_ids':item['incident_edge_ids'],'normalization_distance':item['normalization_distance'],'human_accepted':False})
 out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_normalized_tee_state')
 out['preHilComparison']={'status':'pending','previous_comparison':copy.deepcopy(graph.get('preHilComparison')),'families':[{'id':'normalized-near-tee','status':'algorithm_pending','disposition':'对照原图逐点确认近接支路，禁止将候选连接当作已验收。'}]}
 return out

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','normalization','devices','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));doc,proof=read_source(a.source);source_hash=proof['source_sha256'];graph_hash=sha(a.graph);g=load(a.graph);policy=load(a.policy)
 evidence=screen(doc,g,load(a.normalization),policy,{'source_sha256':source_hash,'graph_sha256':graph_hash,'normalization_sha256':sha(a.normalization)});out=attach(g,evidence,source_hash,graph_hash)
 a.output.mkdir(parents=True,exist_ok=False);dest=a.output/'graph_with_pending_near_tees.json';dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
 evidence.update(policy_sha256=sha(a.policy),screen_script_sha256=sha(Path(__file__).with_name('screen_applied_near_tees.py')),attach_script_sha256=sha(Path(__file__)),output_graph_sha256=sha(dest),devices_sha256=sha(a.devices));(a.output/'near-tee-state-audit.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'status':'pending_near_tee_state_attached','nodes':len(evidence['records']),'hil_ready':False}))
if __name__=='__main__':main()
