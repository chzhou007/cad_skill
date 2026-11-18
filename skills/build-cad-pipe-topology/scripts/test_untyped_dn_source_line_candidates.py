import unittest,ezdxf
from untyped_dn_source_line_candidates import scan

def fixture():
 d=ezdxf.new();m=d.modelspace();t=m.add_text('DN80',dxfattribs={'layer':'空调平面','insert':(10,1),'height':5});l=m.add_line((0,0),(100,0),dxfattribs={'layer':'空调平面'});bulk={'source_sha256':'S','graph_sha256':'G','status':'native_dn_bulk_screen_candidates_only','graph_mutated':False,'hil_ready':False,'records':[{'text_handle':t.dxf.handle,'text':'DN80','position':[10,1],'status':'no_source_line_in_local_scope'}]};p={'source_sha256':'S','graph_sha256':'G','bulk_screen_sha256':'B','selections':[{'text_handle':t.dxf.handle,'line_handle':l.dxf.handle,'expected_text':'DN80','expected_layer':'空调平面'}]};return d,bulk,p

class UntypedDNTests(unittest.TestCase):
 def test_nearby_line_does_not_become_pipe(self):
  d,b,p=fixture();r=scan(d,b,p,'S','G','B');self.assertFalse(r['pipe_system_selected']);self.assertFalse(r['graph_mutated']);self.assertEqual(r['records'][0]['typed_modelspace_endpoint_contacts'],[])
 def test_typed_contact_is_evidence_not_connection(self):
  d,b,p=fixture();d.modelspace().add_line((100,0),(150,0),dxfattribs={'layer':'空调冷冻水供水'});r=scan(d,b,p,'S','G','B');self.assertEqual(len(r['records'][0]['typed_modelspace_endpoint_contacts']),1);self.assertFalse(r['pipe_system_selected'])
 def test_changed_layer_or_stale_source_rejected(self):
  d,b,p=fixture();p['selections'][0]['expected_layer']='other'
  with self.assertRaises(ValueError):scan(d,b,p,'S','G','B')
  with self.assertRaises(ValueError):scan(d,b,p,'S','changed','B')

if __name__=='__main__':unittest.main()
