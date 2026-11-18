import copy,unittest
from reconcile_joint_inventory_contacts import reconcile

class JointContacts(unittest.TestCase):
 def setUp(self):
  self.h={'source_sha256':'S','inventory_sha256':'I','old_graph_sha256':'O','final_graph_sha256':'F'};self.g={'edges':[{'edge_id':'E','system':'return','start_node_id':'A','end_node_id':'B','attribute_paths':[[[0,0],[1,0]]],'source_handles':['L']}]};self.i={'source_sha256':'S','inventory_sha256':'I','records':[{'source_handle':'H','status':'inventory_assignment_present_not_verified','inventory_matches':[{'edge_id':'E','device_name':'D'}]},{'source_handle':'U','status':'unassigned_source_instance','inventory_matches':[]}]};line={'source_handle':'L','system':'return','assigned_edge_witnessed':True};self.c={'source_sha256':'S','inventory_sha256':'I','graph_sha256':'O','records':[{'source_handle':'H','edge_id':'E','device_name':'D','assigned_system':'return','status':'same_system_assigned_edge_contact_witnessed','contacts':[{'lines':[line]},{'lines':[line]}]}]}
 def test_witnesses_remain_unaccepted(self):
  r=reconcile(self.i,self.c,self.g,self.g,self.h);self.assertEqual([x['status'] for x in r['records']],['two_source_contacts_witnessed_not_acceptance','unassigned_source_instance']);self.assertFalse(r['human_accepted'])
 def test_changed_edge_or_system_does_not_inherit_contact(self):
  g=copy.deepcopy(self.g);g['edges'][0]['end_node_id']='C'
  with self.assertRaises(ValueError):reconcile(self.i,self.c,self.g,g,self.h)
  c=copy.deepcopy(self.c);c['records'][0]['contacts'][0]['lines'][0]['system']='supply'
  with self.assertRaises(ValueError):reconcile(self.i,c,self.g,self.g,self.h)
if __name__=='__main__':unittest.main()
