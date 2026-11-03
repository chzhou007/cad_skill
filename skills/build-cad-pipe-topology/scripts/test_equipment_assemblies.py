import unittest,ezdxf
from equipment_assemblies import profile_native_assemblies,primitive_distance
from auxiliary_pipes import recover_inline_source_spans,physical_auxiliary_geometry
class EquipmentCoverageContract(unittest.TestCase):
 def fixture(self):
  d=ezdxf.new();b=d.blocks.new('NATIVE_UNIT')
  for a,z in [((0,0),(120,0)),((120,0),(120,150)),((120,150),(0,150)),((0,150),(0,0)),((30,100),(30,170)),((90,100),(90,170))]:b.add_line(a,z)
  for p in [(30,40),(90,40),(30,100),(90,100)]:b.add_circle(p,12)
  ins=d.modelspace().add_blockref('NATIVE_UNIT',(0,0));tag=d.modelspace().add_text('UNIT-1',dxfattribs={'insert':(20,-15),'height':10});bind={'equipment_tag':'UNIT-1','source_handle':tag.dxf.handle,'x':20,'y':-15,'profile_candidates':['UNIT-PROFILE']};profiles=[{'profile_id':'UNIT-PROFILE','label':'Pressurization Unit'}];return d,ins,bind,profiles
 def test_complete_assembly_collapses_to_one_node_candidate(self):
  d,e,b,p=self.fixture();found,a=profile_native_assemblies(d,[b],p,set());self.assertEqual(len(found),1);self.assertEqual(found[0]['counts']['CIRCLE'],4);self.assertEqual(found[0]['binding']['equipment_tag'],'UNIT-1')
 def test_bare_circle_and_profile_tag_are_not_an_assembly(self):
  d,e,b,p=self.fixture();d.modelspace().delete_entity(e);bl=d.blocks.new('FALSE_UNIT');bl.add_circle((50,50),30);d.modelspace().add_blockref('FALSE_UNIT',(0,0));found,a=profile_native_assemblies(d,[b],p,set());self.assertEqual(found,[])
 def test_two_nearby_assemblies_remain_ambiguous(self):
  d,e,b,p=self.fixture();d.modelspace().add_blockref('NATIVE_UNIT',(20,0));found,a=profile_native_assemblies(d,[b],p,set());self.assertEqual(found,[]);self.assertIn('ambiguous',a[0]['status'])
 def test_missing_profile_not_silently_promoted(self):
  d,e,b,p=self.fixture();found,a=profile_native_assemblies(d,[b],[],set());self.assertEqual(found,[]);self.assertEqual(a[0]['status'],'pending_no_source_profile')
 def test_large_drawing_frame_is_not_equipment(self):
  d,e,b,p=self.fixture();d.modelspace().delete_entity(e);d.modelspace().add_blockref('NATIVE_UNIT',(0,0),dxfattribs={'xscale':100,'yscale':100});found,a=profile_native_assemblies(d,[b],p,set());self.assertEqual(found,[])
 def test_two_tags_cannot_claim_the_same_assembly(self):
  d,e,b,p=self.fixture();tag=d.modelspace().add_text('UNIT-2',dxfattribs={'insert':(50,-15),'height':10});b2=dict(b,equipment_tag='UNIT-2',source_handle=tag.dxf.handle,x=50);found,a=profile_native_assemblies(d,[b,b2],p,set());self.assertEqual(found,[]);self.assertTrue(all(x['status']=='pending_multiple_tags_claim_same_assembly'for x in a))
 def test_native_arc_boundary_is_a_real_port_contact(self):
  d=ezdxf.new();arc=d.modelspace().add_arc((0,0),100,0,90);self.assertAlmostEqual(primitive_distance((100,0),arc),0);self.assertGreater(primitive_distance((-100,0),arc),100)
 def test_true_auxiliary_quarter_bend_preserves_curved_source(self):
  d=ezdxf.new();a=d.modelspace().add_arc((0,0),100,0,90,dxfattribs={'layer':'AUX'});segs,jumps,audit=physical_auxiliary_geometry(list(d.modelspace()),'AUX');self.assertEqual(jumps,[]);self.assertEqual(len(segs),18);self.assertTrue(all(s['normalization']=='source_physical_quarter_bend'for s in segs))
 def circle_span(self,with_ink=True,both_tails=True):
  d=ezdxf.new();m=d.modelspace();m.add_circle((0,0),100)
  if with_ink:m.add_line((-60,20),(20,65));m.add_line((-60,-60),(60,65))
  segs=[{'a':(-300,0),'b':(-100,0),'system':'physical','handle':'L'}]
  if both_tails:segs.append({'a':(100,0),'b':(300,0),'system':'physical','handle':'R'})
  return recover_inline_source_spans(segs,[],list(m))
 def test_complete_inline_circle_glyph_and_opposed_pipes_positive(self):self.assertEqual(len(self.circle_span()[0]),1)
 def test_circle_alone_does_not_heal_pipe_gap(self):self.assertEqual(self.circle_span(with_ink=False)[0],[])
 def test_one_pipe_end_does_not_create_a_connection(self):self.assertEqual(self.circle_span(both_tails=False)[0],[])
if __name__=='__main__':unittest.main(verbosity=2)
