import copy,unittest,ezdxf
from source_concentric_terminal_glyphs import reconcile

class ConcentricGlyphTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();layer='P';a=m.add_circle((0,0),10,dxfattribs={'layer':layer});b=m.add_circle((0,0),15,dxfattribs={'layer':layer});line=m.add_line((15,0),(50,0),dxfattribs={'layer':layer});self.a=a;self.b=b;self.line=line
  self.g={'metadata':{'source_sha256':'s'},'nodes':[{'node_id':'U','node_type':'virtual_equipment','boundary_type':'unresolved_source_terminal','x':15,'y':0,'floor':'F1','ports':[{'port_id':'P'}]},{'node_id':'T','node_type':'tee'}],'edges':[{'edge_id':'E','start_node_id':'U','end_node_id':'T','system':'return','source_handles':[line.dxf.handle]}]}
  self.ev={'source_sha256':'s','graph_sha256':'g','assemblies_examined':1,'records':[{'node_id':'U','edge_id':'E','floor':'F1','system':'return','center':[0,0],'rings':[{'handle':a.dxf.handle,'radius':10},{'handle':b.dxf.handle,'radius':15}],'native_contacts':[{'line_handle':line.dxf.handle,'side':'start'}]}]}
 def call(self):return reconcile(self.g,self.ev,'s','g',self.doc)
 def test_local_glyph_does_not_modify_connectivity(self):
  old=copy.deepcopy(self.g);out,v=self.call();self.assertEqual(self.g,old);self.assertEqual(out['edges'],old['edges']);self.assertEqual(out['nodes'][0]['ports'],old['nodes'][0]['ports']);self.assertEqual(v['glyphs_added'],1);self.assertFalse(out['sourceTerminalGlyphs'][0]['remote_continuation_confirmed']);self.assertEqual(out['nodes'][0]['boundary_type'],'unresolved_source_terminal')
 def test_stale_source_shape_or_additional_contact_rejected(self):
  with self.assertRaises(ValueError):reconcile(self.g,self.ev,'s','wrong',self.doc)
  self.b.dxf.radius=16
  with self.assertRaises(ValueError):self.call()
  self.b.dxf.radius=15;self.doc.modelspace().add_line((-15,0),(-50,0),dxfattribs={'layer':'P'})
  with self.assertRaisesRegex(ValueError,'Competing native circle contacts'):self.call()
 def test_competing_glyph_or_wrong_edge_rejected(self):
  self.g['nodes'][0]['source_terminal_glyph_ids']=['OTHER']
  with self.assertRaises(ValueError):self.call()
  self.g['nodes'][0].pop('source_terminal_glyph_ids');self.g['edges'][0]['source_handles']=[]
  with self.assertRaises(ValueError):self.call()

if __name__=='__main__':unittest.main()
