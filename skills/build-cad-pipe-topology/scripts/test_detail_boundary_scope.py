import copy,unittest,ezdxf
from detail_boundary_scope import analyze

class BoundaryScopeTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();anchors=[];edges=[];uppers=[]
  for i,system in enumerate(('supply','return')):
   x=i*10;c=m.add_circle((x,0),2,dxfattribs={'layer':system});line=m.add_line((x,0),(x,10),dxfattribs={'layer':system});bid='B'+str(i)
   anchors.append({'boundary_id':bid,'kind':'user_confirmed_non_node_source_boundary','system':system,'x':x,'y':0,'source_circle_handle':c.dxf.handle,'source_pipe_handle':line.dxf.handle});edges.append({'edge_id':'E'+str(i),'system':system,'end_boundary_id':bid,'source_handles':[line.dxf.handle]});uppers.append({'node_id':'U'+str(i),'system':system,'center':[x+100,100,0],'in_existing_candidate_set':False})
  self.graph={'metadata':{'source_sha256':'S'},'boundary_anchors':anchors,'edges':edges};self.scope={'status':'scoped_coverage_not_mapping','source_sha256':'S','graph_sha256':'G','mapping_ready':False,'regions':{'detail':{'xmin':-20,'xmax':20,'ymin':-2,'ymax':2}},'upper':uppers};self.policy={'source_sha256':'S','graph_sha256':'G','source_endpoint_tolerance':1,'reference_tolerance':1,'radius_min':1,'radius_max':3,'system_layers':{'supply':'supply','return':'return'}}
 def run_case(self):return analyze(self.doc,self.graph,self.scope,self.policy,'S','G')
 def test_non_node_boundaries_become_candidates_only(self):
  r=self.run_case();self.assertEqual(r['counts']['ordered_candidates'],2);self.assertFalse(r['mapping_ready']);self.assertFalse(r['graph_mutated']);self.assertTrue(all(x['status']=='ordered_candidate_not_connection' for x in r['rows']))
 def test_wrong_system_and_stale_evidence_are_rejected(self):
  self.policy['graph_sha256']='old'
  with self.assertRaises(ValueError):self.run_case()
  self.policy['graph_sha256']='G';self.policy['system_layers']['supply']='return'
  with self.assertRaises(ValueError):self.run_case()
 def test_duplicate_boundary_edge_rejected(self):
  self.graph['edges'].append(copy.deepcopy(self.graph['edges'][0]))
  with self.assertRaises(ValueError):self.run_case()
 def test_translation_outlier_remains_unresolved(self):
  m=self.doc.modelspace()
  for i in (1,2):
   x=i*4;c=m.add_circle((x,0),2,dxfattribs={'layer':'supply'});line=m.add_line((x,0),(x,10),dxfattribs={'layer':'supply'});bid='BS'+str(i)
   self.graph['boundary_anchors'].append({'boundary_id':bid,'kind':'user_confirmed_non_node_source_boundary','system':'supply','x':x,'y':0,'source_circle_handle':c.dxf.handle,'source_pipe_handle':line.dxf.handle});self.graph['edges'].append({'edge_id':'ES'+str(i),'system':'supply','end_boundary_id':bid,'source_handles':[line.dxf.handle]});self.scope['upper'].append({'node_id':'US'+str(i),'system':'supply','center':[x+100+(200 if i==2 else 0),100,0],'in_existing_candidate_set':False})
  r=self.run_case();self.assertEqual(r['counts']['offset_exceptions'],1);self.assertFalse(r['mapping_ready'])
 def test_unbalanced_groups_not_silently_zipped(self):
  self.scope['upper'].pop()
  with self.assertRaises(ValueError):self.run_case()
if __name__=='__main__':unittest.main()
