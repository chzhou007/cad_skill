import copy,unittest
import ezdxf
from native_exploded_device_joint_evidence import collect
from native_nested_joint_evidence import fingerprint
from native_line_path_evidence import LAYERS

class ExplodedDeviceJointTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();block=self.doc.blocks.new('J')
  for x in (0,10):block.add_line((x,-1),(x,1))
  for i in range(4):block.add_arc((i,5),1,0,90)
  self.j=m.add_blockref('J',(0,0));self.a=m.add_line((-10,0),(0,0),dxfattribs={'layer':LAYERS['supply']});self.b=m.add_line((10,0),(20,0),dxfattribs={'layer':LAYERS['supply']});self.c=m.add_circle((-10,0),2)
  self.g={'nodes':[{'node_id':'D','node_type':'equipment'},{'node_id':'T','node_type':'tee'}],'edges':[{'edge_id':'E','system':'supply','device_label':'D','start_node_id':'D','end_node_id':'T','attribute_paths':[[[10,0],[20,0]]],'equipment_inventory':[{'equipment_type':'金属软接','count':1,'device_names':['J1']}]}]}
  self.inv=[{'source_top_handle':self.j.dxf.handle,'assignment_status':'assigned','edge_id':'E','owner_equipment':'D','equipment_type':'金属软接','device_name':'J1'}];self.h={'source_sha256':'s','graph_sha256':'g','inventory_sha256':'i'}
  self.p=dict(self.h,joint_block='J',block_fingerprint_sha256=fingerprint(block),selections=[{'equipment_id':'D','edge_id':'E','system':'supply','joint_handle':self.j.dxf.handle,'inner_line':self.a.dxf.handle,'outer_line':self.b.dxf.handle,'circle_handle':self.c.dxf.handle}])
 def test_witnessed_chain_remains_unaccepted(self):
  before=copy.deepcopy(self.g);r=collect(self.doc,self.g,self.inv,self.p,self.h);self.assertEqual(len(r['records']),1);self.assertFalse(r['records'][0]['physical_port_verified']);self.assertEqual(r['records'][0]['physical_length'],'unknown');self.assertEqual(self.g,before)
 def test_stale_and_wrong_ownership_rejected(self):
  with self.assertRaises(ValueError):collect(self.doc,self.g,self.inv,self.p,dict(self.h,graph_sha256='old'))
  self.inv[0]['edge_id']='other'
  with self.assertRaises(ValueError):collect(self.doc,self.g,self.inv,self.p,self.h)
 def test_competing_other_system_line_rejected(self):
  self.doc.modelspace().add_line((0,0),(0,10),dxfattribs={'layer':LAYERS['return']})
  with self.assertRaisesRegex(ValueError,'competing'):collect(self.doc,self.g,self.inv,self.p,self.h)
 def test_circle_and_graph_source_line_are_required(self):
  self.c.dxf.center=(-11,0)
  with self.assertRaises(ValueError):collect(self.doc,self.g,self.inv,self.p,self.h)
  self.c.dxf.center=(-10,0);self.g['edges'][0]['attribute_paths']=[[[11,0],[20,0]]]
  with self.assertRaises(ValueError):collect(self.doc,self.g,self.inv,self.p,self.h)
if __name__=='__main__':unittest.main()
