import copy,unittest
from test_screen_equipment_label_pairs import EquipmentLabelPairsTest
from screen_equipment_label_pairs import screen
from attach_equipment_pair_label_candidates import attach

class AttachEquipmentPairLabelsTest(unittest.TestCase):
 def setUp(self):
  f=EquipmentLabelPairsTest();f.setUp();self.g=f.pg;self.e=screen(f.p,f.a,f.pg,f.ag,f.receipt,f.policy,f.h)
 def test_both_labels_retained_without_identity_assignment(self):
  self.g['nodes'][0]['source_label_candidates']=['CRAH-1'];old=copy.deepcopy(self.g);out=attach(self.g,self.e,'PS','PG');self.assertEqual(self.g,old);self.assertEqual(out['nodes'][0]['source_label_candidates'],['CRAH-1','CRAH-2']);self.assertEqual(out['nodes'][0]['identity_status'],'unresolved');self.assertFalse(out['nodes'][0]['source_label_pair_evidence']['identity_confirmed'])
 def test_stale_or_discarded_original_candidate_fails(self):
  with self.assertRaisesRegex(ValueError,'stale'):attach(self.g,self.e,'PS','other')
  self.g['nodes'][0]['source_label_candidates']=['unexpected']
  with self.assertRaisesRegex(ValueError,'candidate mismatch'):attach(self.g,self.e,'PS','PG')
if __name__=='__main__':unittest.main()
