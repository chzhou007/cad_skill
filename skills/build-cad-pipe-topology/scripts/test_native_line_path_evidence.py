import copy,unittest,ezdxf
from native_line_path_evidence import collect

def fixture():
 d=ezdxf.new();m=d.modelspace();a=m.add_line((0,0),(15,0),dxfattribs={'layer':'空调冷冻水供水'});b=m.add_line((10,0),(10,10),dxfattribs={'layer':'空调冷冻水供水'});g={'edges':[{'edge_id':'E','system':'supply','connection_mode':'continuous_original_cad_pipe','attribute_paths':[[[0,0],[10,0],[10,10]]]}]};p={'source_sha256':'S','graph_sha256':'G','selections':[{'edge_id':'E','line_handles':[a.dxf.handle,b.dxf.handle]}]};return d,g,p
class NativeLinePathTest(unittest.TestCase):
 def test_native_full_and_partial_lines(self):
  d,g,p=fixture();before=copy.deepcopy(g);r=collect(d,g,p,'S','G');self.assertEqual(g,before);self.assertEqual(len(r['edges'][0]['segments']),2);self.assertFalse(r['hil_ready'])
 def test_missing_source_and_ambiguous_duplicate_rejected(self):
  d,g,p=fixture();d.modelspace().add_line((0,0),(10,0),dxfattribs={'layer':'空调冷冻水供水'})
  with self.assertRaisesRegex(ValueError,'ambiguous'):collect(d,g,p,'S','G')
  d,g,p=fixture();p['selections'][0]['line_handles'][0]='bad'
  with self.assertRaisesRegex(ValueError,'missing'):collect(d,g,p,'S','G')
 def test_hash_system_and_paths_fail_closed(self):
  d,g,p=fixture()
  with self.assertRaisesRegex(ValueError,'hash'):collect(d,g,p,'bad','G')
  g['edges'][0]['system']='return'
  with self.assertRaisesRegex(ValueError,'missing'):collect(d,g,p,'S','G')
  d,g,p=fixture();g['edges'][0]['attribute_paths'][0][1]=[10,1]
  with self.assertRaisesRegex(ValueError,'missing'):collect(d,g,p,'S','G')
 def test_duplicate_graph_ids_rejected(self):
  d,g,p=fixture();g['edges'].append(copy.deepcopy(g['edges'][0]))
  with self.assertRaisesRegex(ValueError,'duplicate graph'):collect(d,g,p,'S','G')
if __name__=='__main__':unittest.main()
