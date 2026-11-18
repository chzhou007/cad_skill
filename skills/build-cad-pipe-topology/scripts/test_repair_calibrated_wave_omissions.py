import copy,unittest
from test_wave_omission_candidates import WaveCandidatesTest
from repair_calibrated_wave_omissions import repair

class WaveRepairTest(unittest.TestCase):
 def setUp(self):
  f=WaveCandidatesTest();f.setUp();self.doc=f.doc;self.g=f.graph;self.ds=[]
  self.g['nodes'] += [{'node_id':'x','node_type':'tee'},{'node_id':'y','node_type':'tee'}]
  m=self.doc.modelspace();lines=[m.add_line((-100,0),(0,0),dxfattribs={'layer':'supply'}),m.add_line((100,0),(200,0),dxfattribs={'layer':'supply'})]
  for n,e,line in zip(self.g['nodes'][:2],self.g['edges'],lines):
   n['node_type']='virtual_equipment';n['source_handles']=[line.dxf.handle]
   e.update(start_floor=2,end_floor=2,edge_type='tee_to_virtual_equipment',path_points=e['path'],attribute_paths=[e['path']],path_length=100.,source_handles=[line.dxf.handle],equipment_names=[],equipment_counts={})
  wave=[x.dxf.handle for x in m.query('INSERT')];self.g['expertWaveOmissionRepair']={'issue':'control','source_sha256':'hash','steps':[{'source_wave_handles':wave}]}
  self.p={'control_issue':'control','source_sha256':'hash','control_wave_handles':wave,'block_name':'wave','block_fingerprint':f.fingerprint,'max_gap':200,'contact_tolerance':.5,'source_layer_by_system':{'supply':'supply','return':'return'},'pairs':[{'nodes':['a','b'],'wave_handles':wave}]}
 def test_join_preserves_paths_and_unknown_length(self):
  before=copy.deepcopy(self.g);g,ds=repair(self.g,self.ds,self.doc,self.p);self.assertEqual(before,self.g);self.assertEqual(len(g['edges']),1);self.assertEqual(len(g['nodes']),2);e=g['edges'][0];self.assertEqual(len(e['attribute_paths']),2);self.assertFalse(e['path_length_complete']);self.assertEqual(e['path_length'],200);self.assertFalse(g['calibratedWaveOmissionRepair']['human_accepted']);self.assertEqual(ds,[])
 def test_reject_wrong_source_system(self):
  self.p['source_layer_by_system']['supply']='return'
  with self.assertRaises(ValueError):repair(self.g,self.ds,self.doc,self.p)
 def test_reject_unknown_attributes(self):
  self.g['edges'][1]['diameter']='DN100'
  with self.assertRaises(ValueError):repair(self.g,self.ds,self.doc,self.p)
 def test_reject_missing_expert_control_and_bad_candidates(self):
  self.g['expertWaveOmissionRepair']['issue']='other'
  with self.assertRaises(ValueError):repair(self.g,self.ds,self.doc,self.p)
  self.g['expertWaveOmissionRepair']['issue']='control';self.g['nodes'][1]['floor']=3
  with self.assertRaises(ValueError):repair(self.g,self.ds,self.doc,self.p)
 def test_component_conservation(self):
  self.g['edges'][0]['equipment_names']=['valve'];self.g['edges'][0]['equipment_counts']={'valve':1};self.ds=[{'edge_id':'1','device_name':'valve','equipment_type':'valve'}]
  g,rows=repair(self.g,self.ds,self.doc,self.p);self.assertEqual(rows[0]['edge_id'],g['edges'][0]['edge_id']);self.assertEqual(g['edges'][0]['equipment_counts'],{'valve':1})
 def test_retired_reference_fails_closed(self):
  self.g['external_mapping']={'edge':'2'}
  with self.assertRaises(ValueError):repair(self.g,self.ds,self.doc,self.p)
if __name__=='__main__':unittest.main()
