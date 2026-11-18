import unittest,json
import ezdxf
from source_evidence import attributes,terminal_geometry
import test_new_drawings as fixture

class NativeMetadata(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new('R2018');b=self.doc.blocks.new('VALVE');b.add_line((0,0),(1,0));self.owner=self.doc.modelspace().add_blockref('VALVE',(0,0));a=self.owner.add_attrib('TYPE','无值',dxfattribs={'flags':1});c=self.owner.add_attrib('COUNT','2',dxfattribs={'flags':1});self.row={'source_top_handle':self.owner.dxf.handle,'source_attributes':[{'source_handle':x.dxf.handle,'tag':x.dxf.tag,'text':x.dxf.text,'invisible':True}for x in (a,c)]}
 def test_raw_chinese_and_count_are_preserved_as_metadata(self):
  self.assertEqual(attributes(self.doc,self.row),self.row['source_attributes']);self.assertEqual(self.row['source_attributes'][0]['text'],'无值');self.assertNotIn('quantity',self.row)
 def test_attribute_of_another_instance_is_rejected(self):
  other=self.doc.modelspace().add_blockref('VALVE',(10,0));self.row['source_top_handle']=other.dxf.handle
  with self.assertRaisesRegex(ValueError,'not attached'):attributes(self.doc,self.row)
 def test_unreadable_or_changed_native_value_is_rejected(self):
  self.row['source_attributes'][0]['text']='\ufffd'
  with self.assertRaises(ValueError):attributes(self.doc,self.row)

class GlyphBuilder(unittest.TestCase):
 build=fixture.NewDrawingViewerContract.build
 tearDown=fixture.NewDrawingViewerContract.tearDown
 def setUp(self):
  fixture.NewDrawingViewerContract.setUp(self);d=ezdxf.readfile(self.root/'demo.dxf');s=d.modelspace().add_spline([(0,0),(.001,.0005),(.002,-.0005),(.003,0)]);d.saveas(self.root/'demo.dxf');g=json.loads((self.root/'graph.json').read_text());n=g['nodes'][-1];n.update(node_type='virtual_equipment',boundary_type='source_native_wave_terminal',source_terminal_glyph_ids=['WAVE-1'],ports=[{'port_id':'END-P1','system':'supply','x':n['x'],'y':n['y']}]);g['edges'][-1]['end_port_id']='END-P1';self.glyph=dict(id='WAVE-1',source_handles=[s.dxf.handle],node_id=n['node_id'],edge_id=g['edges'][-1]['edge_id'],floor=n['floor'],system='supply',remote_continuation_confirmed=False);g['sourceTerminalGlyphs']=[self.glyph];self.graph=g;(self.root/'graph.json').write_text(json.dumps(g))
 def test_native_glyph_is_built_and_fidelity_gate_detects_omission(self):
  from post_drawing_gate import check
  ret=self.build();self.assertEqual(ret.returncode,0,ret.stderr);p=self.out/'public/data/graph.json';g=json.loads(p.read_text('utf8'));self.assertTrue(g['sourceTerminalGlyphs'][0]['sourceGeometry']);self.assertEqual(len(g['edges']),3);g['sourceTerminalGlyphs'][0]['sourceGeometry']=[];p.write_text(json.dumps(g),'utf8');self.assertEqual(check(self.out,self.root/'demo.dxf')['machine_status'],'FAIL')
 def test_glyph_cannot_be_owned_by_a_distant_edge(self):
  self.glyph['edge_id']='P-A';(self.root/'graph.json').write_text(json.dumps(self.graph));ret=self.build();self.assertNotEqual(ret.returncode,0);self.assertIn('adjacent node/edge',ret.stderr)
 def test_native_glyph_does_not_confirm_a_remote_connection(self):
  self.glyph['remote_continuation_confirmed']=True;(self.root/'graph.json').write_text(json.dumps(self.graph));ret=self.build();self.assertNotEqual(ret.returncode,0);self.assertIn('does not confirm',ret.stderr)

class DownturnNativeGeometry(unittest.TestCase):
 def test_circle_geometry_and_wrong_center_or_owner(self):
  doc=ezdxf.new('R2018');circle=doc.modelspace().add_circle((3,4),2,dxfattribs={'layer':'water'});handle=circle.dxf.handle
  n={'node_id':'U','node_type':'virtual_equipment','x':3,'y':4,'floor':'Roof','source_terminal_glyph_ids':['DOWNTURN-'+handle],
     'source_downturn_evidence':{'circle_handle':handle,'pipe_handle':'L1','source_layer':'water'}}
  e={'edge_id':'E','start_node_id':'U','end_node_id':'T','system':'return','source_handles':['L1']}
  glyph={'id':'DOWNTURN-'+handle,'kind':'native_downturn_terminal','source_handles':[handle],'node_id':'U','edge_id':'E','floor':'Roof','system':'return','remote_continuation_confirmed':False}
  self.assertTrue(terminal_geometry(doc,glyph,{'U':n},{'E':e}))
  n['x']=4
  with self.assertRaisesRegex(ValueError,'centered'):terminal_geometry(doc,glyph,{'U':n},{'E':e})
  n['x']=3;n['source_downturn_evidence']['pipe_handle']='other'
  with self.assertRaisesRegex(ValueError,'identity'):terminal_geometry(doc,glyph,{'U':n},{'E':e})

class ConcentricNativeGeometry(unittest.TestCase):
 def test_two_native_circles_and_terminal_witness(self):
  doc=ezdxf.new('R2018');m=doc.modelspace();a=m.add_circle((0,0),10,dxfattribs={'layer':'P'});b=m.add_circle((0,0),15,dxfattribs={'layer':'P'});line=m.add_line((15,0),(50,0),dxfattribs={'layer':'P'});handles=[a.dxf.handle,b.dxf.handle]
  n={'node_id':'U','node_type':'virtual_equipment','x':15,'y':0,'floor':'F1','source_terminal_glyph_ids':['C1'],'source_concentric_candidate':{'source_circle_handles':handles,'source_line_handle':line.dxf.handle,'center':[0,0],'radii':[10,15]}}
  e={'edge_id':'E','start_node_id':'U','end_node_id':'T','system':'return','source_handles':[line.dxf.handle]};glyph={'id':'C1','kind':'native_concentric_circle_candidate','source_handles':handles,'node_id':'U','edge_id':'E','floor':'F1','system':'return','remote_continuation_confirmed':False}
  self.assertEqual(len(terminal_geometry(doc,glyph,{'U':n},{'E':e})),2)
  n['x']=12
  with self.assertRaisesRegex(ValueError,'endpoint'):terminal_geometry(doc,glyph,{'U':n},{'E':e})

class TangentNativeGeometry(unittest.TestCase):
 def test_native_circle_pair_requires_source_line_and_distinct_service(self):
  doc=ezdxf.new('R2018');m=doc.modelspace();a=m.add_circle((0,0),10,dxfattribs={'layer':'s'});b=m.add_circle((0,20),10,dxfattribs={'layer':'r'});line=m.add_line((-20,0),(0,0),dxfattribs={'layer':'s'})
  n={'node_id':'S','node_type':'virtual_equipment','system':'supply','x':0,'y':0,'floor':'F2','source_terminal_glyph_ids':['G'],'source_tangent_circle_candidate':{'source_circle_handle':a.dxf.handle,'source_line_handle':line.dxf.handle,'paired_circle_handle':b.dxf.handle,'paired_node_id':'R'}};peer={'node_id':'R','system':'return','floor':'F2'};e={'edge_id':'E','start_node_id':'S','end_node_id':'T','system':'supply','source_handles':[line.dxf.handle]};glyph={'id':'G','kind':'native_tangent_circle_candidate','source_handles':[a.dxf.handle],'node_id':'S','edge_id':'E','floor':'F2','system':'supply','remote_continuation_confirmed':False}
  self.assertTrue(terminal_geometry(doc,glyph,{'S':n,'R':peer},{'E':e}))
  peer['system']='supply'
  with self.assertRaisesRegex(ValueError,'geometry differs'):terminal_geometry(doc,glyph,{'S':n,'R':peer},{'E':e})

class InsertWaveNativeGeometry(unittest.TestCase):
 def test_source_insert_wave_requires_owned_pipe_and_contact(self):
  doc=ezdxf.new('R2018');block=doc.blocks.new('WAVE');block.add_lwpolyline([(-1,0),(1,0)]);ins=doc.modelspace().add_blockref('WAVE',(3,4));n={'node_id':'U','node_type':'virtual_equipment','system':'supply','x':3,'y':4,'floor':'F3','source_terminal_glyph_ids':['G'],'source_wave_insert_evidence':{'block_name':'WAVE','source_handle':ins.dxf.handle,'source_line_handle':'L','contact_tolerance':.1}};e={'edge_id':'E','start_node_id':'U','end_node_id':'T','system':'supply','source_handles':['L']};glyph={'id':'G','kind':'native_insert_wave_terminal','source_handles':[ins.dxf.handle],'node_id':'U','edge_id':'E','floor':'F3','system':'supply','remote_continuation_confirmed':False}
  self.assertTrue(terminal_geometry(doc,glyph,{'U':n},{'E':e}));n['x']=6
  with self.assertRaisesRegex(ValueError,'enclose terminal'):terminal_geometry(doc,glyph,{'U':n},{'E':e})

class ConfirmedInterfaceNativeGeometry(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new('R2018');m=self.doc.modelspace();c=m.add_circle((3,4),1,dxfattribs={'layer':'空调冷冻水供水'});ls=[m.add_line((i,0),(i,1),dxfattribs={'layer':'空调立管、水平支管'}) for i in range(4)];handles=[c.dxf.handle]+[x.dxf.handle for x in ls]
  original={'node_id':'V1','node_type':'virtual_equipment','subtype':'out_of_plane_interface','floor':2,'system':'supply','x':3,'y':4,'source_handle':c.dxf.handle,'source_handles':handles}
  self.n={'node_id':'D','node_type':'equipment','floor':2};self.e={'edge_id':'E','start_node_id':'T','end_node_id':'D','system':'supply','path_points':[[3,0],[3,4]],'confirmed_equipment_interface':{'original_interface':original,'interface_side':'end','confirmation':{'confirmed_by':'user','answer':'yes'},'physical_port_verified':False,'interface_to_equipment_length_known':False}}
  self.g={'id':'CONFIRMED-V1','kind':'confirmed_equipment_interface','node_id':'D','edge_id':'E','original_interface_id':'V1','source_handles':handles,'floor':2,'system':'supply'}
 def call(self):return terminal_geometry(self.doc,self.g,{'D':self.n},{'E':self.e})
 def test_source_marker_retained_without_fabricating_port(self):self.assertEqual(len(self.call()),5)
 def test_wrong_edge_endpoint_and_system_fail_closed(self):
  self.e['path_points'][-1]=[8,4]
  with self.assertRaises(ValueError):self.call()
  self.e['path_points'][-1]=[3,4];self.g['system']='return'
  with self.assertRaises(ValueError):self.call()
 def test_cannot_claim_unverified_physical_port(self):
  self.e['confirmed_equipment_interface']['physical_port_verified']=True
  with self.assertRaises(ValueError):self.call()

class SourceSystemConflictGlyph(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new('R2018');m=self.doc.modelspace();circle=m.add_circle((3,4),1,dxfattribs={'layer':'空调冷冻水回水'});pipe=m.add_line((0,4),(3,4),dxfattribs={'layer':'空调冷冻水供水'});lines=[m.add_line((i,0),(i,1),dxfattribs={'layer':'空调立管、水平支管'}) for i in range(4)];handles=[circle.dxf.handle]+[l.dxf.handle for l in lines]
  evidence={'status':'source_system_conflict_unresolved','remote_connection':'unknown','edge_id':'E','circle_handle':circle.dxf.handle,'circle_source_system':'return','circle_source_layer':'空调冷冻水回水','glyph_handles':handles[1:],'pipe_handle':pipe.dxf.handle,'pipe_source_system':'supply','pipe_source_layer':'空调冷冻水供水'}
  self.n={'node_id':'U','node_type':'virtual_equipment','floor':2,'x':3,'y':4,'source_glyph_system_conflict':evidence};self.e={'edge_id':'E','start_node_id':'T','end_node_id':'U','system':'supply','path_points':[[0,4],[3,4]],'source_handles':[pipe.dxf.handle]};self.g={'id':'CONFLICT-U','kind':'native_system_conflict','node_id':'U','edge_id':'E','source_handles':handles,'floor':2,'system':'supply','remote_continuation_confirmed':False}
 def call(self):return terminal_geometry(self.doc,self.g,{'U':self.n},{'E':self.e})
 def test_native_marker_is_preserved_with_conflict(self):self.assertEqual(len(self.call()),5)
 def test_wrong_layer_and_remote_confirmation_rejected(self):
  self.g['remote_continuation_confirmed']=True
  with self.assertRaises(ValueError):self.call()
  self.g['remote_continuation_confirmed']=False;self.n['source_glyph_system_conflict']['circle_source_system']='supply'
  with self.assertRaises(ValueError):self.call()
 def test_mismatched_source_contact_rejected(self):
  self.n['x']=5
  with self.assertRaises(ValueError):self.call()
