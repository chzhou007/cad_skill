"""Correct explicitly selected modelspace joint ownership from native contacts."""
import argparse,copy,csv,hashlib,json,math
from collections import Counter,defaultdict
from pathlib import Path
from native_line_path_evidence import LAYERS,_on
from native_nested_joint_evidence import fingerprint
from source_readability import read_source


def _inventory(graph,rows):
 expected=Counter((e['edge_id'],item['equipment_type'],name) for e in graph['edges'] for item in e.get('equipment_inventory',[]) for name in item.get('device_names',[]))
 if any(item.get('count')!=len(item.get('device_names',[])) for e in graph['edges'] for item in e.get('equipment_inventory',[])):raise ValueError('invalid graph inventory')
 actual=Counter((r['edge_id'],r['equipment_type'],r['device_name']) for r in rows if r.get('assignment_status')=='assigned')
 if expected!=actual or any(n!=1 for n in actual.values()) or len({r['device_name'] for r in rows})!=len(rows):raise ValueError('component inventory mismatch')


def repair(doc,graph,rows,policy,hashes,tol=.05):
 for k in ('source_sha256','graph_sha256','devices_sha256'):
  if policy.get(k)!=hashes.get(k):raise ValueError('input hash mismatch: '+k)
 if not 0<tol<=.05:raise ValueError('invalid tolerance')
 block=policy['joint_block'];definition=doc.blocks.get(block)
 if definition is None or fingerprint(definition)!=policy['block_fingerprint_sha256'] or sorted(e.dxftype() for e in definition)!=['ARC']*4+['LINE']*2:raise ValueError('joint definition mismatch')
 _inventory(graph,rows);g=copy.deepcopy(graph);records=copy.deepcopy(rows);edges={e['edge_id']:e for e in g['edges']};nodes={n['node_id']:n for n in g['nodes']}
 if len(edges)!=len(g['edges']) or len(nodes)!=len(g['nodes']):raise ValueError('duplicate graph ids')
 source_layers={v:k for k,v in LAYERS.items()};index=defaultdict(list)
 for line in doc.modelspace().query('LINE'):
  if line.dxf.layer not in source_layers:continue
  for p in (line.dxf.start,line.dxf.end):index[(round(p.x),round(p.y))].append(line)
 results=[]
 for row in records:
  if row['equipment_type']!='金属软接' or row.get('source_block_name')!=block:continue
  entity=doc.entitydb.get(row.get('source_top_handle'))
  if not entity or entity.dxftype()!='INSERT' or entity not in doc.modelspace() or entity.dxf.name!=block:continue
  parts=list(entity.virtual_entities());bars=[e for e in parts if e.dxftype()=='LINE']
  if len(parts)!=6 or len(bars)!=2 or sum(e.dxftype()=='ARC' for e in parts)!=4:raise ValueError('unsupported joint transform')
  contacts=[]
  for bar in bars:
   p=(bar.dxf.start+bar.dxf.end)/2;found={}
   for dx in (-1,0,1):
    for dy in (-1,0,1):
     for line in index.get((round(p.x)+dx,round(p.y)+dy),[]):
      if min(math.dist(tuple(p),tuple(line.dxf.start)),math.dist(tuple(p),tuple(line.dxf.end)))>tol:continue
      a=(line.dxf.start.x,line.dxf.start.y);b=(line.dxf.end.x,line.dxf.end.y);system=source_layers[line.dxf.layer]
      witnesses=sorted(e['edge_id'] for e in g['edges'] if e.get('system')==system and any(_on(a,u,v,tol) and _on(b,u,v,tol) for path in e.get('attribute_paths',[]) for u,v in zip(path,path[1:])))
      found[line.dxf.handle]={'source_handle':line.dxf.handle,'system':system,'line_start':list(line.dxf.start),'line_end':list(line.dxf.end),'graph_edges':witnesses}
   contacts.append({'midpoint':list(p),'lines':sorted(found.values(),key=lambda x:x['source_handle'])})
  all_lines=[c['lines'][0] for c in contacts if len(c['lines'])==1];systems={x['system'] for x in all_lines};candidates=sorted({eid for x in all_lines for eid in x['graph_edges']})
  status='ambiguous_native_contacts'
  if len(all_lines)==2 and len(systems)>1:status='source_system_conflict'
  elif len(all_lines)==2 and len(systems)==1 and len(candidates)==1:status='unique_same_system_contact'
  results.append({'device_name':row['device_name'],'joint_handle':entity.dxf.handle,'assigned_edge_id':row['edge_id'],'contacts':contacts,'witness_edge_ids':candidates,'status':status})
 by_handle={r['joint_handle']:r for r in results};selected=policy.get('corrections')
 if len(by_handle)!=len(results) or not isinstance(selected,list) or not selected or len({x['joint_handle'] for x in selected})!=len(selected):raise ValueError('invalid selected joints')
 changes=[]
 for selection in selected:
  r=by_handle.get(selection['joint_handle']);row=next((x for x in records if x['device_name']==selection.get('device_name')),None)
  if not r or not row or r['status']!='unique_same_system_contact' or r['device_name']!=row['device_name'] or r['assigned_edge_id']!=selection.get('from_edge') or r['witness_edge_ids']!=[selection.get('to_edge')]:raise ValueError('selected correction not uniquely witnessed')
  src=edges.get(selection['from_edge']);dst=edges.get(selection['to_edge']);owner=row.get('owner_equipment')
  if not src or not dst or src is dst or not owner or src.get('device_label')!=owner or dst.get('device_label')!=owner or owner not in nodes or nodes[owner].get('node_type') not in ('equipment','physical_equipment') or owner not in (src.get('start_node_id'),src.get('end_node_id')) or owner not in (dst.get('start_node_id'),dst.get('end_node_id')):raise ValueError('equipment owner mismatch')
  if dst.get('system')!=r['contacts'][0]['lines'][0]['system']:raise ValueError('target system mismatch')
  item=next((i for i in src['equipment_inventory'] if i['equipment_type']==row['equipment_type']),None)
  if not item or row['device_name'] not in item['device_names']:raise ValueError('source component missing')
  item['device_names'].remove(row['device_name']);item['count']-=1
  if not item['count']:src['equipment_inventory'].remove(item)
  item=next((i for i in dst['equipment_inventory'] if i['equipment_type']==row['equipment_type']),None)
  if item is None:item={'equipment_type':row['equipment_type'],'count':0,'device_names':[]};dst['equipment_inventory'].append(item)
  item['device_names'].append(row['device_name']);item['count']+=1
  import pipe_geometry as pg
  point=(float(row['assignment_x']),float(row['assignment_y']));distance=min(pg.segdist(point,a,b) for path in dst['attribute_paths'] for a,b in zip(path,path[1:]))
  row.update(original_edge_id=selection['from_edge'],edge_id=selection['to_edge'],edge_distance=str(distance),assignment_basis='native_same_system_joint_contacts')
  changes.append({'device_name':row['device_name'],'joint_handle':r['joint_handle'],'from_edge':selection['from_edge'],'to_edge':selection['to_edge'],'contacts':r['contacts'],'source_graphic_span_physical_length':'unknown'})
 _inventory(g,records)
 conflicts=[r for r in results if r['status']=='source_system_conflict']
 g['sourceInlineSystemConflicts']=conflicts;g['sourceInlineOwnershipRepair']={'source_sha256':hashes['source_sha256'],'input_graph_sha256':hashes['graph_sha256'],'changes':changes,'review':'unreviewed'}
 g.setdefault('metadata',{}).update(hil_ready=False,review_status='unreviewed')
 return g,records,{'status':'native_joint_ownership_repaired_unreviewed','source_sha256':hashes['source_sha256'],'input_graph_sha256':hashes['graph_sha256'],'devices_sha256':hashes['devices_sha256'],'joint_results':results,'changes':changes,'unresolved_system_conflicts':conflicts,'hil_ready':False}


def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','devices','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);gb=a.graph.read_bytes();db=a.devices.read_bytes();pb=a.policy.read_bytes();sha=lambda x:hashlib.sha256(x).hexdigest()
 with a.devices.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
 g,records,audit=repair(doc,json.loads(gb),rows,json.loads(pb),{'source_sha256':proof['source_sha256'],'graph_sha256':sha(gb),'devices_sha256':sha(db)})
 a.output.mkdir(parents=True,exist_ok=False);target=a.output/'graph_with_edges.json';target.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8');fields=list(dict.fromkeys(fields+[k for row in records for k in row]))
 with (a.output/'edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
 with (a.output/'edge_equipment_by_type.csv').open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=['edge_id','start_node_id','end_node_id','equipment_type','device_count','device_names']);writer.writeheader()
  for edge in g['edges']:
   for item in edge.get('equipment_inventory',[]):writer.writerow({'edge_id':edge['edge_id'],'start_node_id':edge['start_node_id'],'end_node_id':edge['end_node_id'],'equipment_type':item['equipment_type'],'device_count':item['count'],'device_names':';'.join(item['device_names'])})
 audit.update(output_graph_sha256=sha(target.read_bytes()),policy_sha256=sha(pb),script_sha256=sha(Path(__file__).read_bytes()),source_preflight=proof)
 (a.output/'joint-ownership-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'corrected':len(audit['changes']),'system_conflicts':len(audit['unresolved_system_conflicts']),'graph_sha256':audit['output_graph_sha256']}))
if __name__=='__main__':main()
