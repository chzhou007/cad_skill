import hashlib,json,tempfile,unittest
from pathlib import Path
from source_comparison_gate import missing_gap_joint_blockers


class MissingGapJointGate(unittest.TestCase):
 def test_candidates_block_and_stale_evidence_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);e={'status':'missing_source_joints_candidate_screen','graph_mutated':False,'hil_ready':False,'source_sha256':'S','graph_sha256':'I','coverage_sha256':'C','inventory_sha256':'V','policy_sha256':'P','script_sha256':'T','records':[{'insert_handle':'H','edge_id':'E','system':'supply','candidate_type':'金属软接','status':'source_calibrated_joint_unassigned_pending_review','physical_length':'unknown','human_accepted':False}]}
   f=root/'missing_gap_joint_candidates_final.json';f.write_text(json.dumps(e,ensure_ascii=False),encoding='utf8')
   s={'status':'missing_joint_candidates_pending_source_comparison','final_graph_sha256':'G','input_graph_sha256':'I','source_sha256':'S','coverage_sha256':'C','inventory_sha256':'V','policy_sha256':'P','script_sha256':'T','evidence_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'graph_mutated':False,'human_accepted':False,'hil_ready':False,'candidate_count':1,'candidate_handles':['H']}
   (root/'missing_gap_joint_candidates_stage.json').write_text(json.dumps(s),encoding='utf8');graph={'metadata':{'source_sha256':'S'},'edges':[{'edge_id':'E','system':'supply'}]}
   self.assertEqual(len(missing_gap_joint_blockers(root,'G',graph)),1)
   inv={'status':'direct_calibrated_joint_inventory_not_ownership_acceptance','source_sha256':'S','inventory_sha256':'V','policy_sha256':'P','script_sha256':'Z','total_source_instances':2,'counts':{'unassigned_source_instance':2},'records':[{'source_handle':'H','status':'unassigned_source_instance'},{'source_handle':'H2','status':'unassigned_source_instance'}]}
   invpath=root/'calibrated_joint_inventory_final.json';invpath.write_text(json.dumps(inv),encoding='utf8');s['joint_inventory_evidence_sha256']=hashlib.sha256(invpath.read_bytes()).hexdigest();s['joint_inventory_script_sha256']='Z';(root/'missing_gap_joint_candidates_stage.json').write_text(json.dumps(s),encoding='utf8')
   self.assertEqual(len(missing_gap_joint_blockers(root,'G',graph)),2)
   inv.update(block_name='J',same_fingerprint_block_definitions=['J','J2'],nested_definition_references=[{'parent_block':'P','insert_handle':'N','referenced_block':'J2'}]);invpath.write_text(json.dumps(inv),encoding='utf8');s['joint_inventory_evidence_sha256']=hashlib.sha256(invpath.read_bytes()).hexdigest();(root/'missing_gap_joint_candidates_stage.json').write_text(json.dumps(s),encoding='utf8')
   self.assertEqual(len(missing_gap_joint_blockers(root,'G',graph)),4)
   inv.pop('block_name');inv.pop('same_fingerprint_block_definitions');inv.pop('nested_definition_references');invpath.write_text(json.dumps(inv),encoding='utf8');s['joint_inventory_evidence_sha256']=hashlib.sha256(invpath.read_bytes()).hexdigest();(root/'missing_gap_joint_candidates_stage.json').write_text(json.dumps(s),encoding='utf8')
   rec={'status':'joint_inventory_contacts_bound_to_final_graph_not_acceptance','source_sha256':'S','inventory_sha256':'V','final_graph_sha256':'G','inventory_evidence_sha256':s['joint_inventory_evidence_sha256'],'script_sha256':'Q','human_accepted':False,'records':[{'source_handle':'H','status':'unassigned_source_instance','human_accepted':False},{'source_handle':'H2','status':'unassigned_source_instance','human_accepted':False}]}
   recpath=root/'calibrated_joint_contact_reconciliation_final.json';recpath.write_text(json.dumps(rec),encoding='utf8');s['joint_contact_reconciliation_sha256']=hashlib.sha256(recpath.read_bytes()).hexdigest();s['joint_contact_reconciliation_script_sha256']='Q';(root/'missing_gap_joint_candidates_stage.json').write_text(json.dumps(s),encoding='utf8');self.assertEqual(len(missing_gap_joint_blockers(root,'G',graph)),2)
   graph['metadata']={}
   with self.assertRaises(ValueError):missing_gap_joint_blockers(root,'G',graph)
   receipt=root/'rebuild-receipt.json';receipt.write_text(json.dumps({'final_graph_sha256':'G','inputs':{'dxf':'S'}}),encoding='utf8')
   self.assertEqual(len(missing_gap_joint_blockers(root,'G',graph)),2)
   receipt.write_text(json.dumps({'final_graph_sha256':'different','inputs':{'dxf':'S'}}),encoding='utf8')
   with self.assertRaises(ValueError):missing_gap_joint_blockers(root,'G',graph)
   with self.assertRaises(ValueError):missing_gap_joint_blockers(root,'changed',graph)
   f.write_text('{}',encoding='utf8')
   with self.assertRaises(ValueError):missing_gap_joint_blockers(root,'G',graph)
if __name__=='__main__':unittest.main()
