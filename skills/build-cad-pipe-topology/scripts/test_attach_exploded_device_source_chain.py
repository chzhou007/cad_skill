import copy,unittest
from attach_exploded_device_source_chain import attach
from native_exploded_device_joint_evidence import collect
from test_native_exploded_device_joint_evidence import ExplodedDeviceJointTests

class AttachExplodedChainTests(unittest.TestCase):
 def setUp(self):
  f=ExplodedDeviceJointTests();f.setUp();self.f=f;f.g['edges'][0].update(path_length_complete=False,physical_length='unknown',path_length=10);self.ev=collect(f.doc,f.g,f.inv,f.p,f.h);self.ev.update(f.h)
 def test_attachment_retains_original_topology_paths_lengths_and_input(self):
  f=self.f;before=copy.deepcopy(f.g);out=attach(f.doc,f.g,f.inv,f.p,f.h,self.ev,'sha');edge=out['edges'][0];self.assertEqual(f.g,before);self.assertEqual(edge['attribute_paths'],before['edges'][0]['attribute_paths']);self.assertEqual(edge['path_length'],10);self.assertFalse(edge['source_exploded_device_chain']['physical_port_verified']);self.assertEqual(edge['source_exploded_device_chain']['physical_length'],'unknown');self.assertFalse(out['metadata']['hil_ready'])
 def test_stale_tampered_or_complete_length_rejected(self):
  f=self.f;e=copy.deepcopy(self.ev);e['records'][0]['inner_line_handle']='wrong'
  with self.assertRaises(ValueError):attach(f.doc,f.g,f.inv,f.p,f.h,e,'sha')
  f.g['edges'][0]['path_length_complete']=True
  with self.assertRaises(ValueError):attach(f.doc,f.g,f.inv,f.p,f.h,self.ev,'sha')
 def test_preexisting_extension_rejected(self):
  f=self.f;f.g['edges'][0]['source_exploded_device_chain']={}
  with self.assertRaises(ValueError):attach(f.doc,f.g,f.inv,f.p,f.h,self.ev,'sha')
if __name__=='__main__':unittest.main()
