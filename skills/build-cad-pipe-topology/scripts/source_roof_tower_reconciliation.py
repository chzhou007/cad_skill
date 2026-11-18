"""Recover explicit project-calibrated nested roof equipment bodies only.

This intentionally does not infer ports from a bbox, attach pipe edges, or
assert installed capacity. Each body preserves the full source INSERT chain.
"""
import copy,math
from ezdxf import bbox

def reconcile(doc,graph,inventory,source_sha256,graph_sha256):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256 or inventory.get('source_sha256')!=source_sha256 or inventory.get('graph_sha256')!=graph_sha256:
  raise ValueError('Roof equipment source or graph identity mismatch')
 if inventory.get('source_caption')!='冷塔单模块' or inventory.get('source_caption_handle')!='59E27':raise ValueError('Project source calibration missing')
 caption=doc.entitydb.get(inventory['source_caption_handle'])
 if caption is None or caption.dxftype()!='TEXT' or caption.plain_text()!=inventory['source_caption']:raise ValueError('Native source caption changed')
 rows=inventory.get('candidates',[])
 if len(rows)!=inventory.get('candidate_insert_count') or len({tuple(r['source_chain'])for r in rows})!=len(rows):raise ValueError('Incomplete or duplicate source body candidates')
 out=copy.deepcopy(graph);existing={n['node_id']for n in out['nodes']};owned={n.get('source_handle')for n in out['nodes']if n.get('node_type')=='equipment'};added=[]
 for row in rows:
  chain=row.get('source_chain',[])
  if len(chain)!=3 or chain[:2]!=['486','39A68']:raise ValueError('Unexpected source ancestry')
  root,parent,body=[doc.entitydb.get(h)for h in chain]
  if any(e is None or e.dxftype()!='INSERT'for e in (root,parent,body)):raise ValueError('Missing native insert')
  if parent.dxf.owner!=doc.blocks.get(root.dxf.name).block_record_handle or body.dxf.owner!=doc.blocks.get(parent.dxf.name).block_record_handle:raise ValueError('Source insert ancestry mismatch')
  if body.dxf.name!=row.get('block') or body.dxf.name!='X-建筑底图_t3$0$kt1.25' or body.dxf.layer!=row.get('source_layer'):raise ValueError('Roof equipment source block mismatch')
  if body.dxf.handle in owned:raise ValueError('Source body is already owned')
  if any(e.dxf.xscale!=1 or e.dxf.yscale!=1 or e.dxf.rotation!=0 for e in (root,parent)):raise ValueError('Uncalibrated parent transform')
  box=bbox.extents([body],fast=True)
  if not box.has_data:raise ValueError('Missing visible native body geometry')
  ox=root.dxf.insert.x+parent.dxf.insert.x;oy=root.dxf.insert.y+parent.dxf.insert.y
  bounds=[box.extmin.x+ox,box.extmin.y+oy,box.extmax.x+ox,box.extmax.y+oy]
  if any(not math.isfinite(a) or abs(a-b)>.01 for a,b in zip(bounds,row['world_bbox'])):raise ValueError('Source body extent changed')
  nid='EQ-ROOF-'+body.dxf.handle
  if nid in existing:raise ValueError('Equipment ID collision')
  node={'node_id':nid,'node_type':'equipment','subtype':'Cooling tower module','subtype_zh':'冷塔单模块',
        'floor':'Roof','label':'Cooling tower module / '+nid,'x':(bounds[0]+bounds[2])/2,'y':(bounds[1]+bounds[3])/2,
        'source_handle':body.dxf.handle,'source_handles':[body.dxf.handle],'source_block':body.dxf.name,
        'display_source_chain':chain,'display_source_handles':[body.dxf.handle],'source_bounds':bounds,
        'source_class_reference':{'text':'冷塔单模块','handle':'59E27','scope':'Project caption and repeated native block form; no instance-specific identity or installed quantity inferred.'},
        'recognition_status':'native_nested_body_and_project_class_reference','source_body_verified':True,
        'source_ports':[],'ports':[],'source_port_completeness':'unbound_source_contacts_require_comparison',
        'parameter_binding_state':'source_type_identified_schedule_variant_unbound','review_required':True,
        'review_queue':'source_comparison','display_source_status':'native_body'}
  out['nodes'].append(node);existing.add(nid);owned.add(body.dxf.handle);added.append(nid)
 return out,{'added_bodies':len(added),'node_ids':added,'edges_unchanged':out['edges']==graph['edges'],
             'ports_inferred':0,'source_sha256':source_sha256,'source_graph_sha256':graph_sha256}
