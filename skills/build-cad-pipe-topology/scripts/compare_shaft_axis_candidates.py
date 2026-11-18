"""Enumerate scoped cross-floor shaft/axis candidates without mapping or lengths."""
import argparse,hashlib,json
from pathlib import Path


def compare(floor12,floor23,axis,diagnostic):
 if any(r.get('status')!='translation_hypothesis_not_confirmed' or r.get('graph_mutated') is not False or r.get('hil_ready') is not False for r in (floor12,floor23)):
  raise ValueError('floor registration must remain a candidate')
 if floor12['source_sha256'][1]!=floor23['source_sha256'][0] or floor12['input_sha256']['graph-b']!=floor23['input_sha256']['graph-a']:
  raise ValueError('middle floor evidence mismatch')
 if diagnostic.get('status')!='candidate_diagnostics_not_physical_length' or diagnostic.get('graph_mutated') is not False or diagnostic.get('hil_ready') is not False:
  raise ValueError('axis diagnostic must remain a candidate')
 edges={e['edge_id']:e for e in axis['edges']};diags={e['edge_id']:e for e in diagnostic['edges']}
 if len(edges)!=len(axis['edges']) or len(diags)!=len(diagnostic['edges']):raise ValueError('duplicate edge IDs')
 records=[]
 for first in floor12['same_system_riser_pairs']:
  if first.get('status')!='spatial_candidate_not_a_connection':raise ValueError('unexpected floor candidate state')
  for second in floor23['same_system_riser_pairs']:
   if second.get('status')!='spatial_candidate_not_a_connection':raise ValueError('unexpected floor candidate state')
   if first['system']!=second['system'] or first['target_node']!=second['source_node']:continue
   system=first['system'];matches=[]
   for x in diagnostic['edges']:
    if (x.get('system'),x.get('floor_start'),x.get('floor_end'))!=(system,1,2):continue
    first_edge=edges.get(x['edge_id'])
    if not first_edge or first_edge.get('system')!=system:raise ValueError('axis edge mismatch')
    for y in diagnostic['edges']:
     if (y.get('system'),y.get('floor_start'),y.get('floor_end'))!=(system,2,3):continue
     second_edge=edges.get(y['edge_id'])
     if not second_edge or second_edge.get('system')!=system:raise ValueError('axis edge mismatch')
     shared={first_edge.get('start_node_id'),first_edge.get('end_node_id')} & {second_edge.get('start_node_id'),second_edge.get('end_node_id')}
     shared.discard(None)
     if len(shared)!=1:continue
     if not any(s.get('drawing_direction')=='vertical' and s.get('source_handle') for s in x.get('segments',[])):continue
     if not any(s.get('drawing_direction')=='vertical' and s.get('source_handle') for s in y.get('segments',[])):continue
     matches.append({'axis_1_to_2_edge':x['edge_id'],'axis_2_to_3_edge':y['edge_id'],'shared_node':next(iter(shared)),
                     'axis_vertical_source_handles_1_to_2':[s['source_handle'] for s in x['segments'] if s.get('drawing_direction')=='vertical'],
                     'axis_vertical_source_handles_2_to_3':[s['source_handle'] for s in y['segments'] if s.get('drawing_direction')=='vertical'],
                     'status':'same_system_floor_geometry_candidate_not_mapping'})
   records.append({'system':system,'plan_floor_nodes':[first['source_node'],first['target_node'],second['target_node']],
                   'axis_chain_candidates':matches,'mapping_ready':False,'physical_length':'unknown'})
 if not records:raise ValueError('no continuous candidate floor registration')
 return {'status':'shaft_axis_candidate_inventory_not_mapping','records':records,'graph_mutated':False,'mapping_ready':False,'human_accepted':False,'hil_ready':False,
         'limitations':['Floor registrations are selected spatial hypotheses, not confirmed pipe identity or connectivity.',
                        'Axis candidates require selected diagnostic edges and a shared graph node; unselected or unsupported source paths are not inventoried.',
                        'Same system and floor sequence do not prove shaft membership or 3D identity; datum drawing spans are not physical lengths.']}


def main():
 p=argparse.ArgumentParser()
 for k in ('floor12','floor23','axis-graph','axis-diagnostic','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'))
 f12,f23,g,d=map(load,(a.floor12,a.floor23,a.axis_graph,a.axis_diagnostic))
 if d.get('graph_sha256')!=sha(a.axis_graph):raise ValueError('stale axis diagnostic')
 result=compare(f12,f23,g,d);result.update(input_sha256={k:sha(getattr(a,k)) for k in ('floor12','floor23','axis_graph','axis_diagnostic')},script_sha256=sha(Path(__file__)))
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':result['status'],'records':len(result['records'])}))
if __name__=='__main__':main()
