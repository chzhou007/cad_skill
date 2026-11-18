import copy,unittest,ezdxf
from prepare_expert_duplicate_circle_screen import prepare
from source_circle_rim_tee_screen import LAYERS

class ExpertDuplicateCircleScreenTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();layer=next(k for k,v in LAYERS.items() if v=='supply')
  self.main=m.add_line((0,0),(1000,0),dxfattribs={'layer':layer});self.dup=m.add_line((1000,0),(0,0),dxfattribs={'layer':layer})
  self.branch=m.add_line((400,80),(400,300),dxfattribs={'layer':layer});self.circle=m.add_circle((400,0),80,dxfattribs={'layer':layer})
  self.graph={'metadata':{'source_sha256':'s'},'nodes':[{'node_id':'U','subtype':'unresolved_source_terminal','system':'supply','x':400,'y':80}],
   'edges':[{'edge_id':'M','system':'supply','start_node_id':'A','end_node_id':'B','path':[[0,0],[1000,0]],'source_handles':[self.main.dxf.handle]},
            {'edge_id':'BR','system':'supply','start_node_id':'U','end_node_id':'D','path':[[400,80],[400,300]],'source_handles':[self.branch.dxf.handle]}]}
  self.screen={'source_sha256':'s','graph_sha256':'g','ambiguous_native_geometry':[{'circle_handle':self.circle.dxf.handle,'system':'supply','main_handles':[self.main.dxf.handle,self.dup.dxf.handle],'branch_handles':[self.branch.dxf.handle]}]}
  self.issue={'sourceHashes':{'main_dxf':'s'},'issue':{'id':'case','note':'connect','sourceBounds':[0,-100,1000,500],'nodes':['U'],'edges':['M','BR']}}
  self.policy={'source_sha256':'s','graph_sha256':'g','screen_sha256':'screen','issue_sha256':'issue','issue_id':'case','selections':[{'circle_handle':self.circle.dxf.handle,'main_edge':'M','branch_edge':'BR','terminal':'U'}]}
 def call(self):return prepare(self.doc,self.graph,self.screen,self.issue,self.policy,'s','g','screen','issue')
 def test_selected_scope_rebuilt_without_claiming_duplicate_identity(self):
  before=copy.deepcopy(self.graph);row=self.call()['candidates'][0]
  self.assertEqual(row['main_graph_edges'],['M']);self.assertEqual(row['physical_main_identity'],'unresolved');self.assertEqual(self.graph,before)
 def test_unselected_and_nonidentical_mains_fail(self):
  self.issue['issue']['edges'].remove('BR')
  with self.assertRaises(ValueError):self.call()
  self.issue['issue']['edges'].append('BR');self.dup.dxf.end=(0,1,0)
  with self.assertRaises(ValueError):self.call()
 def test_stale_issue_and_outside_region_fail(self):
  self.policy['issue_sha256']='wrong'
  with self.assertRaises(ValueError):self.call()
  self.policy['issue_sha256']='issue';self.issue['issue']['sourceBounds']=[500,0,100,100]
  with self.assertRaises(ValueError):self.call()
if __name__=='__main__':unittest.main()
