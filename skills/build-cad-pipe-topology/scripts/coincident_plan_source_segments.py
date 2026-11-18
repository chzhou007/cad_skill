"""Relate unreferenced coincident source LINEs to graph paths as candidates only."""
import argparse,hashlib,json,math
from pathlib import Path
from duplicate_native_main_diagnostics import same_line
from partial_native_line_coverage import intervals
from source_readability import read_source

def compare(doc,graph,inventory,source_hash,graph_hash,tol=.05):
 if (graph.get('metadata',{}).get('source_sha256')!=source_hash or inventory.get('source_sha256')!=source_hash or inventory.get('graph_sha256')!=graph_hash or inventory.get('status')!='final_plan_line_handle_inventory_not_acceptance' or inventory.get('graph_mutated') is not False or inventory.get('human_accepted') is not False or inventory.get('hil_ready') is not False):raise ValueError('stale line inventory')
 if not math.isfinite(tol) or tol<=0:raise ValueError('invalid tolerance')
 if inventory.get('normalization_tolerance')!=tol:raise ValueError('inventory tolerance mismatch')
 edges={e['edge_id']:e for e in graph['edges']}
 if len(edges)!=len(graph['edges']):raise ValueError('duplicate graph edges')
 rows=[]
 for item in inventory['records']:
  if item.get('status')!='coincident_referenced_source_candidate':continue
  if item.get('direct_edge_ids')!=[] or any(item.get('source_handle') in e.get('source_handles',[]) for e in graph['edges']):raise ValueError('candidate already referenced')
  line=doc.entitydb.get(item.get('source_handle'));matches=item.get('coincident_referenced_sources')
  if not line or line.dxftype()!='LINE' or line not in doc.modelspace() or line.dxf.layer!=item.get('source_layer') or list(line.dxf.start)!=item.get('start') or list(line.dxf.end)!=item.get('end') or not isinstance(matches,list) or not matches:raise ValueError('source line candidate mismatch')
  related=[]
  for m in matches:
   other=doc.entitydb.get(m.get('source_handle'));edge_ids=m.get('edge_ids')
   if not other or other not in doc.modelspace() or not same_line(line,other,tol) or not isinstance(edge_ids,list) or not edge_ids or len(set(edge_ids))!=len(edge_ids):raise ValueError('coincident source mismatch')
   actual=sorted(e['edge_id'] for e in graph['edges'] if other.dxf.handle in e.get('source_handles',[]))
   if sorted(edge_ids)!=actual:raise ValueError('coincident edge references mismatch')
   for eid in edge_ids:
    e=edges[eid]
    if e.get('system')!=item.get('system'):raise ValueError('coincident system mismatch')
    spans=[]
    for pi,path in enumerate(e.get('attribute_paths',[])):
     for si,(a,b) in enumerate(zip(path,path[1:])):
      if math.dist(a,b)<=tol:continue
      pieces=intervals(a,b,[(line.dxf.handle,(line.dxf.start.x,line.dxf.start.y),(line.dxf.end.x,line.dxf.end.y))],tol)
      for part in pieces:
       if part['status']=='unique_source_line':spans.append({'path_index':pi,'segment_index':si,'start_distance':part['start_distance'],'end_distance':part['end_distance'],'drawing_overlap_length':part['drawing_length']})
    related.append({'edge_id':eid,'referenced_source_handle':other.dxf.handle,'overlap_spans':spans,'status':'geometric_overlap_candidate_not_ownership' if spans else 'source_handle_referenced_without_scoped_overlap'})
  rows.append({'unreferenced_source_handle':line.dxf.handle,'system':item['system'],'related_edges':related,'physical_identity_resolved':False,'status':'coincident_source_line_identity_unresolved'})
 return {'status':'coincident_source_segments_not_physical_identity','source_sha256':source_hash,'graph_sha256':graph_hash,'records':rows,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Exact same-layer 3D source LINE candidates are scoped by the supplied inventory; graph paths are compared in drawing XY.','Coincident source lines and graph overlap do not establish one versus multiple physical pipes, ownership, connectivity or physical length.','A missing overlap does not prove absence of source coverage in other geometry types.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','inventory','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));inv=load(a.inventory);r=compare(doc,load(a.graph),inv,proof['source_sha256'],h(a.graph),inv['normalization_tolerance']);r.update(inventory_sha256=h(a.inventory),script_sha256=h(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'source_candidates':len(r['records'])}))
if __name__=='__main__':main()
