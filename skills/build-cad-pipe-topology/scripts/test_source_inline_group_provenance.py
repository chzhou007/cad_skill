import unittest,copy
from source_inline_group_provenance import attach
class ProvenanceTest(unittest.TestCase):
 def setUp(self):
  gr={'group_id':'G','edge_id':'E','source_insert_handle':'I','endpoint_node_ids':['U']};self.g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'U','source_inline_endpoint_group':copy.deepcopy(gr)}],'edges':[{'edge_id':'E','source_handles':['L'],'source_inline_endpoint_group':copy.deepcopy(gr)}],'sourceInlineEndpointGroups':[copy.deepcopy(gr)]};self.ev={'source_sha256':'S','graph_sha256':'G0','primary_dxf_sha256':'P','reference_dxf_sha256':'R','records':[{'group_id':'G','edge_id':'E','normalized_insert_handle':'I','endpoint_node_ids':['U'],'reference_insert_handle':'RI','reference_block_name':'B','primary_source_lines':[{'normalized_handle':'L','primary_polyline_handle':'PL'}],'individual_primary_proxy_identity':'not_established'}]}
 def test_provenance_retains_uncertain_proxy(self):
  o,a=attach(self.g,self.ev,'S','G0');self.assertEqual(a['groups'],1);self.assertEqual(o['nodes'][0]['source_inline_endpoint_group']['source_provenance']['individual_primary_proxy_identity'],'not_established');self.assertNotIn('source_provenance',self.g['sourceInlineEndpointGroups'][0])
 def test_rejects_stale_or_fabricated_identity(self):
  with self.assertRaises(ValueError):attach(self.g,self.ev,'S','other')
  self.ev['records'][0]['individual_primary_proxy_identity']='proven'
  with self.assertRaises(ValueError):attach(self.g,self.ev,'S','G0')
 def test_rejects_changed_line(self):
  self.ev['records'][0]['primary_source_lines'][0]['normalized_handle']='OTHER'
  with self.assertRaises(ValueError):attach(self.g,self.ev,'S','G0')
if __name__=='__main__':unittest.main()
