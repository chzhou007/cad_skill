import copy,unittest,ezdxf
from expert_node_reconciliation import evaluate
class ExpertNodeReconciliation(unittest.TestCase):
 def setUp(self):
  self.d=ezdxf.new();m=self.d.modelspace();layer='空调冷冻水供水';line=m.add_line((0,80),(0,200),dxfattribs={'layer':layer});main=m.add_line((-200,0),(200,0),dxfattribs={'layer':layer});circle=m.add_circle((0,0),80,dxfattribs={'layer':layer});bars=[m.add_line((-10,y),(10,y),dxfattribs={'layer':'空调平面'}) for y in (200,210)];h=line.dxf.handle;mh=main.dxf.handle;ch=circle.dxf.handle
  self.issue={'sourceHashes':{'main_dxf':'S'},'issue':{'label':'ERR','nodes':['U1','U2']}};self.context={'nodes':[{'node_id':'U1','system':'supply','x':0,'y':200,'source_handles':[h]},{'node_id':'U2','system':'supply','x':0,'y':80,'source_handles':[h]}]};self.graph={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'T','x':0,'y':0,'system':'supply','source_handles':[h,mh,ch],'source_reviewed_circle':{'circle_handle':ch,'source_rim':[0,80],'z_consistent_within_tolerance':False}}],'boundary_anchors':[{'boundary_id':'A','kind':'expert_non_node_source_boundary','expert_issue':'ERR','source_pipe_handle':h,'x':0,'y':200,'source_marker_handles':[x.dxf.handle for x in bars]}],'edges':[{'edge_id':'E','system':'supply','start_node_id':'T','end_node_id':None,'end_boundary_id':'A','source_handles':[h],'path':[[0,0],[0,80],[0,200]]}]};self.graph['edges'].extend([{'edge_id':'M1','system':'supply','start_node_id':'T','end_node_id':'X','source_handles':[mh]},{'edge_id':'M2','system':'supply','start_node_id':'T','end_node_id':'Y','source_handles':[mh]}]);self.graph['nodes'][0]['node_type']='tee';self.policy={'source_sha256':'S','graph_sha256':'G','issue_sha256':'I','context_sha256':'C','cases':[{'expert_node_id':'U1','source_pipe_handle':h,'final_edge_id':'E','mode':'expert_non_node_boundary','boundary_id':'A'},{'expert_node_id':'U2','source_pipe_handle':h,'final_edge_id':'E','mode':'circle_rim_is_edge_interior','tee_id':'T','circle_handle':ch,'main_handle':mh}]}
 def run_case(self):return evaluate(self.d,self.graph,self.issue,self.context,self.policy,'S','G','I','C')
 def test_boundary_and_rim_both_preserve_pipe(self):
  before=copy.deepcopy(self.graph);r=self.run_case();self.assertEqual(len(r['records']),2);self.assertFalse(r['human_accepted']);self.assertFalse(r['records'][1]['source_z_consistent']);self.assertEqual(self.graph,before)
 def test_missing_legacy_node_or_stale_evidence_fails(self):
  self.policy['cases'].pop()
  with self.assertRaises(ValueError):self.run_case()
  self.policy['graph_sha256']='old'
  with self.assertRaises(ValueError):self.run_case()
 def test_mixed_system_or_missing_tee_ray_fails(self):
  self.graph['edges'][-1]['system']='return'
  with self.assertRaises(ValueError):self.run_case()
  self.graph['edges'][-1]['system']='supply';self.graph['edges'].pop()
  with self.assertRaises(ValueError):self.run_case()
 def test_legacy_fake_node_or_broken_source_path_fails(self):
  self.graph['nodes'].append({'node_id':'BAD','x':0,'y':80,'system':'supply'})
  with self.assertRaises(ValueError):self.run_case()
  self.graph['nodes'].pop();self.graph['edges'][0]['path']=[[0,0],[0,200]]
  with self.assertRaises(ValueError):self.run_case()
if __name__=='__main__':unittest.main()
