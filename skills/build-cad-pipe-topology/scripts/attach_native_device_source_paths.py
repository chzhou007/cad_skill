"""Attach source-backed device-side drawing paths without altering connectivity."""
import argparse, copy, csv, hashlib, json
from pathlib import Path
from source_readability import read_source
from native_nested_joint_evidence import collect


def attach(doc, graph, inventory, circle, joint, policy, hashes):
 if joint.get('status')!='native_joint_geometry_unreviewed':raise ValueError('invalid joint evidence')
 checked=collect(doc,graph,inventory,circle,policy,hashes)
 if checked['edges']!=joint.get('edges') or any(joint.get(k)!=hashes[k] for k in ('source_sha256','graph_sha256','inventory_sha256','circle_sha256')):
  raise ValueError('joint evidence does not reproduce')
 if any(row['status']!='unique_source_symbol_evidence' or len(row['matches'])!=1 for row in checked['edges']):raise ValueError('unresolved joint candidates')
 g=copy.deepcopy(graph);edges={e['edge_id']:e for e in g['edges']};nodes={n['node_id']:n for n in g['nodes']}
 if len(edges)!=len(g['edges']) or len(nodes)!=len(g['nodes']):raise ValueError('duplicate graph ids')
 for row in checked['edges']:
  edge=edges[row['edge_id']];match=row['matches'][0];device=edge.get('device_label')
  if device not in (edge.get('start_node_id'),edge.get('end_node_id')) or device not in nodes or nodes[device].get('node_type') not in ('equipment','physical_equipment'):raise ValueError('device node mismatch')
  if edge.get('path_length_complete') is not False or edge.get('physical_length')!='unknown' or not edge.get('source_path_coverage'):raise ValueError('incomplete length protection required')
  if edge.get('source_device_extension'):raise ValueError('extension already attached')
  edge['source_device_extension']={'status':'source_drawn_line_with_joint_evidence_unreviewed','source_sha256':hashes['source_sha256'],'input_graph_sha256':hashes['graph_sha256'],'circle_evidence_sha256':hashes['circle_sha256'],'joint_evidence_sha256':hashes['joint_sha256'],'source_line_chain':match['inner_line_chain'],'source_joint_chain':match['joint_chain'],'source_circle_chain':match['circle_chain'],'source_outer_line_chain':match['outer_line_chain'],'joint_component_name':match['component_name'],'physical_port_verified':False,'physical_length':'unknown','changes_topology':False}
 g.setdefault('metadata',{}).update(hil_ready=False,review_status='unreviewed')
 return g


def main():
 p=argparse.ArgumentParser()
 for key in ('source','graph','inventory','circle','joint','policy','output'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);sha=lambda b:hashlib.sha256(b).hexdigest();gb=a.graph.read_bytes();ib=a.inventory.read_bytes();cb=a.circle.read_bytes();jb=a.joint.read_bytes();pb=a.policy.read_bytes()
 with a.inventory.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 hashes={'source_sha256':proof['source_sha256'],'graph_sha256':sha(gb),'inventory_sha256':sha(ib),'circle_sha256':sha(cb),'joint_sha256':sha(jb)}
 g=attach(doc,json.loads(gb),rows,json.loads(cb),json.loads(jb),json.loads(pb),hashes)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(g,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'extensions':sum(bool(e.get('source_device_extension')) for e in g['edges']),'hil_ready':False}))
if __name__=='__main__':main()
