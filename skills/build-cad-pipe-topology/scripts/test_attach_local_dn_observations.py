import copy,unittest
from attach_local_dn_observations import attach
class LocalDN(unittest.TestCase):
 def setUp(self):
  self.g={'metadata':{'source_sha256':'S'},'edges':[{'edge_id':'E','system':'supply','source_handles':['L'],'path':[[0,0],[0,10]]}],'nodes':[]}
  self.ev={'source_sha256':'S','graph_sha256':'G','status':'candidate_not_accepted','observations':[{'edge_id':'E','system':'supply','status':'candidate_source_annotation','nominal_mm':300.,'source_line_handle':'L','source_text':{'source_sha256':'S','source_id':'sheet','handle':'T','text':'DN300'},'graph_projection':[0,5]}]}
 def test_local_observation_does_not_become_edgewide(self):
  before=copy.deepcopy(self.g);out,a=attach(self.g,self.ev,'S','G');self.assertEqual(before,self.g);e=out['edges'][0];self.assertIsNone(e['diameter_nominal_mm']);self.assertIsNone(e['pipe_diameter']['nominal_mm']);self.assertEqual(e['pipe_diameter']['observations'][0]['nominal_mm'],300.);self.assertFalse(a['inheritance_applied']);self.assertFalse(out['metadata']['hil_ready'])
 def test_wrong_hash_system_or_line_rejected(self):
  with self.assertRaises(ValueError):attach(self.g,self.ev,'S','wrong')
  for field,val in [('system','return'),('source_line_handle','wrong'),('nominal_mm',float('nan'))]:
   ev=copy.deepcopy(self.ev);ev['observations'][0][field]=val
   with self.assertRaises(ValueError):attach(self.g,ev,'S','G')
 def test_existing_value_and_duplicate_observations_rejected(self):
  self.g['edges'][0]['diameter_nominal_mm']=100
  with self.assertRaises(ValueError):attach(self.g,self.ev,'S','G')
  self.g['edges'][0]['diameter_nominal_mm']=None;self.ev['observations'].append(copy.deepcopy(self.ev['observations'][0]))
  with self.assertRaises(ValueError):attach(self.g,self.ev,'S','G')
if __name__=='__main__':unittest.main()
