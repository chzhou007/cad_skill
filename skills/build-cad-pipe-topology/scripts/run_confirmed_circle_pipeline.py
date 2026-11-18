"""Run confirmed-circle repair and terminal-reference reconciliation together.

This is a post-build stage, not a CAD-to-graph family builder. Other sidecars
and expert review remain pending.
"""
import argparse
import csv
import hashlib
import io
import json
import tempfile
from pathlib import Path
from source_readability import read_source
from confirmed_circle_junctions import apply
from reconcile_confirmed_circle_references import reconcile

def digest(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for arg in ('graph','source','original-source','plan','policy','inventory','output-dir'):
  p.add_argument('--'+arg,type=Path,required=True)
 for arg in ('overlay-spans','overlay-groups','overlay-policy'):
  p.add_argument('--'+arg,type=Path)
 for arg in ('length-control','length-variant','length-policy'):
  p.add_argument('--'+arg,type=Path)
 for arg in ('tangent-evidence','tangent-reference','tangent-policy'):
  p.add_argument('--'+arg,type=Path)
 for arg in ('component-inventory','component-policy'):
  p.add_argument('--'+arg,type=Path)
 a=p.parse_args()
 overlay_args=(a.overlay_spans,a.overlay_groups,a.overlay_policy)
 if any(overlay_args) and not all(overlay_args):p.error('all three overlay arguments are required together')
 length_args=(a.length_control,a.length_variant,a.length_policy)
 if any(length_args) and not all(length_args):p.error('all three length arguments are required together')
 tangent_args=(a.tangent_evidence,a.tangent_reference,a.tangent_policy)
 if any(tangent_args) and not all(tangent_args):p.error('all three tangent arguments are required together')
 component_args=(a.component_inventory,a.component_policy)
 if any(component_args) and not all(component_args):p.error('both component arguments are required together')
 if a.output_dir.exists():p.error('output directory already exists')
 if not a.output_dir.parent.is_dir():p.error('output parent does not exist')
 graph=read(a.graph);plan=read(a.plan);policy=read(a.policy);inventory=read(a.inventory)
 original_doc,original=read_source(a.original_source);doc,source=read_source(a.source)
 if original['source_sha256']!=policy.get('original_source_sha256'):
  raise ValueError('Original source hash mismatch')
 if not original['native_chinese_entity_count']:
  raise ValueError('Original source has no readable Chinese text; inspect source before semantic work')
 if original['source_sha256']!=source['source_sha256'] and not policy.get('restored_source_provenance'):
  raise ValueError('Restored source provenance required')
 for witness in policy.get('required_source_texts',[]):
  e=doc.entitydb.get(witness['handle'])
  if e is None or e.dxftype() not in ('TEXT','MTEXT','ATTRIB','ATTDEF') or e.plain_text()!=witness['text']:
   raise ValueError('Required native text witness changed')
 input_hash=digest(a.graph.read_bytes());inv_hash=digest(a.inventory.read_bytes())
 interim,repair=apply(graph,doc,plan,policy,graph_sha256=input_hash,source_sha256=source['source_sha256'])
 interim_bytes=encoded(interim);interim_hash=digest(interim_bytes)
 final,inventory_out,summary=reconcile(interim,inventory,graph_sha256=interim_hash,inventory_sha256=inv_hash)
 circle_bytes=encoded(final);circle_hash=digest(circle_bytes);summary['output_graph_sha256']=circle_hash;inventory_out['graph_sha256']=circle_hash
 overlay_audit=None
 if all(overlay_args):
  from confirmed_overlaid_supply import apply as apply_overlay
  span_data,group_data,overlay_policy=read(a.overlay_spans),read(a.overlay_groups),read(a.overlay_policy)
  final,inventory_out,overlay_audit=apply_overlay(final,inventory_out,doc,span_data,group_data,overlay_policy,
   graph_sha256=circle_hash,source_sha256=source['source_sha256'],inventory_sha256=digest(encoded(inventory_out)),
   span_evidence_sha256=digest(a.overlay_spans.read_bytes()),group_evidence_sha256=digest(a.overlay_groups.read_bytes()))
 before_length_bytes=encoded(final);length_audit=None
 if all(length_args):
  from rebase_section_length_updates import apply as apply_lengths
  length_policy=read(a.length_policy)
  for key,path in (('control_sha256',a.length_control),('variant_sha256',a.length_variant)):
   if digest(path.read_bytes())!=length_policy.get(key):raise ValueError('Length input hash mismatch: '+key)
  if digest(before_length_bytes)!=length_policy.get('target_sha256') or length_policy.get('source_sha256')!=source['source_sha256']:
   raise ValueError('Length target or source hash mismatch')
  final,length_audit=apply_lengths(read(a.length_control),read(a.length_variant),final,source['source_sha256'])
 before_tangent_bytes=encoded(final);inventory_out['graph_sha256']=digest(before_tangent_bytes);tangent_audit=None
 if all(tangent_args):
  from rebase_tangent_circle_evidence import apply as apply_tangent
  final,inventory_out,tangent_audit=apply_tangent(final,inventory_out,read(a.tangent_reference),read(a.tangent_evidence),doc,read(a.tangent_policy),
   source_sha256=source['source_sha256'],graph_sha256=digest(before_tangent_bytes),inventory_sha256=digest(encoded(inventory_out)),
   reference_sha256=digest(a.tangent_reference.read_bytes()),evidence_sha256=digest(a.tangent_evidence.read_bytes()))
 final_bytes=encoded(final);final_hash=digest(final_bytes);inventory_out['graph_sha256']=final_hash
 component_audit=None;component_bytes=None
 if all(component_args):
  from bind_component_inventory import validate as validate_components
  component_bytes=a.component_inventory.read_bytes()
  component_rows=list(csv.DictReader(io.StringIO(component_bytes.decode('utf-8-sig'),newline='')))
  component_audit=validate_components(final,component_rows,read(a.component_policy),graph_sha256=final_hash,
   components_sha256=digest(component_bytes),source_sha256=source['source_sha256'])
 circle_remaining=summary['remaining_terminal_records']
 summary.update(original_source_sha256=original['source_sha256'],restored_source_sha256=source['source_sha256'],
                restored_source_provenance=policy.get('restored_source_provenance','same source'),
                plan_sha256=digest(a.plan.read_bytes()),policy_sha256=digest(a.policy.read_bytes()),
                circle_graph_sha256=circle_hash,output_graph_sha256=final_hash,
                remaining_terminal_records_after_circle=circle_remaining,remaining_terminal_records=len(inventory_out['records']),
                family_counts=inventory_out['family_counts'],
                overlay_spans_applied=len(overlay_audit['steps']) if overlay_audit else 0,
                source_section_length_updates=len(length_audit['changed_edge_ids']) if length_audit else 0,
                tangent_circle_pairs=tangent_audit['pairs'] if tangent_audit else 0,
                component_instances_checked=component_audit['component_instances'] if component_audit else None,
                status='partial_post_build_stage_other_sidecars_pending',hil_ready=False)
 if overlay_audit:
  summary['overlay_policy_sha256']=digest(a.overlay_policy.read_bytes())
 with tempfile.TemporaryDirectory(prefix='.confirmed-circle-',dir=a.output_dir.parent) as temp:
  temp=Path(temp)
  (temp/'intermediate_graph.json').write_bytes(interim_bytes)
  if overlay_audit:(temp/'circle_reconciled_graph.json').write_bytes(circle_bytes)
  if length_audit:(temp/'before_length_graph.json').write_bytes(before_length_bytes)
  if tangent_audit:(temp/'before_tangent_graph.json').write_bytes(before_tangent_bytes)
  (temp/'graph_with_edges.json').write_bytes(final_bytes)
  files=[('repair-audit.json',repair),('remaining-terminal-source-inventory.json',inventory_out),
         ('reconciliation-audit.json',summary),('original-readability.json',original),('source-readability.json',source)]
  if overlay_audit:files.append(('overlay-audit.json',overlay_audit))
  if length_audit:files.append(('section-length-audit.json',length_audit))
  if tangent_audit:files.append(('tangent-audit.json',tangent_audit))
  if component_audit:
   (temp/'edge_device_instances.csv').write_bytes(component_bytes)
   files.append(('component-binding-audit.json',component_audit))
  for name,value in files:
   (temp/name).write_bytes(encoded(value))
  temp.rename(a.output_dir)
 print(json.dumps(summary,ensure_ascii=True))

if __name__=='__main__':main()
