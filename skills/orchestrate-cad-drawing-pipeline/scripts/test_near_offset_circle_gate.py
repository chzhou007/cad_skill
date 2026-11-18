import hashlib,json,tempfile,unittest
from pathlib import Path
from source_comparison_gate import near_offset_circle_blockers
class NearOffsetCircleGateTest(unittest.TestCase):
 def test_keeps_candidates_and_rejects_stale_or_missing_evidence(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);r=root/'reports';r.mkdir();graph={'edges':[{'edge_id':'M','system':'return','source_handles':['MAIN']},{'edge_id':'B','system':'return','source_handles':['BRANCH']}],'nodes':[{'node_id':'U','system':'return'}]};row={'circle_handle':'C','line_system':'return','status':'near_main_not_connection_confirmation','radius':100,'main_handle':'MAIN','branch_handle':'BRANCH','main_offset_drawing_units':1,'main_graph_edges':['M'],'branch_graph_edges':['B'],'rim_virtual_nodes':['U']};e={'status':'near_offset_circle_candidates_only','source_sha256':'S','graph_sha256':'G','circle_radius':100,'max_main_offset':2,'policy_sha256':'a'*64,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'candidates':[row],'ambiguous_native_geometry':[]};ep=r/'near-offset-circle-screen.json';sp=r/'near-offset-circle-stage.json'
   def write():
    ep.write_text(json.dumps(e),encoding='utf8');s={'status':'near_offset_circle_screen_required','source_sha256':'S','graph_sha256':'G','policy_sha256':'a'*64,'policy_map_sha256':'b'*64,'evidence_sha256':hashlib.sha256(ep.read_bytes()).hexdigest(),'candidate_count':1,'ambiguous_count':0,'hil_ready':False};sp.write_text(json.dumps(s),encoding='utf8')
   write();self.assertEqual(near_offset_circle_blockers(root,'G','S',graph)[0]['circle_handle'],'C')
   row['branch_graph_edges']=['M'];write()
   with self.assertRaises(ValueError):near_offset_circle_blockers(root,'G','S',graph)
   sp.unlink()
   with self.assertRaises(ValueError):near_offset_circle_blockers(root,'G','S',graph)
if __name__=='__main__':unittest.main()
