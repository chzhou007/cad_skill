import unittest,ezdxf
from source_fidelity import pump_display_family,assembly_fidelity
from instrumentation import gauge_connector_handles
import pipe_geometry as pg

class SourceFidelity(unittest.TestCase):
 def setUp(self):pg.set_tolerance(.01)
 def tearDown(self):pg.set_tolerance(.5)
 def pump(self,lead=True,partial=False):
  d=ezdxf.new();m=d.modelspace();c=m.add_circle((0,0),10);s=m.add_lwpolyline([(15,-4),(30,-4),(30,4),(15,4)],close=not partial)
  if lead:m.add_line((10,0),(15,0))
  return d,{'node_id':'P1','source_handle':c.dxf.handle,'source_handles':[c.dxf.handle]}
 def test_complete_attached_rectangle(self):
  d,n=self.pump();r=pump_display_family(d,n);self.assertEqual(r['status'],'complete_native_display_family');self.assertEqual(len(r['source_handles']),3)
 def test_nearby_rectangle_is_not_enough(self):
  d,n=self.pump(False);self.assertEqual(pump_display_family(d,n)['status'],'body_only_no_proven_attached_family')
 def test_open_contour_not_whole_family(self):
  d,n=self.pump(partial=True);self.assertEqual(pump_display_family(d,n)['status'],'body_only_no_proven_attached_family')
 def test_competing_display_families_stay_pending(self):
  d,n=self.pump();d.modelspace().add_lwpolyline([(-15,-4),(-30,-4),(-30,4),(-15,4)],close=True);d.modelspace().add_line((-10,0),(-15,0));self.assertEqual(pump_display_family(d,n)['status'],'pending_ambiguous_display_family')
 def test_cross_layer_connector_with_both_facing_contacts(self):
  d=ezdxf.new();e=d.modelspace().add_line((10,0),(25,0),dxfattribs={'layer':'ANNOTATION'});self.assertEqual(gauge_connector_handles(d,dict(center=(0,0),radius=10),dict(center=(30,0),radius=5)),[e.dxf.handle])
 def test_close_but_disconnected_connector_rejected(self):
  d=ezdxf.new();d.modelspace().add_line((11,0),(24,0));self.assertEqual(gauge_connector_handles(d,dict(center=(0,0),radius=10),dict(center=(30,0),radius=5)),[])
 def test_nonfacing_circle_contacts_rejected(self):
  d=ezdxf.new();d.modelspace().add_line((0,10),(30,5));self.assertEqual(gauge_connector_handles(d,dict(center=(0,0),radius=10),dict(center=(30,0),radius=5)),[])
 def test_gate_catches_missing_exploded_member_strokes(self):
  d=ezdxf.new();group=dict(id='PANEL',source_kind='source_measurement_panel',source_handles=['A'],component_handles=['A']);r=assembly_fidelity(d,[group],[dict(handle='A',source_handles=['A','B','C','D'])]);self.assertEqual(r[0]['missing_source_handles'],['B','C','D']);self.assertEqual(r[0]['status'],'FAIL')
if __name__=='__main__':unittest.main(verbosity=2)
