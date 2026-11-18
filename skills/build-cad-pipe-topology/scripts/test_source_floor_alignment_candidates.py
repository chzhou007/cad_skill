import copy,unittest,ezdxf
from source_floor_alignment_candidates import attach

class FloorAlignmentTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();floorrows=[]
  for k in range(1,6):
   t=m.add_text('Floor '+str(k));floorrows.append({'floor':'F'+str(k),'title_handle':t.dxf.handle,'title_text':t.dxf.text})
  self.f={'source_sha256':'s','graph_sha256':'g','records':floorrows};self.grid={'source_sha256':'s','building_sha256':'b','pitch_native_units':100,'matches':[{'normalized_position':[i,i],'members':[{'floor':'F'+str(k)}for k in range(1,6)]}for i in range(3)]}
  nodes=[];members=[]
  for k in (4,5):
   y=-(5-k)*100;a=m.add_circle((10,y),10);b=m.add_circle((10,y),15);handles=[a.dxf.handle,b.dxf.handle];nid='U'+str(k)
   nodes.append({'node_id':nid,'node_type':'virtual_equipment','floor':'F'+str(k),'system':'supply','source_concentric_candidate':{'center':[10,y],'source_circle_handles':handles}});members.append({'node_id':nid,'floor':'F'+str(k),'center':[10,y],'rings':handles})
  self.g={'metadata':{'source_sha256':'s'},'nodes':nodes,'edges':[{'edge_id':'E','start_node_id':'A','end_node_id':'B'}]};self.ev={'source_sha256':'s','current_graph_sha256':'g','derived_floor_pitch_native_units':100,'groups':[{'normalized_key':[10,0,'supply',[10,15]],'members':members}]}
 def call(self):return attach(self.g,self.ev,self.f,self.grid,'b','s','g',self.doc,pitch=100)
 def test_group_preserves_physical_graph(self):
  before=copy.deepcopy(self.g);out,v=self.call();self.assertEqual(self.g,before);self.assertEqual(out['edges'],before['edges']);self.assertEqual(v['member_nodes'],2);self.assertEqual(len(out['sourceFloorAlignmentCandidates']),1);self.assertFalse(out['metadata']['hil_ready'])
 def test_wrong_shape_or_system_or_source_fails(self):
  self.g['nodes'][0]['system']='return'
  with self.assertRaises(ValueError):self.call()
  self.g['nodes'][0]['system']='supply';self.ev['groups'][0]['members'][0]['center'][0]+=1
  with self.assertRaises(ValueError):self.call()
  self.ev['groups'][0]['members'][0]['center'][0]-=1;self.grid['building_sha256']='bad'
  with self.assertRaises(ValueError):self.call()
 def test_insufficient_independent_alignment_fails(self):
  self.grid['matches']=self.grid['matches'][:2]
  with self.assertRaisesRegex(ValueError,'Insufficient independent'):self.call()

if __name__=='__main__':unittest.main()
