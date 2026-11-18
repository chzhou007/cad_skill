"""Isolated, source- and expert-pinned conversion of leaf endpoints to typed boundaries."""
from pathlib import Path
import argparse, copy, hashlib, json, math, shutil
from source_readability import read_source

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def convert(graph, doc, issue, policy):
 g=copy.deepcopy(graph); spec=policy['anchors']; note=issue['issue']; source_hash=policy['source_sha256']
 if issue['sourceHashes']['main_dxf']!=source_hash or g.get('metadata',{}).get('source_sha256',source_hash)!=source_hash:raise ValueError('source identity mismatch')
 if note['label']!=policy['expert_issue'] or note['note']!=policy['expert_note']:raise ValueError('expert issue mismatch')
 markers=[tuple(s.get('marker_handles',[])) if s.get('marker_kind')=='two_bar' else (s.get('circle_handle'),) for s in spec]
 if not spec or len({x['pipe_handle'] for x in spec})!=len(spec) or len(set(markers))!=len(spec):raise ValueError('duplicate or empty source scope')
 nodes={x['node_id']:x for x in g['nodes']};edges={x['edge_id']:x for x in g['edges']}
 if len(nodes)!=len(g['nodes']) or len(edges)!=len(g['edges']):raise ValueError('duplicate graph IDs')
 x,y,w,h=note['sourceBounds']; anchors=copy.deepcopy(g.get('boundary_anchors',[]));retired=set();changes=[]
 for s in spec:
  inferred=s.get('evidence_basis')=='source_similar_inferred'
  if inferred:
   if s.get('reference_expert_node_id') not in note['nodes'] or s.get('marker_kind')!='two_bar' or s.get('allow_outside_expert_region') is not True:raise ValueError('inferred marker requires explicit expert reference and scope')
  elif s['expert_node_id'] not in note['nodes']:raise ValueError('node absent from expert selection')
  pipe=doc.entitydb.get(s['pipe_handle'])
  if not pipe or pipe.dxftype()!='LINE' or pipe.dxf.layer!=s['source_layer']:raise ValueError('source pipe mismatch')
  candidates=[n for n in nodes.values() if n.get('subtype')=='unresolved_source_terminal' and n.get('node_type')=='virtual_equipment' and n.get('system')==s['system'] and s['pipe_handle'] in n.get('source_handles',[])]
  candidates=[n for n in candidates if math.hypot(n['x']-s['x'],n['y']-s['y'])<.01]
  if len(candidates)!=1:raise ValueError('source endpoint must map uniquely')
  n=candidates[0];nid=n['node_id'];px,py=n['x'],n['y']
  if not inferred and not(x<=px<=x+w and y<=py<=y+h):raise ValueError('endpoint outside expert region')
  if min(math.hypot(p.x-px,p.y-py) for p in (pipe.dxf.start,pipe.dxf.end))>.01:raise ValueError('source pipe endpoint mismatch')
  if s.get('marker_kind')=='two_bar':
   handles=s.get('marker_handles',[]);bars=[doc.entitydb.get(h) for h in handles]
   if len(handles)!=2 or len(set(handles))!=2 or any(not e or e.dxftype()!='LINE' or e.dxf.layer!=s['marker_layer'] for e in bars):raise ValueError('two-bar source mismatch')
   a,b=bars;aa,ab=a.dxf.start,a.dxf.end;ba,bb=b.dxf.start,b.dxf.end
   if abs(aa.y-ab.y)>.01 or abs(ba.y-bb.y)>.01 or abs(abs(aa.x-ab.x)-s['long_length'])>.2 or abs(abs(ba.x-bb.x)-s['short_length'])>.2 or abs((aa.x+ab.x-ba.x-bb.x)/2)>.1 or abs(abs(aa.y-ba.y)-s['spacing'])>.2 or math.hypot((aa.x+ab.x)/2-px,aa.y-py)>.6:raise ValueError('two-bar geometry mismatch')
   if inferred:
    ref=s.get('reference_marker_handles',[]);rr=[doc.entitydb.get(h) for h in ref];rp=doc.entitydb.get(s.get('reference_pipe_handle'))
    if len(ref)!=2 or len(set(ref))!=2 or any(not z or z.dxftype()!='LINE' or z.dxf.layer!=s['marker_layer'] for z in rr) or not rp or rp.dxftype()!='LINE' or rp.dxf.layer!=pipe.dxf.layer:raise ValueError('reference marker source mismatch')
    u,v=rr[0].dxf.start,rr[0].dxf.end;z,t=rr[1].dxf.start,rr[1].dxf.end;rx,ry=(u.x+v.x)/2,u.y
    if abs(u.y-v.y)>.01 or abs(z.y-t.y)>.01 or abs(abs(u.x-v.x)-s['long_length'])>.2 or abs(abs(z.x-t.x)-s['short_length'])>.2 or abs((u.x+v.x-z.x-t.x)/2)>.1 or abs(abs(u.y-z.y)-s['spacing'])>.2 or not(x<=rx<=x+w and y<=ry<=y+h) or min(math.hypot(p.x-rx,p.y-ry) for p in (rp.dxf.start,rp.dxf.end))>.6:raise ValueError('reference marker geometry mismatch')
   marker={'source_marker_kind':'two_bar','source_marker_handles':handles,'source_marker_layer':s['marker_layer'],'source_marker_lengths':[s['long_length'],s['short_length']],'source_marker_spacing':s['spacing'],'source_marker_z':[aa.z,ba.z],'source_pipe_endpoint_z':min((pipe.dxf.start,pipe.dxf.end),key=lambda p:math.hypot(p.x-px,p.y-py)).z}
  else:
   circle=doc.entitydb.get(s['circle_handle'])
   if not circle or circle.dxftype()!='CIRCLE' or pipe.dxf.layer!=circle.dxf.layer or math.hypot(circle.dxf.center.x-px,circle.dxf.center.y-py)>1 or abs(circle.dxf.radius-s['radius'])>.01:raise ValueError('source circle/pipe mismatch')
   marker={'source_circle_handle':s['circle_handle']}
  incident=[e for e in edges.values() if nid in (e['start_node_id'],e['end_node_id'])]
  if len(incident)!=1 or incident[0]['system']!=s['system'] or s['pipe_handle'] not in incident[0].get('source_handles',[]):raise ValueError('endpoint is not a unique same-system leaf')
  e=incident[0];side='start' if e['start_node_id']==nid else 'end';aid='A-'+nid
  if e.get(side+'_port_id') or n.get('ports') or any(p.get('node_id')==nid for p in g.get('virtual_equipment_ports',[])):raise ValueError('endpoint has an existing explicit port; conversion requires a separate mapping')
  if aid in nodes or aid in {a['boundary_id'] for a in anchors}:raise ValueError('boundary ID collision')
  basis={'evidence_basis':'source_similar_inferred','reference_expert_node_id':s['reference_expert_node_id'],'reference_pipe_handle':s['reference_pipe_handle'],'reference_marker_handles':s['reference_marker_handles']} if inferred else {}
  e[side+'_node_id']=None;e[side+'_boundary_id']=aid;anchors.append({'boundary_id':aid,'kind':'expert_non_node_source_boundary','system':s['system'],'x':px,'y':py,'source_pipe_handle':s['pipe_handle'],**marker,**basis,'expert_issue':note['label'],'connectivity_beyond_boundary':'unknown','legacy_node':copy.deepcopy(n),'expert_review':'unreviewed'});retired.add(nid);changes.append({'expert_node_id':s.get('expert_node_id'),'input_node_id':nid,'boundary_id':aid,'edge_id':e['edge_id'],'pipe':s['pipe_handle'],'evidence_basis':basis.get('evidence_basis','expert_selected'),'marker':marker})
 g['nodes']=[n for n in g['nodes'] if n['node_id'] not in retired];g['boundary_anchors']=anchors
 remaining={n['node_id'] for n in g['nodes']}
 for pair in g.get('sourceDetailComparison',{}).get('pairs',[]):
  if pair.get('detail_tee') not in remaining or pair.get('upper_terminal') not in remaining or pair.get('upper_edge') not in edges:raise ValueError('detail comparison references invalid after boundary conversion')
 g.setdefault('metadata',{}).update(source_sha256=source_hash,graph_format='experimental-typed-boundaries-v1',hil_ready=False,graph_complete=False,stage_status='experimental_non_node_boundaries_consumer_integration_pending');return g,changes

def main():
 ap=argparse.ArgumentParser();[ap.add_argument('--'+n,type=Path,required=True) for n in ['source','graph','devices','issue','policy','output']];a=ap.parse_args();p=json.loads(a.policy.read_text(encoding='utf8'))
 for k,path in [('source_sha256',a.source),('input_graph_sha256',a.graph),('devices_sha256',a.devices),('issue_sha256',a.issue)]:
  if sha(path)!=p[k]:raise ValueError(k+' mismatch')
 doc,proof=read_source(a.source)
 if proof['source_sha256']!=p['source_sha256']:raise ValueError('readability preflight source mismatch')
 g=json.loads(a.graph.read_text(encoding='utf8'));issue=json.loads(a.issue.read_text(encoding='utf8'));out,changes=convert(g,doc,issue,p)
 a.output.mkdir(parents=True,exist_ok=False);target=a.output/'graph_with_typed_boundaries.json';target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv');audit={'input_graph_sha256':sha(a.graph),'source_sha256':sha(a.source),'issue_sha256':sha(a.issue),'policy_sha256':sha(a.policy),'devices_sha256':sha(a.devices),'output_graph_sha256':sha(target),'changes':changes,'hil_ready':False,'expert_review':'unreviewed','status':'experimental_typed_boundaries'};(a.output/'boundary-stage.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(audit,ensure_ascii=False))
if __name__=='__main__':main()
