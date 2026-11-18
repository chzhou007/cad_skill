"""Compare scoped sub-tolerance source LINEs to native circles and graph nodes."""
import argparse,hashlib,json,math
from pathlib import Path
from source_readability import read_source

def compare(doc,graph,inventory,source_hash,graph_hash,tol=.05):
 if (graph.get('metadata',{}).get('source_sha256')!=source_hash or inventory.get('source_sha256')!=source_hash or inventory.get('graph_sha256')!=graph_hash or inventory.get('status')!='final_plan_line_handle_inventory_not_acceptance' or inventory.get('graph_mutated') is not False or inventory.get('human_accepted') is not False or inventory.get('hil_ready') is not False):raise ValueError('stale source inventory')
 if not math.isfinite(tol) or tol<=0:raise ValueError('invalid tolerance')
 rows=[];circles=list(doc.modelspace().query('CIRCLE'));edges=graph['edges']
 for item in inventory['records']:
  if item.get('status')!='shorter_than_normalization_tolerance_unclassified':continue
  line=doc.entitydb.get(item.get('source_handle'))
  if not line or line.dxftype()!='LINE' or line not in doc.modelspace() or line.dxf.layer!=item.get('source_layer') or list(line.dxf.start)!=item.get('start') or list(line.dxf.end)!=item.get('end'):raise ValueError('source micro line mismatch')
  a,b=line.dxf.start,line.dxf.end;length=math.dist(a,b)
  if length>tol or abs(length-item.get('drawing_length',-1))>1e-8:raise ValueError('micro line length mismatch')
  center=((a.x+b.x)/2,(a.y+b.y)/2);candidates=[]
  for c in circles:
   if c.dxf.layer!=line.dxf.layer:continue
   delta=math.dist(center,(c.dxf.center.x,c.dxf.center.y))
   if delta>tol:continue
   nodes=[]
   for node in graph['nodes']:
    if math.dist(center,(node['x'],node['y']))>tol:continue
    incident=[{'edge_id':e['edge_id'],'system':e.get('system')} for e in edges if node['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))]
    edge_evidence=[]
    for e in edges:
     if node['node_id'] not in (e.get('start_node_id'),e.get('end_node_id')):continue
     evidence=e.get('source_circle_connection')
     if isinstance(evidence,dict) and evidence.get('circle_handle')==c.dxf.handle:edge_evidence.append({'edge_id':e['edge_id'],'field':'source_circle_connection','expert_issue':evidence.get('expert_issue')})
    nodes.append({'node_id':node['node_id'],'node_type':node.get('node_type'),'circle_handle_in_node_source':c.dxf.handle in node.get('source_handles',[]),'incident_edges':incident,'incident_edge_circle_evidence':edge_evidence})
   candidates.append({'circle_handle':c.dxf.handle,'radius':float(c.dxf.radius),'center_distance':delta,'graph_nodes':nodes})
  rows.append({'source_handle':item['source_handle'],'system':item['system'],'drawing_length':length,'same_layer_center_circles':candidates,'status':'micro_line_source_context_not_classified'})
 return {'status':'micro_line_circle_context_not_classification','source_sha256':source_hash,'graph_sha256':graph_hash,'records':rows,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Only same-layer modelspace circles centered within tolerance are checked; other symbol forms and nested content are excluded.','A circle or graph node at the same location does not prove the micro line is nonphysical, prove connectivity, or authorize removal.','Graph node source handles and incident edges are reported separately from source circle identity.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','inventory','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));r=compare(doc,load(a.graph),load(a.inventory),proof['source_sha256'],h(a.graph));r.update(inventory_sha256=h(a.inventory),script_sha256=h(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'records':len(r['records'])}))
if __name__=='__main__':main()
