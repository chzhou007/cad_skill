"""Group repeated local source markers across plan layouts without hydraulic joins."""
import copy,math

def attach(graph,evidence,floors,grid,building_sha256,source_sha256,graph_sha256,doc,pitch=130000,tolerance=.5):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256 or evidence.get('source_sha256')!=source_sha256 or evidence.get('current_graph_sha256')!=graph_sha256 or floors.get('source_sha256')!=source_sha256 or floors.get('graph_sha256')!=graph_sha256 or grid.get('source_sha256')!=source_sha256 or grid.get('building_sha256')!=building_sha256:raise ValueError('Stale floor correspondence evidence')
 if not 0<tolerance<=.5 or grid.get('pitch_native_units')!=pitch or evidence.get('derived_floor_pitch_native_units')!=pitch:raise ValueError('Floor alignment calibration mismatch')
 byfloor={r['floor']:r for r in floors.get('records',[])}
 if set(byfloor)!={'F1','F2','F3','F4','F5'}:raise ValueError('Missing native floor titles')
 for r in byfloor.values():
  e=doc.entitydb.get(r['title_handle'])
  if e is None or e.dxftype() not in ('TEXT','MTEXT') or e.plain_text()!=r['title_text']:raise ValueError('Native floor title changed')
 gridgroups=grid.get('matches',[])
 full=[r for r in gridgroups if {m['floor']for m in r['members']}==set(byfloor) and len(r['members'])==5]
 if len(full)<3 or len({tuple(r['normalized_position'])for r in full})<3:raise ValueError('Insufficient independent floor grid evidence')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};seen=set();groups=[]
 for index,record in enumerate(sorted(evidence.get('groups',[]),key=lambda r:tuple(r['normalized_key'])) ,1):
  members=record.get('members',[]);key=record.get('normalized_key',[])
  if len(members)<2 or len(key)!=4 or len({m['floor']for m in members})!=len(members):raise ValueError('Ambiguous floor correspondence')
  normalized=[];output=[]
  for m in members:
   n=nodes.get(m.get('node_id'));candidate=n.get('source_concentric_candidate',{}) if n else {};floor=m['floor']
   if not n or n['node_id']in seen or n.get('node_type')!='virtual_equipment' or n.get('floor')!=floor or n.get('system')!=key[2] or floor not in byfloor or candidate.get('source_circle_handles')!=m.get('rings') or n.get('source_floor_alignment_candidate'):raise ValueError('Changed or competing candidate owner')
   center=candidate.get('center',[])
   if len(center)!=2 or math.dist(center,m['center'])>1e-6:raise ValueError('Circle center changed')
   circles=[doc.entitydb.get(h)for h in m['rings']]
   if any(c is None or c.dxftype()!='CIRCLE' or math.dist((c.dxf.center.x,c.dxf.center.y),center)>.5 for c in circles) or sorted(round(c.dxf.radius)for c in circles)!=key[3]:raise ValueError('Native circle signature changed')
   normalized.append((center[0],center[1]+(5-int(floor[1:]))*pitch));output.append({'node_id':n['node_id'],'floor':floor});seen.add(n['node_id'])
  if max(math.dist(a,b)for a in normalized for b in normalized)>tolerance:raise ValueError('Floor marker position differs')
  gid=f'PLAN-POSITION-{index:03d}';output.sort(key=lambda r:r['floor']);group={'group_id':gid,'system':key[2],'members':output,'status':'repeated_plan_position_candidate','scope':'Matching source layout positions only; no inter-floor equipment identity or hydraulic link inferred.','source_sha256':source_sha256,'source_graph_sha256':graph_sha256}
  for member in output:nodes[member['node_id']]['source_floor_alignment_candidate']={'group_id':gid,'members':output,'status':group['status'],'scope':group['scope']}
  groups.append(group)
 if len(seen)!=sum(len(r['members'])for r in evidence.get('groups',[])):raise ValueError('Incomplete floor grouping')
 out['sourceFloorAlignmentCandidates']=groups;out['metadata']['hil_ready']=False;out['metadata']['stage_status']='repeated_floor_source_positions_pending'
 return out,{'groups':len(groups),'member_nodes':len(seen),'edges_unchanged':out['edges']==graph['edges'],'nodes_added':0,'edges_added':0,'scope':'Layout comparison grouping only; no physical connection or identity inference.'}
