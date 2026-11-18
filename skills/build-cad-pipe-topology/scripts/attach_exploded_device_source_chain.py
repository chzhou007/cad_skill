"""Attach rechecked exploded source chains without changing graph connectivity."""
import argparse,copy,csv,hashlib,json
from pathlib import Path
from source_readability import read_source
from native_exploded_device_joint_evidence import collect

def attach(doc,graph,inventory,policy,hashes,evidence,evidence_sha):
 fresh=collect(doc,graph,inventory,policy,hashes)
 if any(evidence.get(k)!=hashes[k] for k in ('source_sha256','graph_sha256','inventory_sha256')) or evidence.get('records')!=fresh['records'] or evidence.get('status')!=fresh['status'] or evidence.get('hil_ready') is not False:raise ValueError('device source chain evidence stale or unreproducible')
 g=copy.deepcopy(graph);edges={e['edge_id']:e for e in g['edges']}
 for r in fresh['records']:
  edge=edges[r['edge_id']]
  if edge.get('source_exploded_device_chain') is not None:raise ValueError('source chain already attached')
  if edge.get('path_length_complete') is not False or edge.get('physical_length')!='unknown':raise ValueError('unknown physical length protection required')
  edge['source_exploded_device_chain']={'source_sha256':hashes['source_sha256'],'input_graph_sha256':hashes['graph_sha256'],'evidence_sha256':evidence_sha,'joint_handle':r['joint_handle'],'joint_component_name':r['joint_component_name'],'inner_line_handle':r['inner_line_handle'],'inner_line_endpoints':r['inner_line_endpoints'],'outer_line_handle':r['outer_line_handle'],'circle_handle':r['circle_handle'],'joint_contacts':r['joint_contacts'],'physical_port_verified':False,'physical_length':'unknown','additional_line_length_not_added':True,'status':'native_chain_geometry_unreviewed'}
 g.setdefault('metadata',{}).update(hil_ready=False,review_status='unreviewed_after_source_evidence_change')
 return g

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','inventory','policy','evidence','output'):p.add_argument('--'+k,required=True,type=Path)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 if a.output.exists():raise FileExistsError(a.output)
 doc,proof=read_source(a.source);g=json.loads(a.graph.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'));ev=json.loads(a.evidence.read_text(encoding='utf8'))
 with a.inventory.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 hashes={'source_sha256':proof['source_sha256'],'graph_sha256':sha(a.graph),'inventory_sha256':sha(a.inventory)};result=attach(doc,g,rows,policy,hashes,ev,sha(a.evidence));a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'output_graph_sha256':sha(a.output),'attached':len(ev['records']),'hil_ready':False}))
if __name__=='__main__':main()
