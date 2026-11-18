import hashlib,json,tempfile,unittest
from pathlib import Path
from source_comparison_gate import final_plan_line_blockers
class PlanLineGateTest(unittest.TestCase):
 def test_required_stage_and_coincident_evidence_are_bound(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);r=root/'reports';r.mkdir();g={'edges':[{'edge_id':'E','system':'supply','source_handles':['A']}]}
   e={'status':'final_plan_line_handle_inventory_not_acceptance','source_sha256':'S','graph_sha256':'G','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':[{'source_handle':'B','system':'supply','status':'coincident_referenced_source_candidate','direct_edge_ids':[],'physical_identity_resolved':False}]}
   p=r/'final-plan-line-inventory.json';p.write_text(json.dumps(e),encoding='utf8');h=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
   c={'status':'coincident_source_segments_not_physical_identity','source_sha256':'S','graph_sha256':'G','inventory_sha256':h(p),'graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':[{'unreferenced_source_handle':'B','physical_identity_resolved':False}]};cp=r/'final-coincident-source-segments.json';cp.write_text(json.dumps(c),encoding='utf8')
   s={'status':e['status'],'source_sha256':'S','graph_sha256':'G','hil_ready':False,'evidence_sha256':h(p),'coincident_evidence_sha256':h(cp),'candidate_count':1};sp=r/'final-plan-line-stage.json';sp.write_text(json.dumps(s),encoding='utf8')
   d={'status':'required_plan_line_screen','source_sha256':'S','graph_sha256':'G','policy_map_sha256':'a'*64,'evidence_path':'reports/final-plan-line-inventory.json','stage_path':'reports/final-plan-line-stage.json','coincident_path':'reports/final-coincident-source-segments.json','hil_ready':False};(root/'plan-line-required.json').write_text(json.dumps(d),encoding='utf8')
   self.assertEqual(len(final_plan_line_blockers(root,'G','S',g)),1)
   c['records']=[];cp.write_text(json.dumps(c),encoding='utf8');s['coincident_evidence_sha256']=h(cp);sp.write_text(json.dumps(s),encoding='utf8')
   with self.assertRaisesRegex(ValueError,'candidate mismatch'):final_plan_line_blockers(root,'G','S',g)
   p.unlink();sp.unlink();cp.unlink()
   with self.assertRaisesRegex(ValueError,'stage missing'):final_plan_line_blockers(root,'G','S',g)
 def test_retains_unclassified_and_rejects_stale(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);r=root/'reports';r.mkdir();graph={'edges':[{'edge_id':'E','system':'supply','source_handles':['A']}]};rows=[{'source_handle':'A','system':'supply','status':'source_handle_referenced','direct_edge_ids':['E'],'physical_identity_resolved':False},{'source_handle':'B','system':'supply','status':'coincident_referenced_source_candidate','direct_edge_ids':[],'coincident_referenced_sources':[{'source_handle':'A','edge_ids':['E']}],'physical_identity_resolved':False}];e={'status':'final_plan_line_handle_inventory_not_acceptance','source_sha256':'S','graph_sha256':'G','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':rows};p=r/'final-plan-line-inventory.json';p.write_text(json.dumps(e),encoding='utf8');s={'status':e['status'],'source_sha256':'S','graph_sha256':'G','hil_ready':False,'evidence_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'candidate_count':1};(r/'final-plan-line-stage.json').write_text(json.dumps(s),encoding='utf8');self.assertEqual(final_plan_line_blockers(root,'G','S',graph)[0]['source_handle'],'B')
   with self.assertRaises(ValueError):final_plan_line_blockers(root,'old','S',graph)
   rows[0]['direct_edge_ids']=[];p.write_text(json.dumps(e),encoding='utf8');s['evidence_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();(r/'final-plan-line-stage.json').write_text(json.dumps(s),encoding='utf8')
   with self.assertRaises(ValueError):final_plan_line_blockers(root,'G','S',graph)
 def test_micro_family_groups_without_removing_source_blockers(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);r=root/'reports';r.mkdir();h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
   graph={'nodes':[{'node_id':'T','node_type':'tee'}],'edges':[{'edge_id':f'E{i}','start_node_id':'T','end_node_id':f'N{i}','system':'supply','source_handles':[]} for i in range(3)]}
   rows=[{'source_handle':x,'system':'supply','status':'shorter_than_normalization_tolerance_unclassified','direct_edge_ids':[],'physical_identity_resolved':False} for x in ('A','B')]
   e={'status':'final_plan_line_handle_inventory_not_acceptance','source_sha256':'S','graph_sha256':'G','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':rows};p=r/'final-plan-line-inventory.json';p.write_text(json.dumps(e),encoding='utf8')
   family={'status':'micro_line_families_not_classification','source_sha256':'S','graph_sha256':'G','inventory_sha256':h(p),'graph_mutated':False,'human_accepted':False,'hil_ready':False,'source_handle_count':2,'ungrouped_source_handles':[],'families':[{'status':'same_source_geometry_unclassified','system':'supply','members':[{'source_handle':x,'circle_handle':'C','node_id':'T','incident_edge_ids':['E0','E1','E2']} for x in ('A','B')]}]};fp=r/'final-micro-line-families.json';fp.write_text(json.dumps(family),encoding='utf8')
   stage={'status':e['status'],'source_sha256':'S','graph_sha256':'G','hil_ready':False,'evidence_sha256':h(p),'micro_family_evidence_sha256':h(fp),'candidate_count':2};sp=r/'final-plan-line-stage.json';sp.write_text(json.dumps(stage),encoding='utf8')
   result=final_plan_line_blockers(root,'G','S',graph);self.assertEqual(len(result),2);self.assertEqual({x['source_geometry_family'] for x in result},{'MICRO-001'})
   family['families'][0]['members'][0]['incident_edge_ids']=['E0'];fp.write_text(json.dumps(family),encoding='utf8');stage['micro_family_evidence_sha256']=h(fp);sp.write_text(json.dumps(stage),encoding='utf8')
   with self.assertRaisesRegex(ValueError,'family member'):final_plan_line_blockers(root,'G','S',graph)
if __name__=='__main__':unittest.main()
