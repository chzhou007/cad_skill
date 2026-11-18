import copy,unittest
import ezdxf
from source_direct_dn_evidence import collect

def fixture():
 doc=ezdxf.new();space=doc.modelspace();line=space.add_line((0,0),(100,0),dxfattribs={'layer':'空调冷冻水供水'});text=space.add_text('DN200(3.000)',dxfattribs={'insert':(40,2),'height':5,'layer':'空调平面'});graph={'metadata':{'source_sha256':'SRC'},'nodes':[],'edges':[{'edge_id':'E1','system':'supply','source_handles':[line.dxf.handle],'attribute_paths':[[[0,0],[100,0]]]}]};policy={'source_id':'S','source_sha256':'SRC','graph_sha256':'GRAPH','text_layers':['空调平面'],'selections':[{'text_handle':text.dxf.handle,'expected_text':'DN200(3.000)','edge_id':'E1','source_line_handle':line.dxf.handle}]};return doc,graph,policy,line,text

class NativeDirectDNTest(unittest.TestCase):
 def test_aligned_text_insert_is_not_used_as_source_position(self):
  doc,g,p,line,text=fixture();text.dxf.halign=2
  with self.assertRaisesRegex(ValueError,'unsupported text transform'):collect(doc,g,p,'SRC','GRAPH')
 def test_candidate_and_graph_unchanged(self):
  doc,g,p,line,text=fixture();before=copy.deepcopy(g);r=collect(doc,g,p,'SRC','GRAPH');self.assertEqual(g,before);self.assertEqual(r['status'],'candidate_not_accepted');x=r['observations'][0];self.assertEqual(x['nominal_mm'],200);self.assertEqual(x['parenthesized_source_value'],'3.000');self.assertFalse(r['hil_ready'])
 def test_bad_hashes_and_altered_text_rejected(self):
  doc,g,p,line,text=fixture()
  for a,b in [('WRONG','GRAPH'),('SRC','WRONG')]:
   with self.assertRaises(ValueError):collect(doc,g,p,a,b)
  text.dxf.text='DN150(3.000)'
  with self.assertRaisesRegex(ValueError,'source text mismatch'):collect(doc,g,p,'SRC','GRAPH')
 def test_unmodeled_closer_parallel_source_line_blocks(self):
  doc,g,p,line,text=fixture();doc.modelspace().add_line((0,3),(100,3),dxfattribs={'layer':'空调冷冻水回水'})
  with self.assertRaisesRegex(ValueError,'native source pipe match'):collect(doc,g,p,'SRC','GRAPH')
 def test_ambiguous_graph_and_wrong_source_layer_block(self):
  doc,g,p,line,text=fixture();g['edges'].append({'edge_id':'E2','system':'return','source_handles':[],'attribute_paths':[[[0,4],[100,4]]]})
  with self.assertRaisesRegex(ValueError,'ambiguous'):collect(doc,g,p,'SRC','GRAPH')
  doc,g,p,line,text=fixture();line.dxf.layer='空调冷冻水回水'
  with self.assertRaisesRegex(ValueError,'line or system'):collect(doc,g,p,'SRC','GRAPH')
 def test_conflicting_labels_and_duplicate_policy_block(self):
  doc,g,p,line,text=fixture();doc.modelspace().add_text('DN150',dxfattribs={'insert':(60,2),'height':5,'layer':'空调平面'})
  with self.assertRaisesRegex(ValueError,'conflicting'):collect(doc,g,p,'SRC','GRAPH')
  doc,g,p,line,text=fixture();p['selections'].append(dict(p['selections'][0]))
  with self.assertRaisesRegex(ValueError,'duplicate'):collect(doc,g,p,'SRC','GRAPH')

 def test_composite_or_qualified_dn_blocks_nearby_edge(self):
  for value in ('DN300(3.600)/DN200(3.000)','CHWS1 DN450'):
   doc,g,p,line,text=fixture();doc.modelspace().add_text(value,dxfattribs={'insert':(60,2),'height':5,'layer':'空调平面'})
   with self.assertRaisesRegex(ValueError,'unparsed DN annotation'):collect(doc,g,p,'SRC','GRAPH')
  doc,g,p,line,text=fixture();doc.modelspace().add_text('DN300/DN200',dxfattribs={'insert':(60,100),'height':5,'layer':'空调平面'})
  self.assertEqual(collect(doc,g,p,'SRC','GRAPH')['status'],'candidate_not_accepted')

if __name__=='__main__':unittest.main()
