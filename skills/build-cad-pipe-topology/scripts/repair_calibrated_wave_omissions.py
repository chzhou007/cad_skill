"""Rebuild explicitly scoped, source-calibrated paired wave omissions.

Keeps the expert control and raw pipe paths; does not claim human acceptance or
physical length. Rejects unknown edge attributes instead of discarding them.
"""
import argparse,copy,csv,hashlib,json,math
from collections import Counter
from pathlib import Path
from source_readability import read_source
from wave_omission_candidates import screen
from reconcile_pending_main_continuity import validate_references

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def repair(graph, devices, doc, policy):
 g=copy.deepcopy(graph);ds=copy.deepcopy(devices)
 if g.get('calibratedWaveOmissionRepair'):raise ValueError('wave repair already applied')
 control=g.get('expertWaveOmissionRepair',{})
 if control.get('issue')!=policy['control_issue'] or control.get('source_sha256')!=policy['source_sha256']:
  raise ValueError('missing original expert control')
 controls={h for s in control.get('steps',[]) for h in s.get('source_wave_handles',[])}
 if set(policy['control_wave_handles'])!=controls:raise ValueError('expert control handles mismatch')
 for h in controls:
  ins=doc.entitydb.get(h)
  if ins is None or ins.dxftype()!='INSERT' or ins.dxf.name!=policy['block_name']:raise ValueError('control source mismatch')
 result=screen(doc,g,block_name=policy['block_name'],expected_fingerprint=policy['block_fingerprint'],max_gap=policy['max_gap'],contact_tolerance=policy['contact_tolerance'])
 rows={n['node_id']:n for n in result['wave_endpoints']}; found={frozenset((p['a'],p['b'])):p for p in result['candidate_pairs'] if p['unique_for_each_endpoint']}
 selected=policy['pairs'];keys=[frozenset(p['nodes']) for p in selected]
 if len(keys)!=len(set(keys)) or any(len(k)!=2 or k not in found for k in keys):raise ValueError('candidate missing or ambiguous')
 used=[n for pair in selected for n in pair['nodes']]
 if len(used)!=len(set(used)):raise ValueError('endpoint reused')
 nodes={n['node_id']:n for n in g['nodes']};edges={e['edge_id']:e for e in g['edges']};mapping={};steps=[]
 allowed={'edge_id','start_node_id','end_node_id','edge_type','system','start_floor','end_floor','path','attribute_paths','path_length','source_handles','equipment_counts','equipment_names','path_points','endpoint_semantics','start_port_id','end_port_id'}
 for spec in selected:
  u,v=(nodes[n] for n in spec['nodes']);r,s=(rows[n] for n in spec['nodes']);eu,ev=(edges[x['edge_id']] for x in (r,s))
  if set(spec['wave_handles'])!={r['wave_handle'],s['wave_handle']}:raise ValueError('source wave identity mismatch')
  for node,row,edge in ((u,r,eu),(v,s,ev)):
   if set(edge)-allowed:raise ValueError('unhandled edge attributes: '+str(sorted(set(edge)-allowed)))
   expected=policy['source_layer_by_system'][row['system']];matches=[]
   for h in node.get('source_handles',[]):
    ent=doc.entitydb.get(h)
    if ent is not None and ent.dxftype()=='LINE' and ent.dxf.layer==expected and h in edge.get('source_handles',[]):
     if min(math.dist((pt.x,pt.y),(node['x'],node['y'])) for pt in (ent.dxf.start,ent.dxf.end))<=policy['contact_tolerance']:matches.append(h)
   if len(matches)!=1:raise ValueError('source pipe contact missing or ambiguous')
  if eu['edge_id']==ev['edge_id']:raise ValueError('cycle or duplicate edge')
  def outer(edge,n):return edge['end_node_id'] if edge['start_node_id']==n['node_id'] else edge['start_node_id']
  a,b=outer(eu,u),outer(ev,v)
  if a==b or a not in nodes or b not in nodes:raise ValueError('invalid outer endpoints')
  # The first edge retains its ID; explicit historical mapping follows the other.
  def path_from(e,start):
   path=e.get('path_points') or e['path'];return copy.deepcopy(path if e['start_node_id']==start else list(reversed(path)))
  merged=copy.deepcopy(eu);combined=path_from(eu,a)+path_from(ev,v['node_id'])
  merged.update(start_node_id=a,end_node_id=b,path=combined,path_points=combined,
                attribute_paths=copy.deepcopy(eu['attribute_paths']+ev['attribute_paths']),
                path_length=eu['path_length']+ev['path_length'],path_length_complete=False,
                path_length_scope='source_drawn_pipe_only_wave_omission_length_unknown',
                source_handles=sorted(set(eu['source_handles']+ev['source_handles'])),
                connection_mode='source_calibrated_wave_omission_unreviewed')
  merged['equipment_names']=eu.get('equipment_names',[])+ev.get('equipment_names',[])
  counts=Counter(eu.get('equipment_counts',{}));counts.update(ev.get('equipment_counts',{}));merged['equipment_counts']=dict(counts)
  merged['source_wave_omission']={'wave_handles':spec['wave_handles'],'source_endpoints':[r['xy'],s['xy']],
    'control_issue':policy['control_issue'],'physical_length':'unknown','human_accepted':False}
  semantics={}
  for side,nid,e in [('start',a,eu),('end',b,ev)]:
   old='start' if e['start_node_id']==nid else 'end';merged.pop(side+'_port_id',None)
   if e.get(old+'_port_id'):merged[side+'_port_id']=e[old+'_port_id']
   if e.get('endpoint_semantics',{}).get(old):semantics[side]=copy.deepcopy(e['endpoint_semantics'][old])
  merged['endpoint_semantics']=semantics
  merged['edge_type']='tee_to_virtual_equipment' if any(nodes[i]['node_type']=='virtual_equipment' for i in (a,b)) else 'tee_to_equipment' if any(nodes[i]['node_type']=='equipment' for i in (a,b)) else 'tee_to_tee'
  del edges[ev['edge_id']];edges[eu['edge_id']]=merged;mapping[ev['edge_id']]=eu['edge_id'];del nodes[u['node_id']];del nodes[v['node_id']]
  steps.append({'nodes':spec['nodes'],'wave_handles':spec['wave_handles'],'system':r['system'],'retained_edge':eu['edge_id'],'retired_edge':ev['edge_id']})
 for row in ds:row['edge_id']=mapping.get(row['edge_id'],row['edge_id'])
 for edge in edges.values():
  assigned=[d for d in ds if d['edge_id']==edge['edge_id']]
  if Counter(d['equipment_type'] for d in assigned)!=Counter(edge.get('equipment_counts',{})) or Counter(d['device_name'] for d in assigned)!=Counter(edge.get('equipment_names',[])):raise ValueError('component conservation failure')
 if any(d['edge_id'] not in edges for d in ds):raise ValueError('orphan component')
 # Fail closed if another structure points at a retired graph object. Historical
 # references must be deliberately reconciled, never silently redirected.
 retired=set(mapping)|set(used)
 def find_stale(value):
  if isinstance(value,str):return value if value in retired else None
  if isinstance(value,dict):
   for key,item in value.items():
    if key in retired:return key
    hit=find_stale(item)
    if hit:return hit
  if isinstance(value,list):
   for item in value:
    hit=find_stale(item)
    if hit:return hit
  return None
 for key,value in g.items():
  if key in ('nodes','edges'):continue
  stale=find_stale(value)
  if stale:raise ValueError('retired graph object referenced by '+key+': '+stale)
 for node in nodes.values():
  stale=find_stale(node)
  if stale:raise ValueError('retired graph object referenced by node: '+stale)
 g['nodes']=list(nodes.values());g['edges']=list(edges.values());g.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False)
 validate_references(g)
 g['calibratedWaveOmissionRepair']={'steps':steps,'edge_id_mapping':mapping,'control_issue':policy['control_issue'],'human_accepted':False,'source_sha256':policy['source_sha256']}
 return g,ds

def main():
 ap=argparse.ArgumentParser()
 for name in ('source','graph','devices','policy','output'):ap.add_argument('--'+name,type=Path,required=True)
 a=ap.parse_args();p=json.loads(a.policy.read_text(encoding='utf8'))
 for key,path in [('source_sha256',a.source),('graph_sha256',a.graph),('devices_sha256',a.devices)]:
  if digest(path)!=p[key]:raise ValueError(key+' mismatch')
 doc,proof=read_source(a.source);g=json.loads(a.graph.read_text(encoding='utf8'))
 with a.devices.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;ds=list(reader)
 result,rows=repair(g,ds,doc,p)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True);out=a.output/'graph_with_edges.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 with (a.output/'assigned_edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
 (a.output/'repair-audit.json').write_text(json.dumps({'input_graph_sha256':p['graph_sha256'],'output_graph_sha256':digest(out),'source_sha256':proof['source_sha256'],'steps':result['calibratedWaveOmissionRepair']['steps'],'human_accepted':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'repaired':len(result['calibratedWaveOmissionRepair']['steps']),'human_accepted':False}))
if __name__=='__main__':main()
