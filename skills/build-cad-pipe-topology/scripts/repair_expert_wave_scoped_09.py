"""Repair two expert-identified same-system wave interruptions in isolation."""
from pathlib import Path
from collections import Counter
import copy,csv,hashlib,json,math,sys
if sys.flags.optimize:raise RuntimeError('Source evidence checks require assertions enabled')
from ezdxf import bbox
sys.path.insert(0,r'C:\Users\lenovo\.codex\skills\build-cad-pipe-topology\scripts')
from source_readability import read_source
import argparse
ap=argparse.ArgumentParser()
for key in ('source','graph','devices','issue','policy','output'):ap.add_argument('--'+key,type=Path,required=True)
args=ap.parse_args();src=args.source;issue=args.issue;out=args.output;load=lambda p:json.loads(p.read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();p=load(args.policy)
for k,v in [('source_sha256',src),('input_graph_sha256',args.graph),('devices_sha256',args.devices),('issue_sha256',issue)]:
 if sha(v)!=p[k]:raise ValueError(k+' mismatch')
doc,proof=read_source(src);i=load(issue);g=load(args.graph);before=copy.deepcopy(g)
if proof['source_sha256']!=i['sourceHashes']['main_dxf'] or g.get('metadata',{}).get('source_sha256',proof['source_sha256'])!=proof['source_sha256'] or i['issue']['label']!=p['expert_issue'] or i['issue']['note']!=p['expert_note']:raise ValueError('source or expert issue mismatch')
if p['wave_pairs']!=[{'system':'return','nodes':['UT0014','UT0015'],'wave_handles':['2A1C0','2A1C1']},{'system':'supply','nodes':['UT0081','UT0082'],'wave_handles':['2A1C2','2A1C3']}]:raise ValueError('wave scope mismatch')
g.setdefault('metadata',{})['source_sha256']=proof['source_sha256']
nodes={n['node_id']:n for n in g['nodes']};edges={e['edge_id']:e for e in g['edges']};
with args.devices.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;devices=list(reader)
mapping={};steps=[]
for system,left,right,waves in [('return','UT0014','UT0015',['2A1C0','2A1C1']),('supply','UT0081','UT0082',['2A1C2','2A1C3'])]:
 u,v=nodes[left],nodes[right];assert u['system']==v['system']==system and u['subtype']==v['subtype']=='unresolved_source_terminal' and u['floor']==v['floor']==2
 eu=[e for e in edges.values() if left in (e['start_node_id'],e['end_node_id'])];ev=[e for e in edges.values() if right in (e['start_node_id'],e['end_node_id'])];assert len(eu)==len(ev)==1;eu,ev=eu[0],ev[0];assert eu['system']==ev['system']==system and eu['edge_id']!=ev['edge_id']
 for node,h in zip((u,v),waves):
  e=doc.entitydb[h];assert e.dxftype()=='INSERT' and e.dxf.name=='$ThvacSys$00000040' and len(list(e.virtual_entities()))==1
  box=bbox.extents(e.virtual_entities());assert box.extmin.x-1<=node['x']<=box.extmax.x+1 and box.extmin.y-1<=node['y']<=box.extmax.y+1
 assert abs(u['y']-v['y'])<.01 and 250<abs(u['x']-v['x'])<350
 # Preserve the longer continuation's ID; the source paths remain disjoint.
 anchor,other=(eu,ev) if eu['path_length']>=ev['path_length'] else (ev,eu);nu,nv=(u,v) if anchor is eu else (v,u)
 a=anchor['end_node_id'] if anchor['start_node_id']==nu['node_id'] else anchor['start_node_id'];b=other['end_node_id'] if other['start_node_id']==nv['node_id'] else other['start_node_id'];assert a!=b
 def orient(e,start):return list(e['path_points'] if e['start_node_id']==start else reversed(e['path_points']))
 merged=copy.deepcopy(anchor);path=orient(anchor,a)+orient(other,nv['node_id']);merged.update(start_node_id=a,end_node_id=b,path=path,path_points=path,attribute_paths=copy.deepcopy(anchor['attribute_paths']+other['attribute_paths']),source_handles=sorted(set(anchor['source_handles']+other['source_handles'])),path_length=anchor['path_length']+other['path_length'],path_length_complete=False,path_length_scope='source_drawn_pipe_only_expert_wave_omission_length_unknown',connection_mode='expert_confirmed_wave_schematic_continuity')
 merged['equipment_names']=anchor.get('equipment_names',[])+other.get('equipment_names',[]);c=Counter(anchor.get('equipment_counts',{}));c.update(other.get('equipment_counts',{}));merged['equipment_counts']=dict(c)
 merged['source_wave_omission']={'expert_issue':'ERR-789DBB','source_insert_handles':waves,'endpoints':[[u['x'],u['y']],[v['x'],v['y']]],'physical_length':'unknown','meaning':'expert confirmed schematic connection; wave marks are not physical nodes'}
 for side,nid,e in [('start',a,anchor),('end',b,other)]:
  merged.pop(side+'_port_id',None);s='start' if e['start_node_id']==nid else 'end'
  if e.get(s+'_port_id'):merged[side+'_port_id']=e[s+'_port_id']
 merged['edge_type']='tee_to_virtual_equipment' if any(nodes[x]['node_type']=='virtual_equipment' for x in (a,b)) else 'tee_to_equipment' if any(nodes[x]['node_type']=='equipment' for x in (a,b)) else 'tee_to_tee'
 del edges[other['edge_id']];edges[anchor['edge_id']]=merged;mapping[other['edge_id']]=anchor['edge_id'];del nodes[left];del nodes[right];steps.append({'system':system,'retired_nodes':[left,right],'retired_edge':other['edge_id'],'retained_edge':anchor['edge_id'],'source_wave_handles':waves,'source_paths':len(merged['attribute_paths']),'omission_graphic_span':math.dist((u['x'],u['y']),(v['x'],v['y'])),'physical_length':'unknown'})
for d in devices:d['edge_id']=mapping.get(d['edge_id'],d['edge_id'])
for e in edges.values():
 ds=[d for d in devices if d['edge_id']==e['edge_id']];assert Counter(d['device_name'] for d in ds)==Counter(e.get('equipment_names',[])) and Counter(d['equipment_type'] for d in ds)==Counter(e.get('equipment_counts',{}))
g['nodes']=list(nodes.values());g['edges']=list(edges.values());g['metadata'].update(hil_ready=False,graph_complete=False,stage_status='expert_wave_pair_connections_repaired_outer_endpoints_pending');g['expertWaveOmissionRepair']={'source_sha256':proof['source_sha256'],'issue':'ERR-789DBB','expert_note':i['issue']['note'],'steps':steps,'edge_id_mapping':mapping,'scope':'Two wave pairs joined by service; two outermost highlighted boundaries remain unverified logical endpoints and the human review remains pending.'}
assert len(g['nodes'])==len(before['nodes'])-4 and len(g['edges'])==len(before['edges'])-2 and all(e['start_node_id'] in nodes and e['end_node_id'] in nodes for e in g['edges'])
if out.exists():raise ValueError('output exists')
out.mkdir(parents=True);(out/'graph_with_edges.json').write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
with (out/'assigned_edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(devices)
report={'source_sha256':proof['source_sha256'],'input_graph_sha256':sha(args.graph),'devices_sha256':sha(args.devices),'issue_sha256':sha(issue),'policy_sha256':sha(args.policy),'output_graph_sha256':sha(out/'graph_with_edges.json'),'nodes_before':len(before['nodes']),'nodes_after':len(g['nodes']),'edges_before':len(before['edges']),'edges_after':len(g['edges']),'original_component_instances':len(devices),'steps':steps,'edge_id_mapping':mapping,'outer_flagged_nodes_still_pending':['UT0013','UT0080'],'hil_ready':False,'review':'unreviewed'}
(out/'repair-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False))
