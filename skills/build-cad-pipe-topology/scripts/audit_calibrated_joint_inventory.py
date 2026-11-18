"""Reconcile direct modelspace instances of a calibrated block with inventory."""
import argparse,csv,hashlib,json
from collections import Counter
from pathlib import Path
from repair_native_flexible_joints import fingerprint
from source_readability import read_source


def audit(doc,inventory,policy,hashes):
 for key in ('source_sha256','inventory_sha256'):
  if policy.get(key)!=hashes.get(key):raise ValueError('input hash mismatch: '+key)
 block=policy['block_name']
 if block not in doc.blocks or fingerprint(doc.blocks[block])!=policy['block_fingerprint_sha256']:raise ValueError('block fingerprint mismatch')
 # The fingerprint is deliberately exact and sequence-sensitive. Other
 # geometrically similar definitions remain outside this check.
 signature=Counter(e.dxftype() for e in doc.blocks[block]);same_definitions=[]
 for definition in doc.blocks:
  if Counter(e.dxftype() for e in definition)!=signature:continue
  try:
   if fingerprint(definition)==policy['block_fingerprint_sha256']:same_definitions.append(definition.name)
  except ValueError:continue
 same_definitions=sorted(same_definitions)
 nested=[]
 for definition in doc.blocks:
  if definition.name.lower().startswith(('*model_space','*paper_space')):continue
  for e in definition.query('INSERT'):
   if e.dxf.name in same_definitions:nested.append({'parent_block':definition.name,'insert_handle':e.dxf.handle,'referenced_block':e.dxf.name})
 source=[e for e in doc.modelspace().query('INSERT') if e.dxf.name==block]
 handles=[e.dxf.handle for e in source]
 if len(handles)!=len(set(handles)):raise ValueError('duplicate native insert handle')
 records=[]
 for e in source:
  owned=[r for r in inventory if r.get('source_top_handle')==e.dxf.handle]
  if len(owned)>1:status='duplicate_inventory_claims'
  elif not owned:status='unassigned_source_instance'
  elif owned[0].get('equipment_type')!='金属软接':status='inventory_type_conflict'
  elif owned[0].get('assignment_status')!='assigned' or not owned[0].get('edge_id'):status='inventory_assignment_unresolved'
  else:status='inventory_assignment_present_not_verified'
  records.append({'source_handle':e.dxf.handle,'source_layer':e.dxf.layer,'source_position':[e.dxf.insert.x,e.dxf.insert.y,e.dxf.insert.z],
                  'inventory_matches':[{'device_name':r.get('device_name'),'edge_id':r.get('edge_id'),'equipment_type':r.get('equipment_type'),'assignment_status':r.get('assignment_status')} for r in owned],
                  'status':status})
 counts=dict(Counter(r['status'] for r in records))
 return {'status':'direct_calibrated_joint_inventory_not_ownership_acceptance','source_sha256':hashes['source_sha256'],'inventory_sha256':hashes['inventory_sha256'],
         'block_name':block,'block_fingerprint_sha256':policy['block_fingerprint_sha256'],'counts':counts,'total_source_instances':len(source),
         'records':records,'same_fingerprint_block_definitions':same_definitions,'nested_definition_references':nested,'graph_mutated':False,'human_accepted':False,'hil_ready':False,
         'limitations':['Only direct modelspace INSERTs of this exact named and fingerprinted block are included.',
                        'Inventory presence does not verify ownership, connectivity, installation length or human acceptance.',
                        'Nested definition references are reported as possible instances, not expanded or counted; exact fingerprint matching is sequence-sensitive.',
                        'Other geometries, reordered definitions, exploded symbols and paper-space instances are outside this inventory.']}


def main():
 p=argparse.ArgumentParser()
 for x in ('source','inventory','policy','output'):p.add_argument('--'+x,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source)
 with a.inventory.open(encoding='utf-8-sig',newline='') as f:inventory=list(csv.DictReader(f))
 result=audit(doc,inventory,json.loads(a.policy.read_text(encoding='utf8')),{k+'_sha256':sha(getattr(a,k)) for k in ('source','inventory')})
 result.update(source_preflight=proof,policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
 with a.output.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'source_instances':result['total_source_instances'],'counts':result['counts']},ensure_ascii=False))
if __name__=='__main__':main()
