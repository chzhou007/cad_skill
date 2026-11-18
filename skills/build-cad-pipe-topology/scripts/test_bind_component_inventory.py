import copy
import unittest
from bind_component_inventory import validate

class ComponentBindingTests(unittest.TestCase):
 def setUp(self):
  self.graph={'metadata':{'source_sha256':'source'},'edges':[{'edge_id':'E1','equipment_inventory':[{'equipment_type':'阀门','count':1,'device_names':['V1']}]},{'edge_id':'E2','equipment_inventory':[]}]}
  self.rows=[{'edge_id':'E1','equipment_type':'阀门','device_name':'V1','assignment_status':'assigned'}]
  self.policy={'source_sha256':'source','graph_sha256':'graph','components_sha256':'csv'}
 def run_validate(self):return validate(self.graph,self.rows,self.policy,graph_sha256='graph',components_sha256='csv',source_sha256='source')
 def test_exact_binding_and_no_source_coverage_claim(self):
  original=copy.deepcopy(self.graph);a=self.run_validate();self.assertEqual(self.graph,original)
  self.assertEqual(a['component_instances'],1);self.assertFalse(a['source_coverage_verified']);self.assertFalse(a['valve_ownership_verified'])
 def test_changed_owner_or_type_rejected(self):
  for k,value in [('edge_id','E2'),('equipment_type','错误'),('assignment_status','pending')]:
   with self.subTest(k=k):
    self.setUp();self.rows[0][k]=value
    with self.assertRaises(ValueError):self.run_validate()
 def test_missing_duplicate_and_bad_aggregate_rejected(self):
  self.rows=[]
  with self.assertRaises(ValueError):self.run_validate()
  self.setUp();self.rows.append(copy.deepcopy(self.rows[0]))
  with self.assertRaises(ValueError):self.run_validate()
  self.setUp();self.graph['edges'][0]['equipment_inventory'][0]['count']=2
  with self.assertRaises(ValueError):self.run_validate()
 def test_stale_hash_rejected(self):
  self.policy['components_sha256']='different'
  with self.assertRaises(ValueError):self.run_validate()

if __name__=='__main__':unittest.main()
