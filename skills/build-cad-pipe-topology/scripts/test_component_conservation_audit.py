import copy,unittest,ezdxf
from component_conservation_audit import evaluate
class ComponentConservation(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();self.doc.blocks.new('FLEX');ent=self.doc.modelspace().add_blockref('FLEX',(0,0));self.h=ent.dxf.handle
  self.initial=[{'device_name':'V','equipment_type':'ball_valve','type_code':'V','source_kind':'block_reference','source_block_name':'VALVE','source_handle':'A','edge_id':'old'}]
  self.final=[dict(self.initial[0],edge_id='E'),{'device_name':'F','equipment_type':'flexible_joint','type_code':'FLEX','source_kind':'block_reference','source_block_name':'FLEX','source_handle':self.h,'edge_id':'E'}]
  self.graph={'metadata':{'source_sha256':'S'},'edges':[{'edge_id':'E','system':'supply','equipment_counts':{'ball_valve':1,'flexible_joint':1},'equipment_names':['V','F'],'source_flexible_joints':[{'source_handle':self.h,'source_block':'FLEX','parameter_status':'unknown_not_zero','physical_length':'unknown'}]}]}
  self.repair={'source_sha256':'S','steps':[{'source_handle':self.h,'system':'supply'}]};self.policy={'source_sha256':'S','graph_sha256':'G','initial_csv_sha256':'I','repair_audit_sha256':'R'}
 def run_case(self):return evaluate(self.doc,self.graph,self.initial,self.final,self.repair,self.policy,'S','G','I','R')
 def test_preservation_reassignment_and_source_flex(self):
  original=copy.deepcopy(self.graph);r=self.run_case();self.assertEqual(r['counts']['flex_additions'],1);self.assertFalse(r['human_accepted']);self.assertEqual(original,self.graph)
 def test_missing_initial_duplicate_and_changed_identity_fail(self):
  old=self.final.pop(0)
  with self.assertRaises(ValueError):self.run_case()
  self.final.insert(0,old);self.final.append(copy.deepcopy(old))
  with self.assertRaises(ValueError):self.run_case()
  self.final.pop();self.final[0]['source_handle']='wrong'
  with self.assertRaises(ValueError):self.run_case()
 def test_bad_aggregation_or_flex_parameter_fails(self):
  self.graph['edges'][0]['equipment_counts']['flexible_joint']=2
  with self.assertRaises(ValueError):self.run_case()
  self.graph['edges'][0]['equipment_counts']['flexible_joint']=1;self.graph['edges'][0]['source_flexible_joints'][0]['parameter_status']='zero'
  with self.assertRaises(ValueError):self.run_case()
 def test_stale_repair_fails(self):
  self.policy['repair_audit_sha256']='old'
  with self.assertRaises(ValueError):self.run_case()
if __name__=='__main__':unittest.main()
