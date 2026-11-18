import unittest,ezdxf
from native_dn_text_position import supported

class NativeDNTextPositionTest(unittest.TestCase):
 def setUp(self):self.d=ezdxf.new();self.t=self.d.modelspace().add_text('DN80',dxfattribs={'insert':(1,2),'height':10})
 def test_default_and_rotation_supported(self):
  self.assertTrue(supported(self.t));self.t.dxf.rotation=90;self.assertTrue(supported(self.t))
 def test_transformed_or_invisible_text_not_supported(self):
  for key,value in [('halign',1),('valign',2),('oblique',12),('invisible',1),('text_generation_flag',2),('extrusion',(0,0,-1))]:
   with self.subTest(key=key):
    self.setUp();setattr(self.t.dxf,key,value);self.assertFalse(supported(self.t))
 def test_mtext_not_supported(self):self.assertFalse(supported(self.d.modelspace().add_mtext('DN80')))
if __name__=='__main__':unittest.main()
