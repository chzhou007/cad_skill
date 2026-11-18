import unittest,ezdxf
from source_annotation_references import attach
class ReferencesTest(unittest.TestCase):
 def setUp(self):
  d=ezdxf.new();m=d.modelspace();t=m.add_text('接至3F-A1',dxfattribs={'insert':(0,0)});self.doc=d;nodes=[];edges=[];targets=[]
  for i,service in enumerate(['supply','return']):
   y=10+i*10;leader=m.add_line((0,0),(10,y));line=m.add_line((0,y),(20,y));nid='U'+str(i);eid='E'+str(i);nodes.append({'node_id':nid,'source_endpoint_annotation':{'text':'3F-A1'}});edges.extend([{'edge_id':'B'+str(i),'start_node_id':nid,'end_node_id':'EQ','system':service},{'edge_id':eid,'start_node_id':'A','end_node_id':'B','system':service,'source_handles':[line.dxf.handle],'attribute_paths':[[[0,y],[20,y]]]}]);targets.append({'system':service,'leader_handle':leader.dxf.handle,'native_pipe_handle':line.dxf.handle,'point':[10,y],'graph_edges':[eid]})
  self.graph={'metadata':{'source_sha256':'S'},'nodes':nodes,'edges':edges};self.evidence={'source_sha256':'S','graph_sha256':'G','records':[{'label':'3F-A1','source_note':'接至3F-A1','text_handle':t.dxf.handle,'endpoint_node_ids':['U0','U1'],'target_sources':targets}]}
 def test_attaches_without_connectivity_change(self):
  graph,a=attach(self.graph,self.doc,self.evidence,'S','G');self.assertEqual(a['groups'],1);self.assertEqual(len(graph['edges']),len(self.graph['edges']));self.assertFalse(graph['nodes'][0]['source_annotation_reference']['hydraulic_connection_confirmed'])
 def test_rejects_source_change(self):
  with self.assertRaises(ValueError):attach(self.graph,self.doc,self.evidence,'S','other')
 def test_rejects_moved_leader_contact(self):
  self.evidence['records'][0]['target_sources'][0]['point']=[11,10]
  with self.assertRaises(ValueError):attach(self.graph,self.doc,self.evidence,'S','G')
if __name__=='__main__':unittest.main()
