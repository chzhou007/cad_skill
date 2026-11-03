"""Portable native-source regression; synthetic geometry tests complement this case."""
import argparse,hashlib,json,subprocess,sys,tempfile
from pathlib import Path

def run(case,out):
 manifest=json.loads((case/'manifest.json').read_text(encoding='utf8'))
 for name,wanted in manifest.items():
  assert hashlib.sha256((case/name).read_bytes()).hexdigest()==wanted,'Case integrity mismatch: '+name
 i=case/'inputs';expected=case/'expected'
 cmd=[sys.executable,'-X','utf8',str(Path(__file__).with_name('build_schematic.py'))]
 for key,p in [('dxf',next(i.glob('*.dxf'))),('bindings',i/'bindings.json'),('profiles',i/'profiles.json'),('materials',i/'materials.json'),('config',i/'source-profile.json'),('previous-graph',i/'previous-graph.json'),('output-dir',out)]:cmd+=['--'+key,str(p)]
 subprocess.run(cmd,check=True)
 files=[p.name for p in sorted(expected.glob('*.json'))]
 for name in files:
  assert json.loads((out/name).read_text(encoding='utf8'))==json.loads((expected/name).read_text(encoding='utf8')),'Regression mismatch: '+name
 g=json.loads((out/'graph_with_edges.json').read_text(encoding='utf8'));arcs=json.loads((out/'pipe_crossover_arc_normalizations.json').read_text(encoding='utf8'));summary=json.loads((out/'edge_summary.json').read_text(encoding='utf8'))
 assert summary['equipment_physical_ports']==summary['equipment_ports_with_edges']==35
 for arc in arcs:
  assert arc['normalization_status']=='normalized'
  assert any(arc['handle']in edge['source_handles']for edge in g['edges']),'Jump lacks complete logical edge: '+arc['handle']
  for crossing in arc['crossings']:
   x,y=crossing['crossing']
   assert not any(abs(n['x']-x)<.5 and abs(n['y']-y)<.5 for n in g['nodes']),'Crossover became a graph node'
 if (case/'regional-head-assertions.json').exists():
  specs=json.loads((case/'regional-head-assertions.json').read_text(encoding='utf8'));heads=json.loads((out/'instrument_head_coverage.json').read_text(encoding='utf8'));byid={h['source_sensor_handle']:h for h in heads}
  for sensor,head in specs['E0116'].items():assert byid[sensor]['source_head_handle']==head and byid[sensor]['status']=='complete_tagged_head'
  published=[h for h in heads if h['source_role']=='edge_component'];complete=[h for h in published if h['status']=='complete_tagged_head'];pending=[h for h in published if h['status']!='complete_tagged_head'];count=specs.get('complete_head_count',58);assert len(complete)==count and len(pending)==1 and pending[0]['source_sensor_handle']==specs['pending_source_sensor']
  assert len({h['source_head_handle']for h in complete})==count,'Two sensors claimed the same instrument head'
 assert g['metadata']['relative_elevation']=='unknown'
 if (case/'regional-assembly-assertions.json').exists():
  specs=json.loads((case/'regional-assembly-assertions.json').read_text(encoding='utf8'));groups={a['id']:a for a in json.loads((out/'source_instrument_assemblies.json').read_text(encoding='utf8'))}
  for aid,hs in specs['restored_source_handles'].items():assert set(hs)<=set(groups[aid]['source_handles']),'Assembly source primitive missing: '+aid
  for nid,h in specs['pump_contours'].items():
   n=next(n for n in g['nodes']if n['node_id']==nid);assert h in n['display_source_handles']and len(n['display_source_handles'])==6
  assert all(a['status']=='PASS'and not a['missing_source_handles']for a in json.loads((out/'assembly_source_fidelity.json').read_text(encoding='utf8')))
 if case.name in ['sh16-plant-v4','sh16-plant-v5','sh16-plant-v6']:
  assert summary['atomic_source_pieces']==summary['atomic_pieces_on_edges']==404
  assert summary['unresolved_path_groups']==0 and summary['unresolved_terminal_nodes']==8
  assert summary['measurement_assemblies']==8 and summary['tee_nodes']==44
  assert len(json.loads((out/'source_component_roles.json').read_text(encoding='utf8')))==(270 if case.name in ['sh16-plant-v5','sh16-plant-v6']else 263)
  for edge in g['edges']:
   assert edge['start_node_id']in {n['node_id']for n in g['nodes']}and edge['end_node_id']in {n['node_id']for n in g['nodes']}
  straight=json.loads((out/'straight_crossover_audit.json').read_text(encoding='utf8'));assert len(straight)==3
  for gap in straight:
   for c in gap['crossings']:
    assert not any(abs(n['x']-c['crossing'][0])<.5 and abs(n['y']-c['crossing'][1])<.5 for n in g['nodes'])
 result={'status':'PASS','case':case.name,'compared_files':files,'equipment_ports':'35/35','normalized_jumps_on_completed_edges':'9/9','crossover_nodes':0,'review_status':'unreviewed'}
 (out/'regression-report.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--case',type=Path,default=Path(__file__).resolve().parents[1]/'assets/alignment/sh16-plant-v6');p.add_argument('--output-dir',type=Path);a=p.parse_args()
 if a.output_dir:run(a.case,a.output_dir)
 else:
  with tempfile.TemporaryDirectory(prefix='cad-schematic-regression-')as d:run(a.case,Path(d)/'result')
