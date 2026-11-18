import types,unittest
from proxy_metadata_inventory import inventory
class Tag:
 def __init__(self,c,v):self.code=c;self.value=v
class Obj:
 def __init__(self,name,kind='CLASS'):self.dxf=types.SimpleNamespace(name=name,cpp_class_name='CPP-'+name);self._kind=kind
 def dxftype(self):return self._kind
class Proxy:
 def __init__(self,id):self.dxf=types.SimpleNamespace(handle='AB',layer='L');self.acdb_proxy_entity=[Tag(91,id),Tag(340,'B')];self.proxy_graphic=b'\x08\0\0\0\0\0\0\0'
 def dxftype(self):return 'ACAD_PROXY_ENTITY'
class ProxyInventory(unittest.TestCase):
 def test_candidates_refs_empty_graphic_and_unknown(self):
  d=types.SimpleNamespace(classes=types.SimpleNamespace(classes={'x':Obj('TEXT')}),modelspace=lambda:[Proxy(500),Proxy(999)],entitydb={'B':Obj('VALVE','BLOCK_RECORD')});r=inventory(d);self.assertEqual(r['records'][0]['ordinal_class_candidate'],'TEXT');self.assertEqual(r['records'][0]['references'][0]['block_name'],'VALVE');self.assertTrue(r['records'][0]['empty_graphic_header_only']);self.assertIsNone(r['records'][1]['ordinal_class_candidate']);self.assertEqual(r['records'][1]['class_mapping_status'],'unresolved')
if __name__=='__main__':unittest.main()
