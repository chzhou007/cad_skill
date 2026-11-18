import copy,unittest
from test_repair_calibrated_wave_omissions import WaveRepairTest
from attach_unpaired_wave_evidence import attach

class UnpairedWaveEvidenceTest(unittest.TestCase):
 def setUp(self):
  f=WaveRepairTest();f.setUp();self.d=f.doc;self.g=f.g;self.p=copy.deepcopy(f.p);self.p['graph_sha256']='test-graph';self.p['endpoints']=[{'node_id':'a','wave_handle':self.p['pairs'][0]['wave_handles'][0]}]
 def test_unpaired_is_edge_evidence_without_connectivity_change(self):
  wave=self.d.entitydb[self.p['pairs'][0]['wave_handles'][1]];self.d.modelspace().delete_entity(wave)
  old=copy.deepcopy(self.g);g,changes=attach(self.d,self.g,self.p);self.assertEqual(self.g,old);self.assertEqual(g['nodes'],old['nodes']);self.assertEqual(changes[0]['paired_continuation'],'not_established');self.assertEqual(g['edges'][0]['source_wave_terminal']['destination'],'unknown')
 def test_paired_candidate_is_not_called_unpaired(self):
  with self.assertRaises(ValueError):attach(self.d,self.g,self.p)
 def test_source_system_mismatch_rejected(self):
  wave=self.d.entitydb[self.p['pairs'][0]['wave_handles'][1]];self.d.modelspace().delete_entity(wave);self.p['source_layer_by_system']['supply']='return'
  with self.assertRaises(ValueError):attach(self.d,self.g,self.p)
if __name__=='__main__':unittest.main()
