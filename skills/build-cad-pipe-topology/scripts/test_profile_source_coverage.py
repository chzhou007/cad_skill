import unittest,ezdxf
from equipment_assemblies import snap_native_equipment_terminals,profile_native_assemblies
from source_profile_templates import install_templates,validate_template_fills
from exploded_templates import recover_exploded_templates
import pipe_geometry as pg

class ProfileSourceCoverage(unittest.TestCase):
 def setUp(self):pg.set_tolerance(.05)
 def tearDown(self):pg.set_tolerance(.5)
 def fixture(self):
  d=ezdxf.new();block=d.blocks.new('BODY');block.add_lwpolyline([(0,0),(100,0),(100,100),(0,100)],close=True);block.add_circle((50,50),30)
  for y in [20,40,60,80]:block.add_line((0,y),(100,y))
  body=d.modelspace().add_blockref('BODY',(0,0));return d,body
 def test_axial_source_contact_and_overshoot(self):
  d,_=self.fixture();rules=[{'source_block':'BODY','maximum_gap':5,'maximum_body_diagonal_ratio':.1}]
  for x in [98,102]:
   result,audit=snap_native_equipment_terminals(d,[{'a':(x,10),'b':(200,10),'handle':'P'}],rules);self.assertEqual(len(audit),1);self.assertAlmostEqual(result[0]['a'][0],100)
 def test_far_or_internal_pipe_not_bound(self):
  d,_=self.fixture();rules=[{'source_block':'BODY','maximum_gap':5,'maximum_body_diagonal_ratio':.1}]
  for a,b in [((106,10),(200,10)),((98,10),(90,10))]:
   result,audit=snap_native_equipment_terminals(d,[{'a':a,'b':b,'handle':'P'}],rules);self.assertEqual(audit,[])
 def test_ambiguous_native_contacts_not_bound(self):
  d,_=self.fixture();d.blocks['BODY'].add_line((102,0),(102,100));rules=[{'source_block':'BODY','maximum_gap':5,'maximum_body_diagonal_ratio':.1}]
  result,audit=snap_native_equipment_terminals(d,[{'a':(99,10),'b':(200,10),'handle':'P'}],rules);self.assertEqual(audit,[])
 def test_verified_block_gap_calibration_does_not_bypass_uniqueness(self):
  d,_=self.fixture();tag=d.modelspace().add_text('X-1',dxfattribs={'insert':(-60,50),'height':10});b={'equipment_tag':'X-1','source_handle':tag.dxf.handle,'x':-60,'y':50,'profile_candidates':[]};rules=[{'tag_regex':'X-[0-9]+','source_block':'BODY','maximum_tag_gap_text_heights':7,'maximum_tag_gap_body_diagonals':.5}]
  found,a=profile_native_assemblies(d,[b],[],set(),native_rules=rules);self.assertEqual(len(found),1)
  d.modelspace().add_blockref('BODY',(0,5));found,a=profile_native_assemblies(d,[b],[],set(),native_rules=rules);self.assertEqual(found,[]);self.assertEqual(a[0]['status'],'pending_ambiguous_native_assemblies')
 def template(self,omit_fill=False):
  d=ezdxf.new();m=d.modelspace();points=[((0,0),(0,10)),((0,10),(5,5)),((5,5),(10,10)),((10,10),(10,0)),((10,0),(0,0)),((5,5),(5,14))];handles=[]
  for a,b in points:handles.append(m.add_line(a,b).dxf.handle)
  h=m.add_hatch();h.paths.add_polyline_path([(0,0),(0,10),(5,5)],is_closed=True);handles.append(h.dxf.handle)
  for a,b in points:m.add_line((a[0]+100,a[1]),(b[0]+100,b[1]))
  if not omit_fill:
   h=m.add_hatch();h.paths.add_polyline_path([(100,0),(100,10),(105,5)],is_closed=True)
  cfg={'inline_types':{},'source_native_component_templates':[{'prototype_handles':handles,'label':'Unknown source assembly','type_code':'U'}]};rules=install_templates(d,cfg);items=recover_exploded_templates(d,cfg['exploded_template_blocks'],[]);return validate_template_fills(d,items,rules)
 def test_whole_native_template_with_fills(self):
  items,a=self.template();self.assertEqual(len(items),2);self.assertTrue(all(len(r['source_handles'])==7 for r in items))
 def test_missing_fill_remains_pending_not_partial_acceptance(self):
  items,a=self.template(omit_fill=True);self.assertEqual(len(items),1);self.assertTrue(any(x['status']=='pending_missing_or_ambiguous_native_fills'for x in a))
 def test_unknown_service_contact_requires_verified_source_group(self):
  from topology_normalization import snap_near_junction_endpoints
  segments=[{'a':(1,50),'b':(100,50),'system':'physical','source_system':'unclassified_water','source_layer':'N','handle':'A'},{'a':(0,0),'b':(0,100),'system':'physical','source_system':'unclassified_water','source_layer':'N','handle':'B'}];cfg={'maximum_gap':2,'maximum_ratio':.05,'discovery_maximum_gap':3}
  self.assertEqual(snap_near_junction_endpoints(segments,cfg)[1],[])
  cfg['verified_unknown_service_layers']=['N'];result,audit=snap_near_junction_endpoints(segments,cfg);self.assertEqual(len(audit),1);self.assertEqual(result[0]['a'],(0,50));self.assertEqual(result[0]['source_system'],'unclassified_water')
  segments[1]['source_layer']='OTHER';self.assertEqual(snap_near_junction_endpoints(segments,cfg)[1],[])
 def test_required_source_layer_gate_independent_of_configured_input(self):
  from source_coverage_gate import source_coverage_gate
  import tempfile
  from pathlib import Path
  d=ezdxf.new();d.modelspace().add_line((0,0),(1,0),dxfattribs={'layer':'MISSED'})
  cfg={'system_layers':{},'auxiliary_pipe_layer':'A','required_physical_candidate_layers':['MISSED']}
  with tempfile.TemporaryDirectory()as tmp:
   with self.assertRaises(ValueError):source_coverage_gate(d,{'nodes':[],'edges':[]},cfg,Path(tmp))
 def test_configured_duplicate_template_preserves_every_source_identity(self):
  d=ezdxf.new();m=d.modelspace();b=d.blocks.new('DUP');pairs=[((0,0),(0,10)),((0,0),(0,10)),((0,10),(5,5)),((5,5),(10,10)),((10,10),(10,0)),((10,0),(0,0))]
  for a,z in pairs:b.add_line(a,z);m.add_line(a,z)
  self.assertEqual(recover_exploded_templates(d,['DUP'],[]),[])
  result=recover_exploded_templates(d,['DUP'],[],duplicate_tolerant_blocks=['DUP']);self.assertEqual(len(result),1);self.assertEqual(len(result[0]['source_handles']),6)
 def test_native_circle_contact_requires_unique_multisegment_source_exit(self):
  d=ezdxf.new();b=d.blocks.new('ROUND');b.add_circle((0,0),100);d.modelspace().add_blockref('ROUND',(0,0));r=[{'source_block':'ROUND','maximum_gap':10,'maximum_body_diagonal_ratio':.1,'allow_native_circle_contacts':True,'allow_multisegment_source_exit':True}]
  segs=[{'a':(0,105),'b':(0,120),'handle':'A'},{'a':(0,120),'b':(0,200),'handle':'B'}]
  result,audit=snap_native_equipment_terminals(d,segs,r);self.assertEqual(len(audit),1);self.assertAlmostEqual(result[0]['a'][1],100)
  self.assertEqual(snap_native_equipment_terminals(d,[{'a':(0,95),'b':(0,90),'handle':'A'}],r)[1],[])
 def test_one_equipment_candidate_uses_its_own_bounds(self):
  d,_=self.fixture();d.modelspace().add_blockref('BODY',(1000,1000));rules=[{'source_block':'BODY','maximum_gap':5,'maximum_body_diagonal_ratio':.1,'allow_multisegment_source_exit':True}]
  self.assertEqual(snap_native_equipment_terminals(d,[{'a':(98,10),'b':(90,10),'handle':'A'}],rules)[1],[])
if __name__=='__main__':unittest.main(verbosity=2)
