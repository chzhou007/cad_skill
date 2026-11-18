import unittest,ezdxf
from proxy_object_owner_inventory import trace,inventory

class Namespace:
 def __init__(self,handle,owner):self.handle=handle;self.owner=owner
 def get(self,key,default=None):return getattr(self,key,default)
class Entity:
 def __init__(self,handle,owner,kind):self.dxf=Namespace(handle,owner);self.kind=kind
 def dxftype(self):return self.kind
class ProxyOwnerInventoryTest(unittest.TestCase):
 def test_owner_chain_and_cycle(self):
  doc=ezdxf.new();line=doc.modelspace().add_line((0,0),(1,0));p=Entity('P','D','ACAD_PROXY_OBJECT');d=Entity('D',line.dxf.handle,'DICTIONARY');db={'D':d,line.dxf.handle:line};chain,status=trace(db,p);self.assertEqual(status,'graphic_ancestor');self.assertEqual(chain[-1]['handle'],line.dxf.handle)
  d.dxf.owner='P';self.assertEqual(trace(db,p)[1],'owner_cycle')
 def test_no_proxy_does_not_claim_complete_source(self):
  doc=ezdxf.new();r=inventory(doc,'S',{'source_sha256':'S','records':[]});self.assertEqual(r['proxy_object_count'],0);self.assertFalse(r['human_accepted']);self.assertTrue(any('completeness' in x for x in r['limitations']))
  with self.assertRaises(ValueError):inventory(doc,'S',{'source_sha256':'wrong','records':[]})
if __name__=='__main__':unittest.main()
