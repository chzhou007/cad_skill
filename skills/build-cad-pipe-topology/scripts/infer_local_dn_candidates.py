"""Build source-scoped DN inheritance candidates, never authoritative values."""
import argparse,copy,hashlib,json,shutil
from pathlib import Path
from source_readability import read_source
from native_path_coverage_audit import audit as audit_paths
from native_junction_ray_evidence import collect as audit_junctions
from source_dn_annotation_risks import scan
from pipe_annotation_attributes import source_texts
from diameter_tee_inheritance import infer
from source_direct_dn_evidence import collect as collect_direct_dn
from nested_dn_screen import screen as screen_nested_dn

def calculate(graph,policy,coverage,junctions,risks,nested,source_hash,graph_hash):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('source or graph mismatch')
 for evidence in (coverage,junctions,risks,nested):
  if evidence.get('source_sha256')!=source_hash or evidence.get('graph_sha256')!=graph_hash:raise ValueError('stale source evidence')
 selected=policy.get('edges',[]);selected_t=policy.get('junctions',[]);seeds=policy.get('seeds',[])
 if not selected or len(selected)!=len(set(selected)) or not selected_t or len(selected_t)!=len(set(selected_t)) or not seeds:raise ValueError('invalid scoped selections')
 covered={x['edge_id']:x for x in coverage.get('edges',[])}
 if set(covered)!=set(selected) or any(not e.get('segments') or any(s['status']!='single_source_line_covers' for s in e['segments']) for e in covered.values()):raise ValueError('source path coverage incomplete')
 rays={x['node_id']:x for x in junctions.get('junctions',[])}
 if set(rays)!=set(selected_t):raise ValueError('source junction evidence incomplete')
 if {x.get('node_id') for x in policy.get('junction_witnesses',[])}!=set(selected_t):raise ValueError('junction policy mismatch')
 edges={e['edge_id']:e for e in graph['edges']};seed_data=[];seen=set();seeds_by_id={}
 for node in selected_t:
  incident={e['edge_id'] for e in graph['edges'] if node in (e.get('start_node_id'),e.get('end_node_id'))}
  if not incident<=set(selected):raise ValueError('all junction incident edges need source coverage')
 for seed in seeds:
  eid=seed['edge_id'];h=seed['text_handle'];v=seed['nominal_mm'];e=edges.get(eid);obs=(e or {}).get('pipe_diameter',{}).get('observations',[])
  matches=[o for o in obs if o.get('text',{}).get('handle')==h and o.get('nominal_mm')==v and o.get('status')=='native_source_local_observation']
  if eid in seen or not e or e.get('diameter_nominal_mm') is not None or len(matches)!=1:raise ValueError('unbound or nonlocal seed')
  seen.add(eid);key='source:'+h;seed_data.append({'edge_id':eid,'nominal_mm':v,'evidence_id':key});seeds_by_id[key]=matches[0]
 if len({float(x['nominal_mm']) for x in seed_data})!=1:raise ValueError('mixed values require separate scoped conflict analysis')
 value=float(seed_data[0]['nominal_mm'])
 if set(nested.get('selected_edges',[]))!=set(selected) or any(nested.get(k) for k in ('missing_blocks','xref_blocks','proxy_entities_in_blocks','proxy_entities_modelspace','array_inserts','cyclic_block_names')):raise ValueError('nested annotation coverage has unsupported source entities')
 for row in nested.get('nearby_nested_dn',[]):
  parsed=row.get('parsed_single_dn')
  if not parsed or parsed.get('nominal_mm')!=value:raise ValueError('nearby nested DN conflict requires reconciliation')
 for row in risks.get('observations',[]):
  if not set(row.get('geometric_candidate_edge_ids',[])).intersection(selected):continue
  parsed=row.get('parsed_single_dn')
  if row.get('syntax')!='single_dn' or not parsed or parsed.get('nominal_mm')!=value:raise ValueError('nearby unparsed or different diameter needs reconciliation')
 result=infer(graph,seed_data,selected,selected_t)
 if any(x['status'] in ('unknown','conflict') for x in result):raise ValueError('selected candidate network is not uniquely seeded')
 out=copy.deepcopy(graph);out_edges={e['edge_id']:e for e in out['edges']};changes=[]
 for row in result:
  e=out_edges[row['edge_id']];candidates=row['candidates'];lineage=[]
  for c in candidates:
   for ev in c['evidence']:
    obs=seeds_by_id[ev['evidence_id']];lineage.append({'source_text_handle':obs['text']['handle'],'source_text':obs['text']['text'],'edge_path':ev['edge_path']})
  item={'status':'source_scoped_inheritance_candidate_not_accepted','nominal_mm_candidate':row['nominal_mm'],'candidate_type':row['status'],'source_graph_sha256':graph_hash,'source_sha256':source_hash,'lineage':lineage,'scope':'modelspace source lines and modelspace/nested text screening; edgewide DN and opaque proxies not established'}
  if e.get('diameter_nominal_mm') is not None or e.get('diameter_inference'):raise ValueError('existing diameter must be reconciled')
  e['diameter_inference']=item
  e['diameter_candidate_mm']=row['nominal_mm'];e['diameter_candidate_status']=item['status'];e['diameter_candidate_lineage']='; '.join(x['source_text_handle']+': '+' -> '.join(x['edge_path']) for x in lineage)
  if row['status']=='inherited_candidate':
   if e.get('pipe_diameter') or e.get('diameter_status') not in (None,'','unannotated'):raise ValueError('existing diameter annotation must be reconciled')
   e['pipe_diameter']={'status':item['status'],'nominal_mm':None,'display':f"DN{row['nominal_mm']:g}（T继承候选；待核）",'observations':[]};e['diameter_nominal_mm']=None;e['diameter_text']='';e['diameter_status']=item['status']
  changes.append({'edge_id':row['edge_id'],'candidate_type':row['status'],'nominal_mm_candidate':row['nominal_mm'],'lineage':lineage})
 out['preHilComparison']={'status':'pending','previous_comparison':copy.deepcopy(graph.get('preHilComparison')),'reason':'DN inference candidates added; graph-bound comparisons and reviews require reevaluation'}
 out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_attribute_change')
 out['diameterInheritanceCandidates']={'source_sha256':source_hash,'input_graph_sha256':graph_hash,'changes':changes,'status':'candidate_not_accepted','edgewide_values_assigned':False}
 return out,{'changes':changes,'edgewide_values_assigned':False,'hil_ready':False}

def collect_evidence(doc,graph,policy,source_hash,graph_hash,source_id):
 base={'source_sha256':source_hash,'graph_sha256':graph_hash};paths=audit_paths(doc,graph,base|{'edges':policy['edges']},source_hash,graph_hash);rays=audit_junctions(doc,graph,base|{'junctions':policy['junction_witnesses']},source_hash,graph_hash)
 risks=scan(source_texts(doc,source_id,source_hash),graph['edges'],set(policy['text_layers']));risks.update(base);nested=screen_nested_dn(doc,graph,base|{'edges':policy['edges'],'nested_search_radius':policy['nested_search_radius']},source_hash,graph_hash);return paths,rays,risks,nested

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','devices','policy','direct-dn-policy','output'):p.add_argument('--'+k,required=True,type=Path)
 a=p.parse_args()
 if a.output.exists():raise ValueError('refusing to overwrite output')
 doc,proof=read_source(a.source);gb=a.graph.read_bytes();pb=a.policy.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();graph=json.loads(gb);policy=json.loads(pb);h=sha(gb)
 if policy.get('source_sha256')!=proof['source_sha256'] or policy.get('graph_sha256')!=h:raise ValueError('stale policy')
 direct_bytes=a.direct_dn_policy.read_bytes();direct_policy=json.loads(direct_bytes)
 direct=collect_direct_dn(doc,graph,direct_policy,proof['source_sha256'],h)
 direct_pairs={(x['edge_id'],x['source_text']['handle'],x['nominal_mm']) for x in direct['observations']}
 if not {(x['edge_id'],x['text_handle'],x['nominal_mm']) for x in policy['seeds']}<=direct_pairs:raise ValueError('seed missing from fresh native direct DN evidence')
 paths,rays,risks,nested=collect_evidence(doc,graph,policy,proof['source_sha256'],h,a.source.stem);out,audit=calculate(graph,policy,paths,rays,risks,nested,proof['source_sha256'],h);a.output.mkdir(parents=True);dest=a.output/'graph_with_dn_inheritance_candidates.json';dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
 final_hash=sha(dest.read_bytes());final_paths,final_rays,final_risks,final_nested=collect_evidence(doc,out,policy,proof['source_sha256'],final_hash,a.source.stem)
 final_direct_policy=copy.deepcopy(direct_policy);final_direct_policy['prior_graph_sha256']=h;final_direct_policy['graph_sha256']=final_hash;final_direct_policy['rechecked_from_policy_sha256']=sha(direct_bytes)
 final_direct=collect_direct_dn(doc,out,final_direct_policy,proof['source_sha256'],final_hash);final_direct.update(source_preflight=proof,prior_policy_sha256=sha(direct_bytes))
 (a.output/'direct_dn_recheck_policy.json').write_text(json.dumps(final_direct_policy,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 (a.output/'source-direct-dn-candidates.json').write_text(json.dumps(final_direct,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 final_risks['text_layers']=policy['text_layers']
 for name,data in [('source-path-evidence.json',final_paths),('source-junction-evidence.json',final_rays),('source-dn-risk-evidence.json',final_risks),('source-nested-dn-evidence.json',final_nested)]:
  (a.output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 audit.update(source_sha256=proof['source_sha256'],input_graph_sha256=h,output_graph_sha256=final_hash,policy_sha256=sha(pb),component_table_sha256=sha(a.devices.read_bytes()),source_preflight=proof)
 (a.output/'dn-inheritance-candidates-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'candidates':len(audit['changes']),'output_graph_sha256':final_hash,'hil_ready':False}))
if __name__=='__main__':main()
