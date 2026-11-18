import copy,hashlib,json,tempfile,unittest
from pathlib import Path
import ezdxf
from calibrate_duplicate_circle_screen import prepare
from source_circle_rim_tee_screen import LAYERS

class CalibratedDuplicateCircleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name)
  self.doc=ezdxf.new();m=self.doc.modelspace();layer=next(k for k,v in LAYERS.items() if v=='supply');self.main=m.add_line((0,0),(0,1000),dxfattribs={'layer':layer});self.duplicate=m.add_line((0,1000),(0,0),dxfattribs={'layer':layer})
  self.control=m.add_circle((0,300),20,dxfattribs={'layer':layer});self.target=m.add_circle((0,600),20,dxfattribs={'layer':layer});self.cb=m.add_line((-20,300),(-100,300),dxfattribs={'layer':layer});self.tb=m.add_line((-20,600),(-100,600),dxfattribs={'layer':layer})
  issue=root/'issue.json';issue.write_text(json.dumps({'sourceHashes':{'main_dxf':'s'},'issue':{'id':'case','note':'connect'}}),encoding='utf8');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  evidence={'circle_handle':self.control.dxf.handle,'expert_issue_evidence':{'issue':str(issue),'issue_sha256':sha(issue),'issue_id':'case'},'coincident_native_main_handles':[self.main.dxf.handle,self.duplicate.dxf.handle],'physical_main_identity':'unresolved'}
  self.graph={'metadata':{'source_sha256':'s'},'nodes':[{'node_id':'T','node_type':'tee','system':'supply','floor':2,'expert_confirmed_circle':evidence},{'node_id':'U','subtype':'unresolved_source_terminal','system':'supply','floor':2,'x':-20,'y':600},{'node_id':'V','subtype':'out_of_plane_interface','system':'supply','floor':2,'x':-100,'y':600}],
   'edges':[{'edge_id':'M1','system':'supply','start_node_id':'A','end_node_id':'T','path':[[0,0],[0,300]],'source_handles':[self.main.dxf.handle]}, {'edge_id':'M2','system':'supply','start_node_id':'T','end_node_id':'B','path':[[0,300],[0,1000]],'source_handles':[self.main.dxf.handle]}, {'edge_id':'C','system':'supply','start_node_id':'T','end_node_id':'Q','source_handles':[self.cb.dxf.handle]}, {'edge_id':'BR','system':'supply','start_node_id':'U','end_node_id':'V','source_handles':[self.tb.dxf.handle]}],
   'expertConfirmedCircleJunctionRepair':{'source_sha256':'s','confirmation':{'confirmed_by':'expert','answer':'connect'},'records':[{'circle_handle':self.control.dxf.handle,'tee':'T','branch_edge':'C'}]}}
  self.screen={'source_sha256':'s','graph_sha256':'g','ambiguous_native_geometry':[{'circle_handle':self.target.dxf.handle,'system':'supply','main_handles':[self.main.dxf.handle,self.duplicate.dxf.handle],'branch_handles':[self.tb.dxf.handle]}]}
  image=root/'pair.png';image.write_bytes(b'pair');self.review={'source_sha256':'s','graph_sha256':'g','pairs':[{'image':str(image),'image_sha256':sha(image),'connections':[{'circle_handle':self.target.dxf.handle}]}]}
  self.policy={'source_sha256':'s','graph_sha256':'g','screen_sha256':'screen','review_sha256':'review','selections':[{'circle_handle':self.target.dxf.handle,'control_circle':self.control.dxf.handle}]}
 def call(self):return prepare(self.doc,self.graph,self.screen,self.review,self.policy,'s','g','screen','review')
 def test_exact_geometry_is_candidate_not_expert_acceptance(self):
  before=copy.deepcopy(self.graph);c=self.call()['candidates'][0];self.assertFalse(c['human_accepted']);self.assertEqual(c['expert_control_circle'],self.control.dxf.handle);self.assertEqual(c['physical_main_identity'],'unresolved');self.assertEqual(before,self.graph)
 def test_different_branch_z_or_other_system_center_rejected(self):
  self.tb.dxf.end=(-100,600,1)
  with self.assertRaises(ValueError):self.call()
  self.tb.dxf.end=(-100,600,0);other=next(k for k,v in LAYERS.items() if v=='return');self.doc.modelspace().add_line((-10,600),(10,600),dxfattribs={'layer':other})
  with self.assertRaises(ValueError):self.call()
 def test_wrong_floor_or_stale_issue_rejected(self):
  self.graph['nodes'][1]['floor']=3
  with self.assertRaises(ValueError):self.call()
  self.graph['nodes'][1]['floor']=2;Path(self.graph['nodes'][0]['expert_confirmed_circle']['expert_issue_evidence']['issue']).write_text('{}',encoding='utf8')
  with self.assertRaises(ValueError):self.call()
if __name__=='__main__':unittest.main()
