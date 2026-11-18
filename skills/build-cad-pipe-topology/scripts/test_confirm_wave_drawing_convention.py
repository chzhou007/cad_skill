import copy,unittest
from confirm_wave_drawing_convention import apply,STATEMENT
class ConfirmWaveTest(unittest.TestCase):
 def setUp(self):
  self.graph={'edges':[{'edge_id':'e','system':'supply','connection_mode':'source_calibrated_wave_omission_unreviewed','path_length_complete':False,'source_wave_omission':{'wave_handles':['A','B'],'physical_length':'unknown'}}]}
  self.confirm={'statement':STATEMENT,'full_graph_accepted':False,'wave_pairs':[{'system':'supply','wave_handles':['A','B']}],'confirmation_sha256':'c','image_sha256':'i'}
 def test_scoped_confirmation_does_not_mutate_input(self):
  original=copy.deepcopy(self.graph);g,steps=apply(self.graph,self.confirm);self.assertEqual(self.graph,original);w=g['edges'][0]['source_wave_omission'];self.assertTrue(w['scoped_expert_convention_confirmed']);self.assertFalse(w['physical_component']);self.assertFalse(w['additional_physical_property']);self.assertEqual(w['physical_length'],'unknown');self.assertFalse(g['metadata']['hil_ready']);self.assertEqual(len(steps),1)
 def test_reject_wrong_scope_or_full_acceptance(self):
  self.confirm['wave_pairs'][0]['system']='return'
  with self.assertRaises(ValueError):apply(self.graph,self.confirm)
  self.confirm['wave_pairs'][0]['system']='supply';self.confirm['full_graph_accepted']=True
  with self.assertRaises(ValueError):apply(self.graph,self.confirm)
if __name__=='__main__':unittest.main()
