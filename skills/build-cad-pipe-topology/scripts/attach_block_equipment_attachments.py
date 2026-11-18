"""Attach independently recomputed source-block logical equipment evidence."""
import argparse,copy,csv,hashlib,json
from pathlib import Path
from native_nested_joint_evidence import collect
from source_readability import read_source
from verify_block_equipment_attachments import verify

def attach(graph,report,source_hash,graph_hash,evidence_hash):
 if (report.get('status')!='source_block_equipment_attachments_unreviewed' or report.get('source_sha256')!=source_hash or report.get('graph_sha256')!=graph_hash or report.get('graph_mutated') is not False or report.get('human_accepted') is not False or report.get('hil_ready') is not False or not evidence_hash):raise ValueError('stale attachment evidence')
 g=copy.deepcopy(graph);edges={e['edge_id']:e for e in g['edges']};nodes={n['node_id']:n for n in g['nodes']};mappings=[];seen=set()
 if len(edges)!=len(g['edges']) or len(nodes)!=len(g['nodes']) or g.get('sourceBlockEquipmentAttachment'):raise ValueError('duplicate IDs or attachment already present')
 for r in report.get('records',[]):
  did=r.get('equipment_id');root=r.get('source_insert_handle');items=r.get('edges')
  if (r.get('status')!='source_block_supports_logical_equipment_attachment' or r.get('physical_port_verified') is not False or r.get('physical_length')!='unknown' or r.get('human_accepted') is not False or nodes.get(did,{}).get('node_type')!='equipment' or not root or not isinstance(items,list) or len(items)!=2 or {x.get('system') for x in items}!={'supply','return'}):raise ValueError('invalid source block record')
  for item in items:
   eid=item.get('edge_id');e=edges.get(eid);ext=e.get('source_device_extension',{}) if e else {}
   if (eid in seen or not e or e.get('system')!=item.get('system') or did not in (e.get('start_node_id'),e.get('end_node_id')) or e.get('source_insert_handle')!=root or ext.get('source_circle_chain')!=[root,item.get('circle_handle')] or ext.get('source_joint_chain')!=item.get('joint_chain') or e.get('physical_length')!='unknown' or e.get('path_length_complete') is not False or e.get('source_block_equipment_attachment')):raise ValueError('attachment does not match current edge')
   side='start' if e['start_node_id']==did else 'end'
   snapshot={'start_node_id':e['start_node_id'],'end_node_id':e['end_node_id'],'system':e['system'],'attribute_paths':copy.deepcopy(e['attribute_paths']),'equipment_xy':[nodes[did]['x'],nodes[did]['y']]}
   e['source_block_equipment_attachment']={'status':'source_supported_logical_attachment_not_human_accepted','source_sha256':source_hash,'input_graph_sha256':graph_hash,'evidence_sha256':evidence_hash,'equipment_id':did,'interface_side':side,'source_insert_handle':root,'source_circle_handle':item['circle_handle'],'source_joint_chain':item['joint_chain'],'source_edge_snapshot':snapshot,'physical_port_verified':False,'physical_length':'unknown','human_accepted':False};mappings.append({'edge_id':eid,'equipment_id':did,'system':e['system'],'source_insert_handle':root,'source_circle_handle':item['circle_handle']});seen.add(eid)
 if not mappings:raise ValueError('empty source attachments')
 g['sourceBlockEquipmentAttachment']={'status':'source_supported_logical_attachments_not_human_accepted','source_sha256':source_hash,'input_graph_sha256':graph_hash,'evidence_sha256':evidence_hash,'mappings':mappings,'physical_ports_verified':False,'physical_lengths_known':False,'human_accepted':False}
 g.setdefault('metadata',{}).update(hil_ready=False,review_status='unreviewed_after_source_evidence_change')
 return g

def main():
 p=argparse.ArgumentParser()
 for k in ('source','old-graph','graph','joint','inventory','circle','joint-policy','evidence','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));old=load(a.old_graph);graph=load(a.graph);joint=load(a.joint);circle=load(a.circle);policy=load(a.joint_policy);report=load(a.evidence)
 with a.inventory.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 hashes={'source_sha256':proof['source_sha256'],'graph_sha256':sha(a.old_graph),'inventory_sha256':sha(a.inventory),'circle_sha256':sha(a.circle)};rechecked=collect(doc,old,rows,circle,policy,hashes)
 if rechecked['edges']!=joint.get('edges') or any(joint.get(k)!=v for k,v in hashes.items()):raise ValueError('joint evidence does not reproduce')
 expected=verify(doc,old,graph,joint,proof['source_sha256'],sha(a.old_graph),sha(a.graph))
 if any(report.get(k)!=expected.get(k) for k in ('status','source_sha256','old_graph_sha256','graph_sha256','records','graph_mutated','human_accepted','hil_ready')):raise ValueError('attachment evidence does not reproduce')
 output=attach(graph,report,proof['source_sha256'],sha(a.graph),sha(a.evidence))
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True);target=a.output/'graph_with_source_block_attachments.json';target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8');audit={'status':'source_evidence_added_not_human_acceptance','source_sha256':proof['source_sha256'],'input_graph_sha256':sha(a.graph),'output_graph_sha256':sha(target),'evidence_sha256':sha(a.evidence),'script_sha256':sha(Path(__file__)),'edges':len(output['sourceBlockEquipmentAttachment']['mappings']),'graph_connectivity_changed':False,'human_accepted':False,'hil_ready':False};(a.output/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(audit))
if __name__=='__main__':main()
