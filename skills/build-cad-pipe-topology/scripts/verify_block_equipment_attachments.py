"""Verify source-supported logical equipment attachments, without port lengths."""
import argparse,collections,csv,hashlib,json,math
from pathlib import Path
from ezdxf import bbox
from source_readability import read_source

def verify(doc,old,graph,joint,source_hash,old_hash,graph_hash):
 if (joint.get('status')!='native_joint_geometry_unreviewed' or joint.get('source_sha256')!=source_hash or joint.get('graph_sha256')!=old_hash or joint.get('graph_mutated') is not False or joint.get('hil_ready') is not False):raise ValueError('stale joint evidence')
 before={e['edge_id']:e for e in old['edges']};edges={e['edge_id']:e for e in graph['edges']};nodes={n['node_id']:n for n in graph['nodes']}
 if len(before)!=len(old['edges']) or len(edges)!=len(graph['edges']) or len(nodes)!=len(graph['nodes']):raise ValueError('duplicate graph IDs')
 texts=collections.defaultdict(list)
 for entity in doc.modelspace().query('TEXT MTEXT'):texts[entity.plain_text()].append(entity)
 groups=collections.defaultdict(list);immutable=('system','start_node_id','end_node_id','source_insert_handle','device_label','attribute_paths')
 for row in joint['edges']:
  eid=row['edge_id'];a=before.get(eid);b=edges.get(eid)
  if not a or not b or any(a.get(k)!=b.get(k) for k in immutable) or row.get('status')!='unique_source_symbol_evidence' or len(row.get('matches',[]))!=1:raise ValueError('changed edge or nonunique joint')
  x=row['matches'][0];ext=b.get('source_device_extension',{});root=b.get('source_insert_handle');device=b.get('device_label')
  if (b.get('connection_mode')!='direct_existing_cad_branch' or device not in (b.get('start_node_id'),b.get('end_node_id')) or nodes.get(device,{}).get('node_type')!='equipment' or row.get('device_label')!=device or row.get('system')!=b.get('system') or ext.get('status')!='source_drawn_line_with_joint_evidence_unreviewed' or ext.get('source_sha256')!=source_hash or ext.get('physical_port_verified') is not False or ext.get('physical_length')!='unknown' or ext.get('source_line_chain')!=x['inner_line_chain'] or ext.get('source_circle_chain')!=x['circle_chain'] or ext.get('source_joint_chain')!=x['joint_chain'] or ext.get('source_outer_line_chain')!=x['outer_line_chain'] or ext.get('joint_component_name')!=x['component_name'] or any(chain[0]!=root for chain in (x['inner_line_chain'],x['circle_chain'],x['joint_chain'],x['outer_line_chain']))):raise ValueError('source chain or equipment mismatch')
  groups[(root,device)].append((b,x))
 records=[]
 for (handle,device),items in sorted(groups.items()):
  root=doc.entitydb.get(handle)
  if not root or root.dxftype()!='INSERT' or root not in doc.modelspace() or len(items)!=2 or {e['system'] for e,_ in items}!={'supply','return'}:raise ValueError('invalid equipment block or systems')
  children=list(root.virtual_entities());body=[e for e in children if e.dxf.layer=='空调平面' and e.dxftype() in ('LINE','CIRCLE')];circles=[e for e in body if e.dxftype()=='CIRCLE'];lines=[e for e in body if e.dxftype()=='LINE']
  if len(circles)!=2 or len(lines)!=12 or any(getattr(c,'source_of_copy',None) is None for c in circles):raise ValueError('unsupported source equipment body')
  handles={c.source_of_copy.dxf.handle for c in circles};selected={x['circle_chain'][1] for _,x in items}
  if len(handles)!=2 or handles!=selected:raise ValueError('device body circles not uniquely covered')
  bounds=bbox.extents(body)
  if not bounds.has_data:raise ValueError('missing native body bounds')
  hits=[n['node_id'] for n in graph['nodes'] if n.get('node_type')=='equipment' and bounds.extmin.x<=n['x']<=bounds.extmax.x and bounds.extmin.y<=n['y']<=bounds.extmax.y]
  if hits!=[device] or len(texts[device])!=1:raise ValueError('equipment body or caption is ambiguous')
  records.append({'equipment_id':device,'source_insert_handle':handle,'caption_handle':texts[device][0].dxf.handle,'body_circle_handles':sorted(handles),'edges':[{'edge_id':e['edge_id'],'system':e['system'],'circle_handle':x['circle_chain'][1],'joint_chain':x['joint_chain']} for e,x in items],'status':'source_block_supports_logical_equipment_attachment','physical_port_verified':False,'physical_length':'unknown','human_accepted':False})
 return {'status':'source_block_equipment_attachments_unreviewed','source_sha256':source_hash,'old_graph_sha256':old_hash,'graph_sha256':graph_hash,'records':records,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['The two native symbol chains support logical attachment to the same drawn equipment instance, not its physical port location or installed connection length.','This check is limited to the exact supported block body, direct child circles and previously source-rechecked joint evidence.','Cross-view identity and full-graph human acceptance remain unresolved.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','old-graph','graph','joint','inventory','circle','joint-policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));old=load(a.old_graph);joint=load(a.joint)
 from native_nested_joint_evidence import collect
 with a.inventory.open(encoding='utf-8-sig',newline='') as f:inventory=list(csv.DictReader(f))
 hashes={'source_sha256':proof['source_sha256'],'graph_sha256':sha(a.old_graph),'inventory_sha256':sha(a.inventory),'circle_sha256':sha(a.circle)}
 checked=collect(doc,old,inventory,load(a.circle),load(a.joint_policy),hashes)
 if checked['edges']!=joint.get('edges') or any(joint.get(k)!=v for k,v in hashes.items()):raise ValueError('joint source evidence does not reproduce')
 r=verify(doc,old,load(a.graph),joint,proof['source_sha256'],sha(a.old_graph),sha(a.graph));r.update(joint_sha256=sha(a.joint),inventory_sha256=sha(a.inventory),circle_sha256=sha(a.circle),joint_policy_sha256=sha(a.joint_policy),script_sha256=sha(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'equipment':len(r['records']),'edges':sum(len(x['edges']) for x in r['records'])}))
if __name__=='__main__':main()
