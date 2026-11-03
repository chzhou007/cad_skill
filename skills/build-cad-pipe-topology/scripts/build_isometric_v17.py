"""Current isometric adapter; historical alignment implementation stays immutable."""
import sys,json,dataclasses,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'legacy_v17'))
import analyze_graph as geometry
import build_edges as edges
import pipe_geometry as pg
from topology_normalization import trim_elbow_overshoots,snap_near_junction_endpoints

def main():
 args=list(sys.argv[1:]);index=args.index('--previous-graph');prior=Path(args[index+1]);del args[index:index+2];edges.PREVIOUS_GRAPH=json.loads(prior.read_text(encoding='utf8'))
 index=args.index('--normalization-config');cfg=json.loads(Path(args[index+1]).read_text(encoding='utf8'));del args[index:index+2]
 geometry.get_system_layers=lambda doc:cfg['system_layers']
 edges.equipment_graph.tee_id_lookup=edges.node_ids
 owner_audit=[];old_matches=edges.equipment_graph.make_provisional_matches
 def stable_owners(owned,tees):
  matches=old_matches(owned,tees)
  if not cfg.get('previous_source_sha256'):return matches
  source=Path(args[args.index('--dxf')+1])
  if hashlib.sha256(source.read_bytes()).hexdigest()!=cfg['previous_source_sha256']:raise ValueError('Prior ownership requires identical source CAD identity')
  ids=edges.node_ids(tees);byid={ids[(t.system,geometry.point_key((t.x,t.y),geometry.ENDPOINT_QUANTUM))]:t for t in tees};result=[]
  for m in matches:
   prior=[e for e in edges.PREVIOUS_GRAPH['edges']if e['system']==m.system and m.equipment.label in [e['start_node_id'],e['end_node_id']]]
   if len(prior)==1:
    e=prior[0];oldid=e['end_node_id']if e['start_node_id']==m.equipment.label else e['start_node_id'];distance=min(pg.segdist((m.tee.x,m.tee.y),a,b)for path in e['attribute_paths']for a,b in zip(path,path[1:]))
    if m.tee_id!=oldid and distance>cfg.get('near_junction',{}).get('maximum_gap',.5)and oldid in byid:
     owner_audit.append(dict(equipment=m.equipment.label,system=m.system,rejected_target=m.tee_id,preserved_target=oldid,distance_to_prior_source_path=distance,rule='reject_new_owner_binding_outside_unchanged_source_path'))
     m=dataclasses.replace(m,tee=byid[oldid],tee_id=oldid,candidate_selection='source_path_verified_prior_owner_preserved')
   result.append(m)
  return result
 edges.equipment_graph.make_provisional_matches=stable_owners
 oldtrim=geometry.trim_short_dangling_overshoots;audit=[];snaps=[];source_index={};oldcollect=geometry.collect_pipe_segments
 def sourcekey(a,b):return tuple(sorted([tuple(round(v,5)for v in a),tuple(round(v,5)for v in b)]))
 def collect(doc):
  for top in doc.modelspace():
   for e in geometry.recursive_entities(top):
    if e.dxftype()=='LINE'and e.dxf.layer in cfg['system_layers']:
     k=(cfg['system_layers'][e.dxf.layer],sourcekey(tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2]));source_index.setdefault(k,set()).add(top.dxf.handle)
  return oldcollect(doc)
 geometry.collect_pipe_segments=collect
 def trim(ss):
  ss,legacy=oldtrim(ss);pg.set_tolerance(geometry.POINT_TOLERANCE);rows=[dict(a=s.start,b=s.end,system=s.system,handle='SOURCE-SEGMENT-'+str(i),source_handles=sorted(source_index.get((s.system,sourcekey(s.start,s.end)),[])),source_handle_scope='top_level_owner')for i,s in enumerate(ss)]
  rows,records=trim_elbow_overshoots(rows,cfg['elbow_overshoot']);audit.extend(records);rows,records=snap_near_junction_endpoints(rows,cfg.get('near_junction'));snaps.extend(records);return [geometry.Segment(s['system'],tuple(s['a']),tuple(s['b']))for s in rows],legacy
 geometry.trim_short_dangling_overshoots=trim;sys.argv=[sys.argv[0]]+args;edges.main();out=Path(args[args.index('--output-dir')+1]);(out/'normalization_audit.json').write_text(json.dumps({'elbow_overshoots':audit,'junction_snaps':snaps,'config':cfg},indent=2),encoding='utf8')
 g=json.loads((out/'graph_with_edges.json').read_text(encoding='utf8'));old=edges.PREVIOUS_GRAPH
 mapping={'retired_nodes':[n['node_id']for n in old['nodes']if n['node_id']not in {n['node_id']for n in g['nodes']}],'retired_edges':[e['edge_id']for e in old['edges']if e['edge_id']not in {e['edge_id']for e in g['edges']}],'merged_edges':[{'retained_edge_id':e['edge_id'],'old_start':next(x['start_node_id']for x in old['edges']if x['edge_id']==e['edge_id']),'new_start':e['start_node_id'],'end':e['end_node_id']}for e in g['edges']if any(x['edge_id']==e['edge_id']and{x['start_node_id'],x['end_node_id']}!={e['start_node_id'],e['end_node_id']}for x in old['edges'])]}
 (out/'id_mapping.json').write_text(json.dumps(mapping,indent=2),encoding='utf8');print('MAPPING',json.dumps(mapping))
if __name__=='__main__':main()
