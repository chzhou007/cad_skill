import unittest
from source_semantic_reconciliation import reconcile,resolve_profile_aliases
class SemanticTests(unittest.TestCase):
 def setUp(self):
  self.g={'nodes':[{'node_id':'U','x':0,'y':0,'boundary_type':'unresolved_source_terminal','ports':[{}]}],'edges':[]}
  self.e={'interface_bindings':[{'annotation':{'handle':'T','text':'接专用排水管'},'leader_handles':['L'],'terminal_contacts':[{'node_id':'U','leader_endpoint':[0,0]}]}]}
 def test_named_interface_is_not_fabricated_equipment(self):
  g,a=reconcile(self.g,self.e);self.assertEqual(g['nodes'][0]['subtype'],'drain_interface');self.assertFalse(g['metadata']['hil_ready']);self.assertEqual(self.g['nodes'][0]['boundary_type'],'unresolved_source_terminal');self.assertEqual(g['edges'],[])
 def test_nearest_text_cannot_bind_without_native_contact(self):
  self.e['interface_bindings'][0]['terminal_contacts'][0]['leader_endpoint']=[100,0]
  with self.assertRaises(ValueError):reconcile(self.g,self.e)
 def test_alias_preserves_original_and_requires_exact_audit(self):
  p=resolve_profile_aliases({'inline_types':{'A':['symbol','X']},'inline_bridge_blocks':['A']},{'block_aliases':{'A0':'A'}})
  self.assertEqual(p['inline_types']['A0'][1],'SRC');self.assertNotIn('A0',p['inline_bridge_blocks'])
 def test_tangent_is_never_a_hydraulic_merge(self):
  self.e['circle_groups']=[{'circle':{'handle':'C'},'center_nodes':['U'],'rim_nodes':['U'],'pairs':[{'same_system':False}]}]
  g,a=reconcile(self.g,self.e);self.assertEqual(g['sourceAssemblies'][0]['status'],'cross_system_tangency_excluded');self.assertEqual(g['edges'],[])
if __name__=='__main__':unittest.main()
