import copy,unittest
import ezdxf
from crossview_local_dn_screen import screen

class CrossviewDnTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();self.line=m.add_line((0,0),(0,100),dxfattribs={'layer':'空调冷冻水供水'});self.text=m.add_text('DN65',dxfattribs={'layer':'标注','insert':(1,50),'height':10,'rotation':90})
  self.plan={'edges':[{'edge_id':'P','system':'supply','diameter_inference':{'status':'source_scoped_inheritance_candidate_not_accepted','nominal_mm_candidate':300,'lineage':[]}}]}
  self.iso={'edges':[{'edge_id':'I','system':'supply','attribute_paths':[[[0,0],[0,100]]]}]}
  self.policy={'text_layers':['标注'],'selections':[{'plan_edge':'P','iso_edge':'I','system':'supply','text_handle':self.text.dxf.handle,'text':'DN65','line_handle':self.line.dxf.handle}]}
 def test_candidate_does_not_mutate_or_assign(self):
  before=copy.deepcopy((self.plan,self.iso));r=screen(self.plan,self.iso,self.doc,self.policy);self.assertEqual((self.plan,self.iso),before);self.assertEqual(r['records'][0]['status'],'different_values_potential_conflict');self.assertFalse(r['records'][0]['physical_diameter_selected']);self.assertEqual(r['records'][0]['crossview_path_mapping'],'not_confirmed')
 def test_equal_values_are_not_conflict(self):
  self.plan['edges'][0]['diameter_inference']['nominal_mm_candidate']=65;self.assertEqual(screen(self.plan,self.iso,self.doc,self.policy)['records'][0]['status'],'same_values_candidate_only')
 def test_system_mismatch_and_missing_witness_rejected(self):
  self.iso['edges'][0]['system']='return'
  with self.assertRaises(ValueError):screen(self.plan,self.iso,self.doc,self.policy)
  self.iso['edges'][0]['system']='supply';self.iso['edges'][0]['attribute_paths']=[[[5,0],[5,100]]]
  with self.assertRaises(ValueError):screen(self.plan,self.iso,self.doc,self.policy)
 def test_competing_native_line_rejected(self):
  self.doc.modelspace().add_line((2,0),(2,100),dxfattribs={'layer':'空调冷冻水回水'})
  with self.assertRaises(ValueError):screen(self.plan,self.iso,self.doc,self.policy)
 def test_local_observation_stays_candidate_and_never_becomes_edge_value(self):
  edge=self.plan['edges'][0];edge.pop('diameter_inference');edge['source_handles']=['L'];edge['pipe_diameter']={'status':'local_source_observation_edgewide_unverified','nominal_mm':None,'observations':[{'status':'native_source_local_observation','nominal_mm':65,'source_line_handle':'L','text':{'handle':'D'}}]}
  row=screen(self.plan,self.iso,self.doc,self.policy)['records'][0]
  self.assertEqual(row['plan_candidate_kind'],'native_local_observation');self.assertEqual(row['status'],'same_values_candidate_only');self.assertFalse(row['physical_diameter_selected'])
  edge['pipe_diameter']['nominal_mm']=65
  with self.assertRaises(ValueError):screen(self.plan,self.iso,self.doc,self.policy)
if __name__=='__main__':unittest.main()
