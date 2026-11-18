"""Group repeated micro-line source evidence without resolving any blocker."""
import argparse,collections,hashlib,json,math
from pathlib import Path
from micro_line_circle_evidence import compare
from source_readability import read_source

def group(doc,graph,inventory,source_hash,graph_hash):
 screen=compare(doc,graph,inventory,source_hash,graph_hash)
 groups=collections.defaultdict(list);other=[]
 for row in screen['records']:
  circles=row['same_layer_center_circles'];line=doc.entitydb.get(row['source_handle'])
  if len(circles)!=1 or len(circles[0]['graph_nodes'])!=1:
   other.append(row['source_handle']);continue
  circle_info=circles[0];node=circle_info['graph_nodes'][0];circle=doc.entitydb.get(circle_info['circle_handle'])
  if node['node_type']!='tee' or len(node['incident_edges'])!=3 or any(x['system']!=row['system'] for x in node['incident_edges']):
   other.append(row['source_handle']);continue
  a=tuple(line.dxf.start);b=tuple(line.dxf.end);center=tuple(circle.dxf.center)
  if min(math.dist(a,center),math.dist(b,center))>1e-5:
   other.append(row['source_handle']);continue
  # 5 decimal places matches the strict endpoint tolerance; no inferred rotation.
  key=(row['system'],line.dxf.layer,round(circle.dxf.radius,5),*(round(b[i]-a[i],5) for i in range(3)),*(round(a[i]-center[i],5) for i in range(3)))
  groups[key].append({'source_handle':row['source_handle'],'circle_handle':circle_info['circle_handle'],'node_id':node['node_id'],'incident_edge_ids':sorted(x['edge_id'] for x in node['incident_edges'])})
 families=[{'system':k[0],'source_layer':k[1],'circle_radius':k[2],'line_vector_3d':list(k[3:6]),'start_offset_3d':list(k[6:9]),'members':sorted(v,key=lambda x:x['source_handle']),'status':'same_source_geometry_unclassified'} for k,v in sorted(groups.items())]
 return {'status':'micro_line_families_not_classification','source_sha256':source_hash,'graph_sha256':graph_hash,'families':families,'ungrouped_source_handles':sorted(other),'source_handle_count':len(screen['records']),'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Grouping is based on bounded same-system native geometry and graph incidence; it does not identify physical function, authorize deletion, or confirm connectivity.','Every source line remains a separate unresolved source-comparison item.']}

def main():
 p=argparse.ArgumentParser()
 for name in ('source','graph','inventory','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();h=lambda x:hashlib.sha256(x.read_bytes()).hexdigest();doc,proof=read_source(a.source);load=lambda x:json.loads(x.read_text(encoding='utf8'))
 result=group(doc,load(a.graph),load(a.inventory),proof['source_sha256'],h(a.graph));result.update(inventory_sha256=h(a.inventory),script_sha256=h(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'families':len(result['families']),'members':result['source_handle_count'],'ungrouped':len(result['ungrouped_source_handles'])}))
if __name__=='__main__':main()
