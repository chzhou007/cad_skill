"""Compare initial assigned components, explicit flex repairs and final graph."""
import argparse,collections,csv,hashlib,json
from pathlib import Path
from source_readability import read_source

def evaluate(doc,graph,initial,final,repair,policy,source_hash,graph_hash,initial_hash,repair_hash):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or policy.get('initial_csv_sha256')!=initial_hash or policy.get('repair_audit_sha256')!=repair_hash or repair.get('source_sha256')!=source_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('stale source, graph or repair evidence')
 def indexed(rows):
  result={}
  for row in rows:
   name=row.get('device_name')
   if not name or name in result:raise ValueError('missing or duplicate component name')
   result[name]=row
  return result
 before=indexed(initial);after=indexed(final);removed=sorted(before.keys()-after.keys());added=sorted(after.keys()-before.keys())
 if removed:raise ValueError('initial assigned component lost: '+','.join(removed))
 fields=('equipment_type','type_code','source_kind','source_block_name','source_handle')
 for name,row in before.items():
  if any(row.get(k)!=after[name].get(k) for k in fields):raise ValueError('initial component identity changed: '+name)
 steps=repair.get('steps',[]);expected={x.get('source_handle'):x for x in steps}
 if not steps or None in expected or len(expected)!=len(steps):raise ValueError('invalid or duplicate repair handles')
 new_rows=[after[name] for name in added];actual={x.get('source_handle'):x for x in new_rows}
 if len(actual)!=len(new_rows) or set(actual)!=set(expected):raise ValueError('unexpected additions or missing flex repairs')
 edges={e['edge_id']:e for e in graph['edges']}
 if len(edges)!=len(graph['edges']):raise ValueError('duplicate graph edge ID')
 by_edge=collections.defaultdict(list)
 for row in final:
  if row.get('edge_id') not in edges:raise ValueError('component references missing edge')
  by_edge[row['edge_id']].append(row)
 for eid,e in edges.items():
  rows=by_edge[eid];counts=dict(collections.Counter(x['equipment_type'] for x in rows));names=sorted(x['device_name'] for x in rows)
  if e.get('equipment_counts',{})!=counts or sorted(e.get('equipment_names',[]))!=names:raise ValueError('edge aggregation differs from final instance table: '+eid)
 flex=[]
 for handle,step in expected.items():
  row=actual[handle];ent=doc.entitydb.get(handle);edge=edges[row['edge_id']]
  if row.get('equipment_type')!='flexible_joint' or row.get('type_code')!='FLEX' or row.get('source_kind')!='block_reference' or not ent or ent.dxftype()!='INSERT' or ent not in doc.modelspace() or row.get('source_block_name')!=ent.dxf.name or edge.get('system')!=step.get('system'):raise ValueError('flex source or system mismatch: '+handle)
  witnesses=[(e['edge_id'],w) for e in graph['edges'] for w in e.get('source_flexible_joints',[]) if w.get('source_handle')==handle]
  if len(witnesses)!=1 or witnesses[0][0]!=row['edge_id'] or witnesses[0][1].get('source_block')!=ent.dxf.name or witnesses[0][1].get('parameter_status')!='unknown_not_zero' or witnesses[0][1].get('physical_length')!='unknown':raise ValueError('flex witness or unknown parameters missing: '+handle)
  flex.append({'source_handle':handle,'device_name':row['device_name'],'final_edge':row['edge_id'],'system':step['system']})
 return {'status':'initial_assigned_and_scoped_flex_conserved_not_source_completeness','source_sha256':source_hash,'graph_sha256':graph_hash,'initial_csv_sha256':initial_hash,'repair_audit_sha256':repair_hash,'counts':{'initial_assigned':len(before),'final_assigned':len(after),'initial_missing':len(removed),'flex_additions':len(added)},'flex_additions':sorted(flex,key=lambda x:x['source_handle']),'edge_aggregations_match':True,'human_accepted':False,'hil_ready':False,'limitations':['Checks only initially assigned components and the explicitly scoped flex repair audit; unassigned, unrecognized, or other source components are not proven complete.','Preservation and source identity do not prove hydraulic ownership or physical parameters.']}

def main():
 p=argparse.ArgumentParser()
 for n in ('source','graph','initial','final','repair','policy','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source)
 def rows(p):
  with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
 r=evaluate(doc,json.loads(a.graph.read_text(encoding='utf8')),rows(a.initial),rows(a.final),json.loads(a.repair.read_text(encoding='utf8')),json.loads(a.policy.read_text(encoding='utf8')),proof['source_sha256'],sha(a.graph),sha(a.initial),sha(a.repair));r.update(final_csv_sha256=sha(a.final),policy_sha256=sha(a.policy),source_preflight=proof['status'])
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'counts':r['counts']}))
if __name__=='__main__':main()
