import copy,unittest
from test_native_junction_ray_evidence import fixture

class OmissionMarkerNativeTGapTests(unittest.TestCase):
 def test_omission_marker_reference_cannot_witness_a_small_unpainted_T_gap(self):
  # SH16 T306: this legacy field points at a DIM_SYMB LWPOLYLINE, not an INSERT.
  # A source branch stops 2.35484 drawing units short; keep missing coverage.
  from crossview_equipment_branch_inventory import native_tee
  from partial_native_line_coverage import intervals
  d,g,p=fixture();m=d.modelspace();branch=d.entitydb[p['junctions'][0]['edge_witnesses']['B']]
  m.delete_entity(branch);gap=2.354840376327047
  real=m.add_line((0,gap),(0,10),dxfattribs={'layer':'空调冷冻水供水'})
  marker=m.add_lwpolyline([(-1,20),(0,19),(1,20)],dxfattribs={'layer':'DIM_SYMB'})
  g['edges'][2]['source_insert_handle']=marker.dxf.handle
  g['nodes'].extend(dict(node_id=n,node_type='unresolved_endpoint',x=x,y=y)for n,x,y in [('L',-10,0),('R',10,0),('B',0,10)])
  before=copy.deepcopy(g)
  with self.assertRaisesRegex(ValueError,'selected ray insert mismatch'):native_tee(d,g,'T','S','G')
  pieces=intervals([0,0],[0,10],[(real.dxf.handle,[0,gap],[0,10])])
  self.assertEqual(pieces[0]['status'],'unwitnessed');self.assertAlmostEqual(pieces[0]['drawing_length'],gap)
  self.assertEqual(pieces[1]['source_handles'],[real.dxf.handle]);self.assertEqual(g,before)

if __name__=='__main__':unittest.main()
