"""Bind direct joint inventory and source contact audit to the final graph."""
import hashlib,json
from pathlib import Path


def reconcile(inventory,contacts,old,final,hashes):
 if (inventory.get('source_sha256')!=hashes['source_sha256'] or contacts.get('source_sha256')!=hashes['source_sha256'] or inventory.get('inventory_sha256')!=hashes['inventory_sha256'] or contacts.get('inventory_sha256')!=hashes['inventory_sha256'] or contacts.get('graph_sha256')!=hashes['old_graph_sha256']):raise ValueError('joint evidence input mismatch')
 inv=inventory.get('records');audit=contacts.get('records')
 if not isinstance(inv,list) or not isinstance(audit,list):raise ValueError('invalid joint inventory')
 by_handle={x['source_handle']:x for x in audit};old_edges={e['edge_id']:e for e in old['edges']};final_edges={e['edge_id']:e for e in final['edges']}
 if len(by_handle)!=len(audit) or len(old_edges)!=len(old['edges']) or len(final_edges)!=len(final['edges']):raise ValueError('duplicate evidence identity')
 rows=[];seen=set()
 for item in inv:
  handle=item['source_handle']
  if handle in seen:raise ValueError('duplicate inventory source')
  seen.add(handle);status=item['status'];a=by_handle.get(handle)
  if status=='inventory_assignment_present_not_verified':
   matches=item['inventory_matches']
   if len(matches)!=1:raise ValueError('invalid inventory owner')
   owner=matches[0];eid=owner['edge_id'];prior=old_edges.get(eid);now=final_edges.get(eid)
   if not a or not prior or not now or a.get('edge_id')!=eid or a.get('device_name')!=owner.get('device_name') or a.get('assigned_system')!=prior.get('system') or any(prior.get(k)!=now.get(k) for k in ('system','start_node_id','end_node_id','attribute_paths','source_handles')):raise ValueError('joint final edge or owner changed')
   observations=a.get('contacts')
   if not isinstance(observations,list) or len(observations)!=2:raise ValueError('invalid contact evidence')
   if a.get('status')=='same_system_assigned_edge_contact_witnessed':
    for contact in observations:
     lines=contact.get('lines')
     if not isinstance(lines,list) or len(lines)!=1 or lines[0].get('system')!=prior.get('system') or lines[0].get('assigned_edge_witnessed') is not True or not lines[0].get('source_handle'):raise ValueError('invalid same-system contact witness')
    result='two_source_contacts_witnessed_not_acceptance'
   else:result='contact_evidence_pending'
  else:
   if a is not None:raise ValueError('unassigned or conflicting instance has owner audit')
   eid=None;result=status
  rows.append({'source_handle':handle,'edge_id':eid,'status':result,'human_accepted':False})
 if set(by_handle)-seen:raise ValueError('contact audit outside direct instance scope')
 return {'status':'joint_inventory_contacts_bound_to_final_graph_not_acceptance','source_sha256':hashes['source_sha256'],'inventory_sha256':hashes['inventory_sha256'],
         'input_graph_sha256':hashes['old_graph_sha256'],'final_graph_sha256':hashes['final_graph_sha256'],'records':rows,
         'graph_mutated':False,'human_accepted':False,'hil_ready':False,
         'limitations':['Same-system source contacts do not prove physical connectivity or installed length.','Only the scoped direct calibrated block is covered.']}


def write_reconciliation(inventory_path,contacts_path,old_path,final_path,source_hash,inventory_hash,output):
 sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
 hashes={'source_sha256':source_hash,'inventory_sha256':inventory_hash,'old_graph_sha256':sha(old_path),'final_graph_sha256':sha(final_path)}
 result=reconcile(read(inventory_path),read(contacts_path),read(old_path),read(final_path),hashes)
 result.update(inventory_evidence_sha256=sha(inventory_path),contact_evidence_sha256=sha(contacts_path),script_sha256=sha(__file__))
 Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');return result
