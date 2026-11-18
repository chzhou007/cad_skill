"""Attach explicitly selected native DN observations without edge-wide claims."""
import argparse,copy,hashlib,json,shutil,subprocess,sys
from pathlib import Path
from source_readability import read_source
from source_direct_dn_evidence import collect

def attach(graph,evidence,source_hash,graph_hash):
 if graph.get('metadata',{}).get('source_sha256')!=source_hash or evidence.get('source_sha256')!=source_hash or evidence.get('graph_sha256')!=graph_hash or evidence.get('status')!='candidate_not_accepted':raise ValueError('source evidence identity or state mismatch')
 rows=evidence.get('observations');out=copy.deepcopy(graph);edges={e['edge_id']:e for e in out['edges']}
 if len(edges)!=len(out['edges']) or not isinstance(rows,list) or not rows or len({r['edge_id'] for r in rows})!=len(rows):raise ValueError('invalid observations')
 changes=[]
 for r in rows:
  e=edges.get(r['edge_id']);t=r.get('source_text',{});value=r.get('nominal_mm')
  if not e or e.get('system')!=r.get('system') or r.get('status')!='candidate_source_annotation' or r.get('source_line_handle') not in e.get('source_handles',[]) or not isinstance(value,(int,float)) or isinstance(value,bool) or not 0<value<10000:raise ValueError('source observation mismatch')
  if e.get('pipe_diameter') or e.get('diameter_nominal_mm') is not None or e.get('diameter_status') not in (None,'','unannotated'):raise ValueError('existing diameter needs reconciliation')
  if t.get('source_sha256')!=source_hash or not t.get('handle') or not t.get('text') or not r.get('graph_projection'):raise ValueError('incomplete source observation')
  obs={'text':copy.deepcopy(t),'nominal_mm':value,'point':r['graph_projection'],'source_line_handle':r['source_line_handle'],'status':'native_source_local_observation','parenthesized_source_value':r.get('parenthesized_source_value')}
  e['pipe_diameter']={'status':'local_source_observation_edgewide_unverified','nominal_mm':None,'display':f'DN{value:g}（标注处；整边待核）','observations':[obs]}
  e['diameter_nominal_mm']=None;e['diameter_text']=t['text'];e['diameter_status']='local_source_observation_edgewide_unverified'
  changes.append({'edge_id':e['edge_id'],'text_handle':t['handle'],'source_line_handle':r['source_line_handle'],'observed_nominal_mm':value,'point':r['graph_projection']})
 out['preHilComparison']={'status':'pending','previous_comparison':copy.deepcopy(graph.get('preHilComparison')),'reason':'DN source observation added; graph-bound comparisons and reviews require reevaluation'}
 out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_attribute_change')
 out['localDiameterObservations']={'source_sha256':source_hash,'input_graph_sha256':graph_hash,'observations':changes,'edgewide_assignment':False,'inheritance_applied':False,'human_review':'unreviewed'}
 return out,{'observations':changes,'edgewide_assignment':False,'inheritance_applied':False,'hil_ready':False}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','devices','policy','output'):p.add_argument('--'+k,required=True,type=Path)
 a=p.parse_args()
 if a.output.exists():raise ValueError('refusing to overwrite output')
 doc,proof=read_source(a.source);gb=a.graph.read_bytes();pb=a.policy.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();graph=json.loads(gb);policy=json.loads(pb)
 evidence=collect(doc,graph,policy,proof['source_sha256'],sha(gb));out,audit=attach(graph,evidence,proof['source_sha256'],sha(gb));a.output.mkdir(parents=True)
 dest=a.output/'graph_with_local_dn_observations.json';dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
 # Recompute all selected candidates and mixed syntax risks for the resulting graph.
 dp=copy.deepcopy(policy);dp['graph_sha256']=sha(dest.read_bytes());dp['prior_graph_sha256']=sha(gb);dp['rechecked_from_policy_sha256']=sha(pb)
 newp=a.output/'direct_dn_recheck_policy.json';newp.write_text(json.dumps(dp,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 dn=a.output/'source-direct-dn-candidates.json';risk=a.output/'source-dn-annotation-risks.json'
 subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).with_name('source_direct_dn_evidence.py')),'--source',str(a.source),'--graph',str(dest),'--policy',str(newp),'--output',str(dn)],check=True)
 cmd=[sys.executable,'-X','utf8',str(Path(__file__).with_name('source_dn_annotation_risks.py')),'--source',str(a.source),'--graph',str(dest),'--output',str(risk)]
 for layer in dp['text_layers']:cmd.extend(['--text-layer',layer])
 subprocess.run(cmd,check=True)
 audit.update(source_sha256=proof['source_sha256'],input_graph_sha256=sha(gb),output_graph_sha256=sha(dest.read_bytes()),policy_sha256=sha(pb),recheck_policy_sha256=sha(newp.read_bytes()),dn_evidence_sha256=sha(dn.read_bytes()),risk_sha256=sha(risk.read_bytes()),component_table_sha256=sha(a.devices.read_bytes()),source_preflight=proof)
 (a.output/'local-dn-observation-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'observations':len(audit['observations']),'graph_sha256':audit['output_graph_sha256'],'hil_ready':False}))
if __name__=='__main__':main()
