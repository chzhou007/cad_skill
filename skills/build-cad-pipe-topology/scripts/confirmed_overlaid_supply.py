"""Apply a finite user-confirmed set of circle-witnessed overlapping supply spans.

Only the two confirmed circles delimit a span. Display connectors are not native
pipe geometry; valve ownership and physical length remain unresolved.
"""
import copy
import math
import re
from collections import Counter


def apply(graph,inventory,doc,span_data,group_data,policy,*,graph_sha256,source_sha256,inventory_sha256,span_evidence_sha256,group_evidence_sha256):
 if (graph.get('metadata',{}).get('source_sha256')!=source_sha256 or
     inventory.get('source_sha256')!=source_sha256 or inventory.get('graph_sha256')!=graph_sha256 or
     span_data.get('source_sha256')!=source_sha256 or group_data.get('source_sha256')!=source_sha256 or
     policy.get('source_sha256')!=source_sha256 or policy.get('graph_sha256')!=graph_sha256 or
     policy.get('span_evidence_sha256')!=span_evidence_sha256 or policy.get('group_evidence_sha256')!=group_evidence_sha256 or
     not span_evidence_sha256 or not group_evidence_sha256):
  raise ValueError('Stale graph, inventory or source')
 if not policy.get('user_confirmation') or not policy.get('confirmation_evidence'):
  raise ValueError('Explicit user confirmation required')
 wanted=policy.get('confirmed_spans',[])
 keys=[tuple(x['pair']) for x in wanted]
 if not keys or any(len(k)!=2 or k[0]==k[1] for k in keys) or len(set(keys))!=len(keys):
  raise ValueError('Invalid confirmed span scope')
 spans={(r['group_a'],r['group_b']):r for r in span_data['records']}
 if len(spans)!=len(span_data['records']) or not set(keys)<=spans.keys():raise ValueError('Missing or duplicate span evidence')
 groups={g['group_id']:g for g in group_data['records']}
 if len(groups)!=len(group_data['records']):raise ValueError('Duplicate source group')
 out=copy.deepcopy(graph);inv=copy.deepcopy(inventory)
 nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']}
 if len(nodes)!=len(out['nodes']) or len(edges)!=len(out['edges']):raise ValueError('Duplicate graph identities')
 repaired=out.get('confirmedCircleJunctions',{});confirmed={r['circle_handle'] for r in repaired.get('rewired_edge_ends',[])}
 if repaired.get('source_sha256')!=source_sha256:raise ValueError('Missing same-source confirmed return circle repairs')
 next_node=max((int(k[1:]) for k in nodes if re.fullmatch(r'T\d+',k)),default=0)+1
 next_edge=max((int(k[1:]) for k in edges if re.fullmatch(r'E\d+',k)),default=0)+1
 tol=policy.get('contact_tolerance',.1); max_gap=policy.get('max_display_gap')
 if not isinstance(tol,(int,float)) or not math.isfinite(tol) or not 0<tol<=1 or not isinstance(max_gap,(int,float)) or not math.isfinite(max_gap) or max_gap<=0:
  raise ValueError('Invalid calibrated tolerances')
 retired={};created=[];steps=[];changed_edges=set();original_non_supply={e['edge_id']:copy.deepcopy(e) for e in out['edges'] if e['system']!='supply'}
 original_incidence={}
 for edge in out['edges']:
  for nid in (edge['start_node_id'],edge['end_node_id']):original_incidence.setdefault(nid,[]).append(edge['edge_id'])

 def source_group(gid):
  g=groups[gid];rh=g['return_circle'];sh=g['supply_circle'];r=doc.entitydb.get(rh);s=doc.entitydb.get(sh)
  if rh not in confirmed or not r or not s or r.dxftype()!='CIRCLE' or s.dxftype()!='CIRCLE':raise ValueError('Confirmed source circle pair required')
  if r.dxf.layer!=policy['return_layer'] or s.dxf.layer!=policy['supply_layer'] or tuple(r.dxf.extrusion)!=(0.,0.,1.) or tuple(s.dxf.extrusion)!=(0.,0.,1.):raise ValueError('Circle service or transform mismatch')
  c=[s.dxf.center.x,s.dxf.center.y];rc=[r.dxf.center.x,r.dxf.center.y]
  if not all(math.isfinite(x) for x in c+rc+[r.dxf.radius,s.dxf.radius]):raise ValueError('Non-finite source circle')
  if (math.dist(c,g['supply_circle_center'])>tol or abs(math.dist(c,rc)-r.dxf.radius-s.dxf.radius)>tol or
      not math.isfinite(s.dxf.radius) or s.dxf.radius<=tol):raise ValueError('Source circle geometry mismatch')
  branch_handles=g.get('supply_native_branch_handles',[])
  if len(branch_handles)!=1:raise ValueError('Unique native branch witness required')
  native=doc.entitydb.get(branch_handles[0])
  if native is None or native.dxftype()!='LINE' or native.dxf.layer!=policy['supply_layer']:raise ValueError('Native supply branch mismatch')
  return g,c,s.dxf.radius,branch_handles[0]

 def circle_node(gid):
  nonlocal next_node
  group,center,radius,handle=source_group(gid)
  exists=[n for n in nodes.values() if n.get('source_circle_handle')==group['supply_circle'] and n.get('system')=='supply']
  if len(exists)>1:raise ValueError('Ambiguous existing supply circle node')
  if exists:
   n=exists[0]
   if n.get('subtype')!='user_confirmed_overlaid_supply_partial_junction' or math.dist((n['x'],n['y']),center)>tol:raise ValueError('Existing supply circle mismatch')
   n['continuation_status']='both_known_adjacent_spans_confirmed_other_extent_pending'
   return n
  matches=[e for e in edges.values() if e['system']=='supply' and handle in e.get('source_handles',[])]
  if len(matches)!=1:raise ValueError('Supply branch edge not unique')
  edge=matches[0];ends=[nodes[k] for k in (edge['start_node_id'],edge['end_node_id']) if nodes[k].get('subtype')=='unresolved_source_terminal']
  if len(ends)!=1:raise ValueError('Supply branch terminal not unique')
  old=ends[0];oldid=old['node_id'];side='start' if edge['start_node_id']==oldid else 'end'
  if old.get('system')!='supply' or sum(oldid in (e['start_node_id'],e['end_node_id']) for e in edges.values())!=1 or abs(math.dist((old['x'],old['y']),center)-radius)>tol:
   raise ValueError('Supply circle rim mismatch')
  native=doc.entitydb[handle];ends_xy=[(native.dxf.start.x,native.dxf.start.y),(native.dxf.end.x,native.dxf.end.y)]
  if min(math.dist((old['x'],old['y']),p) for p in ends_xy)>tol:raise ValueError('Branch terminal lacks native line endpoint')
  path=edge['path_points'];rim=[old['x'],old['y']]
  if math.dist(path[0 if side=='start' else -1][:2],rim)>tol:raise ValueError('Branch path endpoint mismatch')
  nid='T'+str(next_node).zfill(3);next_node+=1
  n={'node_id':nid,'node_type':'tee','subtype':'user_confirmed_overlaid_supply_partial_junction','floor':old.get('floor'),'system':'supply',
     'x':center[0],'y':center[1],'label':nid,'source_circle_handle':group['supply_circle'],'source_handles':[group['supply_circle']],
     'recognition_status':'user_confirmed_supply_branch_connected_to_overlaid_supply_span','continuation_status':'outside_span_unconfirmed',
     'review_status':'unreviewed','source_boundary_node_retired':oldid,'local_symbol_internal_physical_length':'unknown'}
  if not n['floor']:raise ValueError('Supply floor unknown')
  edge[side+'_node_id']=nid;edge.pop(side+'_port_id',None)
  edge['path_points']=[center]+path if side=='start' else path+[center]
  edge['path_length_complete']=False;edge['path_length_scope']='source_drawn_pipe_only_symbol_interior_excluded'
  edge.setdefault('source_symbol_connectors',[]).append({'source_circle_handle':group['supply_circle'],'source_rim_point':rim,'junction_center':center,'geometry_role':'topology_display_only','physical_length':'unknown','source_pipe_geometry':'not asserted'})
  edge.setdefault('endpoint_reconciliation',[]).append({'old_node_id':oldid,'new_node_id':nid,'side':side,'source_circle_handle':group['supply_circle'],'confirmation':'user_confirmed_supply_and_return_overlay'})
  changed_edges.add(edge['edge_id'])
  del nodes[oldid];nodes[nid]=n;retired[oldid]=nid
  return n

 for item in wanted:
  pair=tuple(item['pair']);span=spans[pair];kind=item['kind']
  if kind not in ('hidden_supply','native_partial_supply'):raise ValueError('Unknown confirmed span kind')
  for segment in span.get('source_segments',[]):
   entity=doc.entitydb.get(segment['source_handle'])
   if not entity or entity.dxf.layer!=segment['source_layer']:raise ValueError('Missing native span source')
  a,b=[circle_node(gid) for gid in pair]
  if a['floor']!=b['floor'] or a['node_id']==b['node_id']:raise ValueError('Supply circle pair floor or identity mismatch')
  if (not isinstance(span.get('span'),(int,float)) or not math.isfinite(span['span']) or
      any(not isinstance(v,(int,float)) or not math.isfinite(v) for xy in (span['a_xy'],span['b_xy']) for v in xy)):
   raise ValueError('Non-finite source span')
  if (math.dist((a['x'],a['y']),span['a_xy'])>tol or math.dist((b['x'],b['y']),span['b_xy'])>tol or
      abs(math.dist((a['x'],a['y']),(b['x'],b['y']))-span['span'])>tol):raise ValueError('Span does not match the confirmed circle centers')
  dx,dy=b['x']-a['x'],b['y']-a['y'];axis=math.hypot(dx,dy)
  if axis<=tol:raise ValueError('Degenerate confirmed span')
  for segment in span.get('source_segments',[]):
   entity=doc.entitydb[segment['source_handle']]
   if entity.dxftype()!='LINE':raise ValueError('Span source is not a native line')
   points=[(entity.dxf.start.x,entity.dxf.start.y),(entity.dxf.end.x,entity.dxf.end.y)]
   if not all(math.isfinite(v) for p in points for v in p):raise ValueError('Non-finite source line')
   offsets=[abs((p[0]-a['x'])*dy-(p[1]-a['y'])*dx)/axis for p in points]
   projected=[((p[0]-a['x'])*dx+(p[1]-a['y'])*dy)/axis for p in points]
   if max(offsets)>tol or min(axis,max(projected))-max(0,min(projected))<=tol:
    raise ValueError('Source line does not overlap confirmed span axis')
  if kind=='hidden_supply':
   if any(x['source_layer']==policy['supply_layer'] for x in span.get('source_segments',[])):raise ValueError('Hidden span has a native supply source')
   eid='E'+str(next_edge).zfill(4);next_edge+=1
   edge={'edge_id':eid,'start_node_id':a['node_id'],'end_node_id':b['node_id'],'edge_type':'tee_to_tee','system':'supply',
         'floor_start':a['floor'],'floor_end':b['floor'],'path_points':[[a['x'],a['y']],[b['x'],b['y']]],'attribute_paths':[],
         'path_length':0,'path_length_complete':False,'path_length_scope':'no_native_supply_path_length_unknown',
         'source_path_status':'user_confirmed_overlay_no_native_supply_path','source_handles':[],'source_systems':['supply'],
         'system_assignment':'user_confirmed_overlaid_supply','connection_mode':'user_confirmed_overlaid_supply','equipment_inventory':[],
         'physical_length':'unknown','diameter_nominal_mm':None,'diameter_text':'','diameter_status':'unannotated',
         'source_overlay_evidence':{'return_source_handles':[x['source_handle'] for x in span.get('source_segments',[]) if x['source_layer']==policy['return_layer']],
             'valve_ownership':'unverified; original component assignments retained'}}
   branch_evidence=[]
   for node in (a,b):
    incident=[e for e in edges.values() if e['system']=='supply' and node['node_id'] in (e['start_node_id'],e['end_node_id'])]
    if len(incident)!=1:raise ValueError('Hidden span branch evidence is not unique')
    branch_evidence.append(incident[0])
   for name in ('pipe_floor_location','floor_location_text_zh','floor_location_status'):
    if branch_evidence[0].get(name) is not None and branch_evidence[0].get(name)==branch_evidence[1].get(name):
     edge[name]=copy.deepcopy(branch_evidence[0][name])
   edge['pipe_diameter']={'status':'unannotated','nominal_mm':None,'display':'','observations':[],
      'scope':'No direct source diameter observation assigned to this inferred supply span.'}
   if not edge['source_overlay_evidence']['return_source_handles']:raise ValueError('Hidden span lacks native return evidence')
   edges[eid]=edge;created.append(eid)
  else:
   sources=[x['source_handle'] for x in span.get('source_segments',[]) if x['source_layer']==policy['supply_layer']]
   if len(sources)!=1:raise ValueError('Native partial supply span must be unique')
   matches=[e for e in edges.values() if e['system']=='supply' and sources[0] in e.get('source_handles',[])]
   if len(matches)!=1:raise ValueError('Native supply edge not unique')
   edge=matches[0];original=copy.deepcopy(edge);targets=[];native_main=doc.entitydb[sources[0]]
   if native_main.dxftype()!='LINE':raise ValueError('Native partial span is not a line')
   native_ends=[(native_main.dxf.start.x,native_main.dxf.start.y),(native_main.dxf.end.x,native_main.dxf.end.y)]
   for side in ('start','end'):
    oldid=original[side+'_node_id'];v=nodes.get(oldid)
    if not v or v.get('subtype')!='unresolved_source_terminal' or v.get('system')!='supply' or sum(oldid in (e['start_node_id'],e['end_node_id']) for e in edges.values())!=1:raise ValueError('Native main terminal mismatch')
    if min(math.dist((v['x'],v['y']),p) for p in native_ends)>tol or math.dist((v['x'],v['y']),original['path_points'][0 if side=='start' else -1][:2])>tol:raise ValueError('Native main endpoint witness mismatch')
    near=sorted((math.dist((n['x'],n['y']),(v['x'],v['y'])),n['node_id']) for n in (a,b))
    if near[0][0]<=tol or near[0][0]>max_gap or abs(near[1][0]-near[0][0])<=tol or near[0][1] in targets:raise ValueError('Ambiguous native main endpoint')
    target=nodes[near[0][1]];targets.append(target['node_id']);pt=[target['x'],target['y']]
    edge[side+'_node_id']=target['node_id'];edge.pop(side+'_port_id',None)
    edge['path_points']=[pt]+edge['path_points'] if side=='start' else edge['path_points']+[pt]
    edge.setdefault('source_overlay_connectors',[]).append({'source_endpoint':[v['x'],v['y']],'target_supply_circle':target['source_circle_handle'],'target_node':target['node_id'],'topology_only':True,'physical_length':'unknown','source_pipe_geometry':'not asserted'})
    del nodes[oldid];retired[oldid]=target['node_id']
   edge['path_length_complete']=False;edge['path_length_scope']='source_drawn_pipe_only_overlay_continuation_unknown'
   edge['connection_mode']='user_confirmed_overlaid_supply_with_native_partial_path';edge['overlay_valve_ownership_status']='existing_assignments_unverified'
   eid=edge['edge_id'];changed_edges.add(eid)
  steps.append({'pair':list(pair),'kind':kind,'supply_edge':eid,'supply_nodes':[a['node_id'],b['node_id']]})
 out['nodes']=list(nodes.values());out['edges']=list(edges.values())
 for eid in changed_edges:
  edge=edges[eid];types=[nodes[edge[k]]['node_type'] for k in ('start_node_id','end_node_id')]
  edge['edge_type']='tee_to_tee' if all(k=='tee' for k in types) else 'tee_to_equipment' if 'equipment' in types else 'tee_to_virtual_equipment'
 if any(edges[k]!=v for k,v in original_non_supply.items()):raise ValueError('Non-supply edge changed')
 records=inv.get('records',[]);removed=[r for r in records if r.get('node_id') in retired];keep=[r for r in records if r.get('node_id') not in retired]
 if len(removed)!=len(retired) or {r['node_id'] for r in removed}!=set(retired):raise ValueError('Retired supply inventory does not match')
 if any(original_incidence.get(r['node_id'])!=[r.get('edge_id')] for r in removed):raise ValueError('Retired terminal inventory edge mismatch')
 if any(r.get('node_id') not in nodes or (r.get('edge_id') and (r['edge_id'] not in edges or r['node_id'] not in (edges[r['edge_id']]['start_node_id'],edges[r['edge_id']]['end_node_id']))) for r in keep):raise ValueError('Unreconciled remaining terminal')
 inv.update(records=keep,remaining_unclassified_nodes=len(keep),family_counts=dict(Counter(r['family'] for r in keep)))
 inv['supply_retired_record_archive']={'source_inventory_sha256':inventory_sha256,'records':removed,'retired_to_junction':retired}
 out['metadata'].update(hil_ready=False,graph_complete=False,stage_status='confirmed_overlay_spans_other_references_pending')
 out.setdefault('technicalPending',[]).append({'id':'OVERLAY-VALVE-OWNERSHIP','kind':'source_ambiguity','reason':'Existing component assignments are preserved; valve ownership on overlapping supply/return remains unverified.'})
 gate=out.setdefault('preHilComparison',{'status':'pending','families':[]});gate['status']='pending';gate.setdefault('families',[]).append({'id':'overlay-other-references-and-valves','status':'algorithm_pending'})
 audit={'source_sha256':source_sha256,'input_graph_sha256':graph_sha256,'user_confirmation':policy['user_confirmation'],
        'confirmation_evidence':policy['confirmation_evidence'],'span_evidence_sha256':span_evidence_sha256,
        'group_evidence_sha256':group_evidence_sha256,'retired_boundaries':retired,'created_edges':created,'steps':steps,
        'physical_extra_length':'unknown','valve_ownership':'unverified','hil_ready':False}
 out['confirmedOverlaidSupplySpans']=copy.deepcopy(audit)
 return out,inv,audit
