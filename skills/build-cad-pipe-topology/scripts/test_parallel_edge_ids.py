import json,tempfile,unittest
from pathlib import Path
from reconcile_graph_ids import reconcile
class ParallelEdgeIdentityTest(unittest.TestCase):
 def test_two_distinct_paths_with_same_endpoints_keep_ids(self):
  with tempfile.TemporaryDirectory()as tmp:
   root=Path(tmp);nodes=[{'node_id':n,'node_type':'tee','system':'supply','x':x,'y':0}for n,x in [('T001',0),('T002',10)]]
   edges=[{'edge_id':eid,'start_node_id':'T001','end_node_id':'T002','system':'supply','path':path}for eid,path in [('E0008',[[0,0],[5,1],[10,0]]),('E0020',[[0,0],[5,-1],[10,0]])]]
   old={'nodes':nodes,'edges':edges};previous=root/'previous.json';previous.write_text(json.dumps(old),encoding='utf8');out=root/'new';out.mkdir()
   new=json.loads(json.dumps(old));new['edges'][0]['edge_id']='E0001';new['edges'][1]['edge_id']='E0002';(out/'graph_with_edges.json').write_text(json.dumps(new),encoding='utf8')
   r=reconcile(previous,out);self.assertEqual(r['edge_remapping'],{'E0001':'E0008','E0002':'E0020'});self.assertEqual(r['retired_edges'],[])
if __name__=='__main__':unittest.main()
