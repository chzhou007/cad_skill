import json,unittest,copy
from equipment_identity_dn_recheck import prepare
class IdentityDNRecheckTest(unittest.TestCase):
 def setUp(self):self.old={'nodes':[{'node_id':'N'}],'edges':[{'edge_id':'E'}]};self.new=copy.deepcopy(self.old);self.new['nodes'].append({'node_id':'C','node_type':'equipment','connection_status':'ports_unresolved'});self.policy=json.dumps({'source_sha256':'S','graph_sha256':'G','selections':[]}).encode()
 def test_node_addition_retains_selections(self):
  r=prepare(self.old,self.new,self.policy,'S','G','G2');self.assertEqual(r['graph_sha256'],'G2');self.assertEqual(r['prior_graph_sha256'],'G');self.assertEqual(r['selections'],[])
 def test_changed_edges_existing_node_or_wrong_source_fail(self):
  for mutation in ('edge','node','source','new'):
   n=copy.deepcopy(self.new);s='S'
   if mutation=='edge':n['edges'][0]['new']=1
   if mutation=='node':n['nodes'][0]['new']=1
   if mutation=='new':n['nodes'][-1]['connection_status']='confirmed'
   if mutation=='source':s='bad'
   with self.assertRaises(ValueError):prepare(self.old,n,self.policy,s,'G','G2')
if __name__=='__main__':unittest.main()
