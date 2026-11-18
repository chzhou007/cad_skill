import copy,unittest
from rebase_unchanged_attribute_policy import rebase

class AttributeRebaseTests(unittest.TestCase):
 def setUp(self):
  self.g={'metadata':{'source_sha256':'s'},'nodes':[{'node_id':'A','node_type':'tee','system':'supply','x':0,'y':0},{'node_id':'B','node_type':'tee','system':'supply','x':10,'y':0}],'edges':[{'edge_id':'E','system':'supply','start_node_id':'A','end_node_id':'B','source_handles':['H'],'attribute_paths':[[[0,0],[10,0]]]}]}
  self.p={'source_sha256':'s','graph_sha256':'before','selections':[{'edge_id':'E','source_line_handle':'H'}]}
 def test_unrelated_repair_requires_reexecution_and_no_acceptance(self):
  new=copy.deepcopy(self.g);new['nodes'].append({'node_id':'OTHER','x':50,'y':0})
  p,a=rebase(self.g,new,self.p,'before','after');self.assertEqual(p['graph_sha256'],'after');self.assertFalse(a['human_acceptance_inherited']);self.assertEqual(self.p['graph_sha256'],'before')
 def test_stale_source_and_changed_path_or_system_fail(self):
  for patch in ({'source_handles':['WRONG']},{'system':'return'},{'attribute_paths':[[[0,0],[5,0]]]},{'end_node_id':'C'}):
   new=copy.deepcopy(self.g);new['edges'][0].update(patch)
   with self.assertRaises(ValueError):rebase(self.g,new,self.p,'before','after')
  with self.assertRaises(ValueError):rebase(self.g,self.g,self.p,'wrong','after')
 def test_added_incidence_blocks_inheritance_scope(self):
  p=dict(self.p,edges=['E'],junctions=['A']);new=copy.deepcopy(self.g)
  new['edges'].append(dict(new['edges'][0],edge_id='NEW'))
  with self.assertRaises(ValueError):rebase(self.g,new,p,'before','after')
  p=dict(self.p,junction_witnesses=[{'node_id':'A','edge_witnesses':{'E':'H'}}])
  with self.assertRaises(ValueError):rebase(self.g,new,p,'before','after')
if __name__=='__main__':unittest.main()
