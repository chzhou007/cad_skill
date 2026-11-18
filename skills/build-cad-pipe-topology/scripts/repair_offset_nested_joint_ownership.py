"""Repair explicitly scoped nested joint ownership from reproduced source contacts."""
import argparse,copy,csv,hashlib,json,math
from pathlib import Path
from native_offset_circle_candidates import collect as offset_collect
from native_nested_joint_evidence import collect as nested_collect
from native_line_path_evidence import _on
from repair_exploded_joint_ownership import _inventory
from source_readability import read_source

def repair(doc,graph,rows,policy,hashes):
 for k in ('source_sha256','graph_sha256','devices_sha256'):
  if policy.get(k)!=hashes.get(k):raise ValueError('input hash mismatch: '+k)
 selections=policy.get('corrections',[])
 if not selections or len({x['device_name'] for x in selections})!=len(selections) or len({x['to_edge'] for x in selections})!=len(selections):raise ValueError('invalid correction selection')
 _inventory(graph,rows);edges={e['edge_id']:e for e in graph['edges']};nodes={n['node_id']:n for n in graph['nodes']};inventory={r['device_name']:r for r in rows}
 offset_policy={'source_sha256':hashes['source_sha256'],'graph_sha256':hashes['graph_sha256'],'max_radius_ratio':policy['max_radius_ratio'],'edges':[x['to_edge'] for x in selections]}
 offset=offset_collect(doc,graph,offset_policy,hashes['source_sha256'],hashes['graph_sha256']);byedge={x['edge_id']:x for x in offset['edges']};root_to_edge={};circle={'status':'source_geometry_candidates_only','source_sha256':hashes['source_sha256'],'graph_sha256':hashes['graph_sha256'],'edges':[]}
 for selected in selections:
  result=byedge[selected['to_edge']];cs=result['candidates']
  if result['status']!='unique_offset_candidate' or len(cs)!=1:raise ValueError('offset candidate is not unique')
  c=cs[0];root=c['source_line_chain'][0]
  if root in root_to_edge:raise ValueError('source instance claimed twice')
  root_to_edge[root]=selected['to_edge'];circle['edges'].append({'edge_id':selected['to_edge'],'system':result['system'],'source_insert_handle':root,'candidates':[{'source_chain':c['source_line_chain'],'circles':[{'source_chain':c['source_circle_chain'],'z_coincident':True,'line_endpoint_index':c['endpoint_index']}]}]})
 temp=[]
 for row in rows:
  x=dict(row)
  if x.get('source_top_handle') in root_to_edge and x.get('equipment_type')=='金属软接' and x.get('source_block_name')==policy['joint_block']:x['edge_id']=root_to_edge[x['source_top_handle']]
  temp.append(x)
 proof_hashes={'source_sha256':hashes['source_sha256'],'graph_sha256':hashes['graph_sha256'],'inventory_sha256':'synthetic-probe-only','circle_sha256':'recomputed-offset-screen'}
 nested_policy=dict(proof_hashes,joint_block=policy['joint_block'],block_fingerprint_sha256=policy['block_fingerprint_sha256'],edges=[x['to_edge'] for x in selections]);nested=nested_collect(doc,graph,temp,circle,nested_policy,proof_hashes);witness={x['edge_id']:x for x in nested['edges']}
 g=copy.deepcopy(graph);records=copy.deepcopy(rows);gedges={e['edge_id']:e for e in g['edges']};rindex={r['device_name']:r for r in records};changes=[]
 for selection in selections:
  target=edges.get(selection['to_edge']);origin=edges.get(selection['from_edge']);row=inventory.get(selection['device_name']);w=witness.get(selection['to_edge'])
  if not row or not target or not origin or not w or w['status']!='unique_source_symbol_evidence' or len(w['matches'])!=1:raise ValueError('source joint witness not unique')
  m=w['matches'][0];owner=row.get('owner_equipment')
  if m['component_name']!=row['device_name'] or row.get('edge_id')!=origin['edge_id'] or row.get('source_top_handle')!=m['joint_chain'][0] or not owner or target.get('device_label')!=owner or origin.get('device_label')!=owner or owner not in nodes or nodes[owner].get('node_type') not in ('equipment','physical_equipment') or owner not in (target.get('start_node_id'),target.get('end_node_id')) or owner not in (origin.get('start_node_id'),origin.get('end_node_id')) or target.get('system')==origin.get('system'):raise ValueError('owner or system mismatch')
  root=doc.entitydb[m['outer_line_chain'][0]];outer=[x for x in root.virtual_entities() if x.dxftype()=='LINE' and getattr(x,'source_of_copy',None) is not None and x.source_of_copy.dxf.handle==m['outer_line_chain'][1]]
  if len(outer)!=1:raise ValueError('outer line instance mismatch')
  a=tuple(outer[0].dxf.start)[:2];b=tuple(outer[0].dxf.end)[:2];hits=[e['edge_id'] for e in graph['edges'] if e.get('system')==target.get('system') and any(_on(a,u,v,.05) and _on(b,u,v,.05) for path in e.get('attribute_paths',[]) for u,v in zip(path,path[1:]))]
  if hits!=[target['edge_id']]:raise ValueError('outer line graph witness is not unique')
  src=gedges[origin['edge_id']];dst=gedges[target['edge_id']];record=rindex[row['device_name']];item=next((i for i in src.get('equipment_inventory',[]) if i['equipment_type']==record['equipment_type']),None)
  if not item or record['device_name'] not in item['device_names']:raise ValueError('source component missing')
  item['device_names'].remove(record['device_name']);item['count']-=1
  if item['count']==0:src['equipment_inventory'].remove(item)
  item=next((i for i in dst.get('equipment_inventory',[]) if i['equipment_type']==record['equipment_type']),None)
  if item is None:item={'equipment_type':record['equipment_type'],'count':0,'device_names':[]};dst.setdefault('equipment_inventory',[]).append(item)
  item['device_names'].append(record['device_name']);item['count']+=1
  import pipe_geometry as pg
  pos=(float(record['assignment_x']),float(record['assignment_y']));dist=min(pg.segdist(pos,a,b) for path in dst['attribute_paths'] for a,b in zip(path,path[1:]));record.update(original_edge_id=origin['edge_id'],edge_id=target['edge_id'],edge_distance=str(dist),assignment_basis='source_nested_joint_offset_circle_contacts')
  changes.append({'device_name':record['device_name'],'owner_equipment':owner,'from_edge':origin['edge_id'],'to_edge':target['edge_id'],'offset_circle_evidence':byedge[target['edge_id']]['candidates'][0],'joint_evidence':m,'source_graphic_span_physical_length':'unknown'})
 _inventory(g,records);g['offsetNestedJointOwnershipRepair']={'source_sha256':hashes['source_sha256'],'input_graph_sha256':hashes['graph_sha256'],'changes':changes,'status':'source_evidence_repaired_unreviewed','hil_ready':False};g.setdefault('metadata',{}).update(hil_ready=False,review_status='unreviewed')
 return g,records,{'status':'source_evidence_repaired_unreviewed','changes':changes,'source_sha256':hashes['source_sha256'],'input_graph_sha256':hashes['graph_sha256'],'devices_sha256':hashes['devices_sha256'],'hil_ready':False}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','devices','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 with a.devices.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
 g,records,report=repair(doc,json.loads(a.graph.read_text(encoding='utf8')),rows,json.loads(a.policy.read_text(encoding='utf8')),{k:sha(getattr(a,{'source_sha256':'source','graph_sha256':'graph','devices_sha256':'devices'}[k])) for k in ('source_sha256','graph_sha256','devices_sha256')})
 a.output.mkdir(parents=True,exist_ok=False);target=a.output/'graph_with_edges.json';target.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8');fields=list(dict.fromkeys(fields+[k for row in records for k in row]))
 with (a.output/'edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
 with (a.output/'edge_equipment_by_type.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['edge_id','start_node_id','end_node_id','equipment_type','device_count','device_names']);w.writeheader()
  for edge in g['edges']:
   for item in edge.get('equipment_inventory',[]):w.writerow({'edge_id':edge['edge_id'],'start_node_id':edge['start_node_id'],'end_node_id':edge['end_node_id'],'equipment_type':item['equipment_type'],'device_count':item['count'],'device_names':';'.join(item['device_names'])})
 report.update(output_graph_sha256=sha(target),policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),source_preflight=proof);(a.output/'offset-joint-ownership-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'corrected':len(report['changes']),'hil_ready':False}))
if __name__=='__main__':main()
