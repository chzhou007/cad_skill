import unittest,copy,math
import ezdxf
from ezdxf import bbox
from ezdxf.math import Matrix44
from native_proxy_evidence import block_fingerprint
from native_instrument_heads import recognize
from instrumentation import source_gauges

def fixture(rotation=0,mirror=1):
 d=ezdxf.new();b=d.blocks.new('Body');b.add_lwpolyline([(-10,-10),(10,-10),(10,10),(-10,10)],close=True);b.add_text('P',dxfattribs={'height':5,'insert':(-2,-2)})
 e=d.modelspace().add_blockref('Body',(100,200),dxfattribs={'rotation':rotation,'xscale':mirror,'layer':'Instrument'});matrix=e.matrix44()
 def pt(p):v=matrix.transform(p);return [v.x,v.y]
 def line(a,b):return d.modelspace().add_line(pt(a),pt(b),dxfattribs={'layer':'Instrument'})
 hl=line((-10,2),(-22,2));tl=line((10,0),(30,0))
 circle=d.modelspace().add_circle(pt((-30,2)),8,dxfattribs={'layer':'Instrument'})
 tag=d.modelspace().add_text('PIT-1',dxfattribs={'height':2,'layer':'Instrument','insert':(-33,1)});tag.transform(matrix)
 dia=line((-30,-6),(-30,10))
 box=bbox.extents([e]);sym={'handle':e.dxf.handle,'block':'Body','entity':e,'bounds':[box.extmin.x,box.extmin.y,box.extmax.x,box.extmax.y]}
 path=[pt((30,-40)),pt((30,40))];edges=[{'edge_id':'E1','system':'supply','source_handles':['MAIN'],'path_points':path,'attribute_paths':[path]}]
 rule={'block':'Body','fingerprint':block_fingerprint(b),'body_caption':'P','head_kinds':['PIT'],'leader_layers':['Instrument'],'contact_tolerance':.001,'maximum_leader_body_diagonals':3,'label':'Pressure Transmitter','type_code':'PIT'}
 return d,sym,edges,rule,hl,tl,circle

class NativeInstrumentHeads(unittest.TestCase):
 def test_complete_offset_face_leaders_and_exact_tap(self):
  d,s,e,r,hl,tl,c=fixture();out=recognize(s,e,d,source_gauges(d),[r]);self.assertEqual(out['status'],'complete_tagged_head');self.assertEqual(out['edge_ids'],['E1']);self.assertFalse(out['hydraulic_connection']);self.assertIn(hl.dxf.handle,out['source_handles']);self.assertIn(tl.dxf.handle,out['source_handles'])
 def test_rotation_and_mirroring_preserve_full_assembly(self):
  for rotation,mirror in [(90,1),(180,-1),(270,1),(35,-1)]:
   with self.subTest(rotation=rotation,mirror=mirror):
    d,s,e,r,*_=fixture(rotation,mirror);out=recognize(s,e,d,source_gauges(d),[r]);self.assertEqual(out['status'],'complete_tagged_head')
 def test_near_head_without_native_leader_is_rejected(self):
  d,s,e,r,hl,*_=fixture();d.modelspace().delete_entity(hl);out=recognize(s,e,d,source_gauges(d),[r]);self.assertEqual(out['edge_ids'],[])
 def test_head_leader_must_touch_native_body(self):
  d,s,e,r,hl,*_=fixture();hl.dxf.start=(89,202,0);out=recognize(s,e,d,source_gauges(d),[r]);self.assertEqual(out['edge_ids'],[])
 def test_label_kind_controls_pressure_class(self):
  d,s,e,r,*_=fixture();r['head_kinds']=['DPS'];out=recognize(s,e,d,source_gauges(d),[r]);self.assertEqual(out['edge_ids'],[])
 def test_tap_endpoint_distance_not_bbox_or_nearest(self):
  d,s,e,r,hl,tl,_=fixture();tl.dxf.end=(129.9,200,0);out=recognize(s,e,d,source_gauges(d),[r]);self.assertEqual(out['edge_ids'],[])
 def test_instrument_leader_does_not_become_hydraulic_edge(self):
  d,s,e,r,*_=fixture();before=copy.deepcopy(e);recognize(s,e,d,source_gauges(d),[r]);self.assertEqual(e,before)
 def test_conflicting_service_at_tap_stays_pending(self):
  d,s,e,r,*_=fixture();other=copy.deepcopy(e[0]);other.update(edge_id='E2',system='return');out=recognize(s,e+[other],d,source_gauges(d),[r]);self.assertEqual(out['status'],'pending_tap_service_conflict');self.assertEqual(out['edge_ids'],[])
 def test_contradictory_caption_preserves_proven_tap_and_original_tag(self):
  d,s,e,r,*_=fixture();d.modelspace().add_text('CHWS-1',dxfattribs={'insert':(67,197),'height':1,'layer':'Instrument'});r['source_service_tags']={'CHWS':'supply'};e[0]['system']='return'
  out=recognize(s,e,d,source_gauges(d),[r]);self.assertEqual(out['status'],'complete_tagged_head');self.assertEqual(out['edge_ids'],['E1']);self.assertTrue(out['source_service_tag_conflict']);self.assertIn('CHWS-1',out['source_service_tags']);self.assertEqual(e[0]['system'],'return')
 def test_competing_typed_heads_stay_pending(self):
  d,s,e,r,_,_,circle=fixture();gauges=source_gauges(d);other=d.modelspace().add_circle((68,202),10,dxfattribs={'layer':'Instrument'});q=dict(gauges[0],entity=other,center=(68,202),radius=10);out=recognize(s,e,d,gauges+[q],[r]);self.assertEqual(out['status'],'pending_ambiguous_heads')
 def test_changed_prototype_cannot_reuse_calibration(self):
  d,s,e,r,*_=fixture();r['fingerprint']='changed'
  with self.assertRaises(ValueError):recognize(s,e,d,source_gauges(d),[r])

if __name__=='__main__':unittest.main()
