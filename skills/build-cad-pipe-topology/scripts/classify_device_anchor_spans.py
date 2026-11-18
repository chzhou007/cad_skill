"""Explain selected unwitnessed graph spans without inferring physical ports."""
import argparse,hashlib,json,math
from pathlib import Path

def near(a,b,tol=.05):return math.dist(a[:2],b[:2])<=tol
def classify(graph,coverage,joints,policy,hashes):
 for key in ('source_sha256','graph_sha256','coverage_sha256','joints_sha256'):
  if policy.get(key)!=hashes.get(key):raise ValueError('stale '+key)
 if graph.get('metadata',{}).get('source_sha256',hashes['source_sha256'])!=hashes['source_sha256']:raise ValueError('graph source mismatch')
 for x in (coverage,joints):
  if x.get('source_sha256')!=hashes['source_sha256'] or x.get('graph_sha256')!=hashes['graph_sha256'] or x.get('hil_ready') is not False:raise ValueError('stale input evidence')
 if coverage.get('status')!='partial_source_coverage_not_physical_length' or joints.get('status')!='native_exploded_device_joint_geometry_unreviewed':raise ValueError('unsupported evidence')
 edge={x['edge_id']:x for x in graph['edges']};node={x['node_id']:x for x in graph['nodes']};cov={x['edge_id']:x for x in coverage['edges']};joint={x['edge_id']:x for x in joints['records']};selected=policy.get('edge_ids')
 if len(edge)!=len(graph['edges']) or len(node)!=len(graph['nodes']) or len(cov)!=len(coverage['edges']) or len(joint)!=len(joints['records']) or not isinstance(selected,list) or not selected or len(set(selected))!=len(selected):raise ValueError('duplicate or invalid scope')
 rows=[]
 for eid in selected:
  if eid not in edge or eid not in cov or eid not in joint:raise ValueError('missing selected evidence')
  e,c,j=edge[eid],cov[eid],joint[eid];owner=j['equipment_id'];system=j['system'];n=node.get(owner);chain=e.get('source_exploded_device_chain',{})
  if system not in ('supply','return') or e.get('system')!=system or c.get('system')!=system or not n or n.get('node_type') not in ('equipment','physical_equipment') or owner not in (e.get('start_node_id'),e.get('end_node_id')):raise ValueError('equipment or system mismatch')
  if j.get('status')!='native_chain_geometry_unreviewed' or j.get('physical_port_verified') is not False or j.get('physical_length')!='unknown' or chain.get('source_sha256')!=hashes['source_sha256']:raise ValueError('unsupported chain evidence')
  if any(chain.get(k)!=j.get(k) for k in ('joint_handle','inner_line_handle','outer_line_handle','circle_handle')):raise ValueError('chain identity mismatch')
  segments=c.get('segments',[]);missing=[s for s in segments if s.get('status')=='no_witness_in_scoped_search']
  if len(missing)!=1 or any(s.get('status') not in ('single_source_line_covers','no_witness_in_scoped_search') for s in segments):raise ValueError('ambiguous missing spans')
  gap=missing[0];a,b=gap['start'],gap['end'];anchor=[n['x'],n['y']];contact=j['joint_contacts'][1];inner=j['joint_contacts'][0]
  if not ((near(a,anchor) and near(b,contact)) or (near(b,anchor) and near(a,contact))):raise ValueError('unwitnessed segment is not equipment anchor to joint')
  paths=e.get('attribute_paths',[]);hits=sum((near(a,x) and near(b,y)) or (near(a,y) and near(b,x)) for path in paths for x,y in zip(path,path[1:]))
  if hits!=1 or not any(near(contact,p) for p in j['outer_line_endpoints']) or not any(near(inner,p) for p in j['inner_line_endpoints']) or not any(near(j['circle_center'],p) for p in j['inner_line_endpoints']):raise ValueError('source chain or path mismatch')
  rows.append({'edge_id':eid,'equipment_id':owner,'system':system,'unwitnessed_segment_index':gap['index'],'unwitnessed_segment_start':a,'unwitnessed_segment_end':b,'unwitnessed_drawing_span':gap['drawing_length'],'equipment_anchor':anchor,'joint_handle':j['joint_handle'],'inner_line_handle':j['inner_line_handle'],'outer_line_handle':j['outer_line_handle'],'circle_handle':j['circle_handle'],'source_inner_line_endpoints':j['inner_line_endpoints'],'status':'equipment_anchor_to_joint_is_unwitnessed_logical_connector','physical_port_verified':False,'physical_length':'unknown','connectivity_accepted':False})
 return {'status':'source_witnessed_chain_and_unwitnessed_anchor_connector','source_sha256':hashes['source_sha256'],'graph_sha256':hashes['graph_sha256'],'coverage_sha256':hashes['coverage_sha256'],'joints_sha256':hashes['joints_sha256'],'records':rows,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Source line and symbol contacts are evidence of a drawn chain, not proof of a physical equipment port.','The anchor connector is not a measured pipe and may overlap some source geometry; its physical length is unknown.','This classification does not establish cross-view identity or validate all other segments.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','coverage','joints','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));g=load(a.graph);hashes={'source_sha256':sha(a.source),'graph_sha256':sha(a.graph),'coverage_sha256':sha(a.coverage),'joints_sha256':sha(a.joints)};r=classify(g,load(a.coverage),load(a.joints),load(a.policy),hashes);r.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':r['status'],'records':len(r['records'])}))
if __name__=='__main__':main()
