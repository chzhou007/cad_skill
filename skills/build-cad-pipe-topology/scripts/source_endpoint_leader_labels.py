"""Attach precisely leader-linked source endpoint text without inferring connectivity."""
import copy,math

def attach(graph,doc,source_sha256,records):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256:raise ValueError('Source mismatch')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};used=set();labels=set();leaders=set()
 for r in records:
  n=nodes.get(r['node_id']);t=doc.entitydb.get(r['text_handle']);l=doc.entitydb.get(r['leader_handle'])
  if not n or n.get('boundary_type')!='unresolved_source_terminal' or n['node_id'] in used:raise ValueError('Endpoint missing, resolved or duplicated')
  if not t or t.dxftype()!='TEXT' or not l or l.dxftype() not in ('LINE','LWPOLYLINE') or t.dxf.owner!=doc.modelspace().block_record_handle or l.dxf.owner!=doc.modelspace().block_record_handle:raise ValueError('Missing native text or leader')
  if (t.dxf.handle in labels and not r.get('shared_text_label')) or l.dxf.handle in leaders or t.dxf.layer!=r['layer'] or l.dxf.layer!=r['layer'] or t.plain_text()!=r['text']:raise ValueError('Changed, duplicate or wrongly layered source text')
  if l.dxftype()=='LINE':
   vertices=[l.ocs().to_wcs(l.dxf.start),l.ocs().to_wcs(l.dxf.end)]
  else:
   if l.closed or any(abs(float(point[4]))>1e-12 for point in l.get_points('xyseb')):raise ValueError('Unsupported leader geometry')
   vertices=list(l.vertices_in_wcs())
   if len(vertices)<2:raise ValueError('Invalid leader polyline')
  p=t.ocs().to_wcs(t.dxf.insert);xy=(n['x'],n['y'])
  d1=math.dist((vertices[0].x,vertices[0].y),xy);d2=math.dist((vertices[-1].x,vertices[-1].y),xy)
  if min(d1,d2)>r['endpoint_tolerance']:raise ValueError('Leader misses terminal')
  anchors=vertices[1:] if d1<d2 else vertices[:-1]
  if min(math.dist((v.x,v.y),(p.x,p.y)) for v in anchors)>r['text_anchor_tolerance']:raise ValueError('Leader misses text insertion')
  n['source_endpoint_annotation']={'text':r['text'],'text_handle':r['text_handle'],'leader_handle':r['leader_handle'],'source_layer':r['layer'],'status':'source_label_role_pending','scope':'Native text and leader contact proven; remote identity and connection are not inferred.'}
  used.add(n['node_id']);labels.add(t.dxf.handle);leaders.add(l.dxf.handle)
 if out['edges']!=graph['edges']:raise ValueError('Edges changed')
 return out,{'matched_nodes':len(used),'edges_unchanged':True,'hydraulic_change':False}
