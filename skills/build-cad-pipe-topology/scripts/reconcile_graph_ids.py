"""Keep established task-local IDs when source positions and endpoints survive."""
import argparse,json,csv,math
from pathlib import Path

def reconcile(previous,directory):
 old=json.loads(Path(previous).read_text(encoding='utf8'));directory=Path(directory);g=json.loads((directory/'graph_with_edges.json').read_text(encoding='utf8'));nm={};used=set();max_t=max([int(n['node_id'][1:])for n in old['nodes']if n['node_id'].startswith('T')]+[0])
 for n in g['nodes']:
  hits=[p for p in old['nodes']if p['node_type']==n['node_type']and p.get('system')==n.get('system')and math.dist((n['x'],n['y']),(p['x'],p['y']))<=.05]
  if len(hits)==1:target=hits[0]['node_id']
  elif n['node_type']=='tee':max_t+=1;target='T'+str(max_t).zfill(4 if len(n['node_id'])>4 else 3)
  else:target=n['node_id']
  if target in used:raise ValueError('Ambiguous source node ID match: '+target)
  nm[n['node_id']]=target;used.add(target)
 em={};used=set();max_e=max([int(e['edge_id'][1:])for e in old['edges']]+[0])
 for e in g['edges']:
  ends={nm[e['start_node_id']],nm[e['end_node_id']]};hits=[p for p in old['edges']if p['system']==e['system']and {p['start_node_id'],p['end_node_id']}==ends]
  if len(hits)!=1:
   def shape(edge):return tuple(tuple(round(x,2)for x in p)for p in edge.get('path_points',edge.get('path',[])))
   key=shape(e);hits=[p for p in old['edges']if p['system']==e['system']and shape(p)in [key,tuple(reversed(key))]]
  if len(hits)==1 and hits[0]['edge_id']not in used:target=hits[0]['edge_id']
  else:max_e+=1;target=f'E{max_e:04d}'
  em[e['edge_id']]=target;used.add(target)
 nodekeys={'node_id','start_node_id','end_node_id','virtual_equipment_id','equipment_id'};edgekeys={'edge_id','related_edge_ids','candidate_edge_ids'}
 def field(k,v):
  mapping=nm if k in nodekeys else em if k in edgekeys else None
  if mapping is None:return walk(v)
  if isinstance(v,list):return[mapping.get(x,x)for x in v]
  if isinstance(v,str)and v.startswith('['):return json.dumps([mapping.get(x,x)for x in json.loads(v)],ensure_ascii=False)
  return mapping.get(v,v)
 def walk(v):
  if isinstance(v,dict):return{k:field(k,x)for k,x in v.items()}
  if isinstance(v,list):return[walk(x)for x in v]
  return v
 for p in directory.rglob('*.json'):
  if p.name=='id_mapping.json':continue
  p.write_text(json.dumps(walk(json.loads(p.read_text(encoding='utf8'))),ensure_ascii=False,indent=2),encoding='utf8')
 for p in directory.rglob('*.csv'):
  with p.open(encoding='utf-8-sig',newline='')as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
  if not fields:continue
  with p.open('w',encoding='utf-8-sig',newline='')as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows({k:field(k,v)for k,v in r.items()}for r in rows)
 new=json.loads((directory/'graph_with_edges.json').read_text(encoding='utf8'));report={'node_remapping':nm,'edge_remapping':em,'retired_nodes':[n['node_id']for n in old['nodes']if n['node_id']not in {n['node_id']for n in new['nodes']}],'retired_edges':[e['edge_id']for e in old['edges']if e['edge_id']not in {e['edge_id']for e in new['edges']}]};(directory/'id_mapping.json').write_text(json.dumps(report,indent=2),encoding='utf8');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--previous',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);a=p.parse_args();reconcile(a.previous,a.directory)
