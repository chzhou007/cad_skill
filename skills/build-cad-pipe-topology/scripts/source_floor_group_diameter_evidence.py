"""Summarize only per-floor edge-bound diameter text, without propagating values."""
import collections,copy,re

def attach(graph,evidence,source_sha256,graph_sha256,doc):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256 or evidence.get('source_sha256')!=source_sha256 or evidence.get('graph_sha256')!=graph_sha256:raise ValueError('Stale diameter evidence')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};adj=collections.defaultdict(list)
 for e in out['edges']:
  for n in (e['start_node_id'],e['end_node_id']):adj[n].append(e)
 groups={x['group_id']:x for x in out.get('sourceFloorAlignmentCandidates',[])};seen=set();annotated=0;original_edges=copy.deepcopy(out['edges'])
 if len(groups)!=evidence.get('groups') or len(evidence.get('records',[]))!=len(groups):raise ValueError('Incomplete group evidence')
 for rec in evidence['records']:
  group=groups.get(rec['group_id']);rows=rec.get('members',[])
  if not group or rec['group_id'] in seen or {(m['floor'],m['node_id'])for m in rows}!={(m['floor'],m['node_id'])for m in group['members']}:raise ValueError('Changed floor group')
  members=[]
  for m in rows:
   n=nodes.get(m['node_id']);edges=adj[m['node_id']]
   if not n or n.get('floor')!=m['floor'] or len(edges)!=1 or edges[0]['edge_id']!=m['edge_id']:raise ValueError('Changed floor edge')
   e=edges[0];value=e.get('diameter_nominal_mm');diam=e.get('pipe_diameter');handles=[]
   if value!=m.get('diameter_nominal_mm') or e.get('diameter_status')!=m.get('diameter_status'):raise ValueError('Changed direct diameter evidence')
   if value is not None:
    if not isinstance(value,(int,float)) or value<=0 or not diam or diam.get('status')!='verified_source_annotation' or diam.get('nominal_mm')!=value or not diam.get('observations'):raise ValueError('Diameter is not directly witnessed')
    for ob in diam['observations']:
     t=ob['text'];native=doc.entitydb.get(t['handle']);text=t.get('original_text',t['text'])
     if native is None or not native.is_alive or native.dxftype() not in ('TEXT','MTEXT','ATTRIB','ATTDEF') or native.plain_text()!=text or ob.get('status')!='assigned' or ob.get('edge_id')!=e['edge_id'] or ob.get('nominal_mm')!=value or not re.search(r'DN\s*'+str(int(value))+r'\b',text,re.I):raise ValueError('Native diameter text witness changed')
     handles.append(t['handle'])
    annotated+=1
   members.append({'floor':m['floor'],'node_id':m['node_id'],'edge_id':e['edge_id'],'direct_diameter_mm':value,'diameter_status':'direct_source_annotation' if value is not None else 'not_directly_annotated','source_text_handles':handles})
  members.sort(key=lambda x:x['floor']);group['members']=members
  for item in members:
   c=nodes[item['node_id']].get('source_floor_alignment_candidate')
   if not c or c.get('group_id')!=group['group_id']:raise ValueError('Missing node group owner')
   c['members']=copy.deepcopy(members)
  seen.add(group['group_id'])
 if out['edges']!=original_edges:raise ValueError('Unexpected edge change')
 return out,{'groups':len(seen),'members':sum(len(g['members'])for g in groups.values()),'direct_annotated_members':annotated,'edges_unchanged':True,'scope':'Each value remains on its own source-annotated edge; no cross-floor diameter propagation.'}
