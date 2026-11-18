import copy,unittest
from gap_joint_viewer_evidence import validate


class GapJointViewerEvidence(unittest.TestCase):
 def setUp(self):
  self.edge={'edge_id':'E','system':'return','start_node_id':'A','end_node_id':'B','start_floor':1,'attribute_paths':[[[0,0],[1,1]]],'source_handles':['L']};self.graph={'edges':[self.edge]}
  self.e={'status':'missing_source_joints_candidate_screen','source_sha256':'S','graph_sha256':'I','policy_sha256':'P','script_sha256':'T','graph_mutated':False,'hil_ready':False,'records':[{'edge_id':'E','insert_handle':'H','system':'return','candidate_type':'金属软接','physical_length':'unknown','human_accepted':False,'status':'source_calibrated_joint_unassigned_pending_review'}]}
  self.s={'status':'missing_joint_candidates_pending_source_comparison','source_sha256':'S','final_graph_sha256':'G','evidence_sha256':'D','input_graph_sha256':'I','policy_sha256':'P','script_sha256':'T','human_accepted':False,'hil_ready':False,'candidate_count':1,'candidate_handles':['H']}
 def test_candidates_remain_unassigned(self):
  r=validate(self.e,self.s,self.graph,self.graph,'S','G','D');self.assertEqual(r[0]['candidate_edge_id'],'E');self.assertNotIn('edge_id',r[0]);self.assertEqual(r[0]['ownership'],'unconfirmed')
 def test_graph_or_evidence_changes_rejected(self):
  g=copy.deepcopy(self.graph);g['edges'][0]['end_node_id']='C'
  with self.assertRaises(ValueError):validate(self.e,self.s,self.graph,g,'S','G','D')
  with self.assertRaises(ValueError):validate(self.e,self.s,self.graph,self.graph,'S','G','changed')
if __name__=='__main__':unittest.main()
