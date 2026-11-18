import copy,unittest
import ezdxf
from native_plan_crossover_centerline import measure
from native_line_path_evidence import LAYERS

class DraftingCrossingProjectionTests(unittest.TestCase):
    def fixture(self):
        d=ezdxf.new('R2013');m=d.modelspace();a=m.add_line((0,0),(4,0),dxfattribs={'layer':LAYERS['return']});b=m.add_line((6,0),(10,0),dxfattribs={'layer':LAYERS['return']});c=m.add_line((5,-2),(5,2),dxfattribs={'layer':LAYERS['supply']});h='a'*64
        gap=dict(source_gap_id='G',source_sha256=h,source_handles=[a.dxf.handle,b.dxf.handle],a=[4.,0.],b=[6.,0.],crossings=[dict(crossing=[5.,0.],crossed_handle=c.dxf.handle,crossed_source_system='supply')],crossing_connectivity='independent_pipes_no_junction',physical_length='unknown',relative_elevation='unknown')
        e=dict(edge_id='E',system='return',start_node_id='T1',end_node_id='T2',floor_start=1,floor_end=1,source_handles=[a.dxf.handle,b.dxf.handle],attribute_paths=[[[0.,0.],[4.,0.]],[[6.,0.],[10.,0.]]],path_length=8.,path_length_complete=False,source_normalized_crossovers=[gap])
        nodes=[dict(node_id=n,node_type='tee',floor=1,system='return',x=x,y=0.)for n,x in [('T1',0.),('T2',10.)]]
        g=dict(metadata=dict(source_sha256=h),nodes=nodes,edges=[e]);u=dict(status='native_mm_units_corroborated_not_pipe_dimension_assignment',plan_window=[-20,20,-20,20]);return d,g,u,h
    def test_replayed_drafting_break_completes_XY_but_keeps_every_physical_unknown(self):
        d,g,u,h=self.fixture();before=copy.deepcopy(g);r=measure(d,g,'E',u,h,'b'*64)
        self.assertEqual(r['pipe_projection_mm'],8);self.assertEqual(r['complete_horizontal_centerline_projection_mm'],10);self.assertEqual(g,before)
        self.assertIsNone(r['installed_length_mm']);self.assertIsNone(r['net_pipe_cut_length_mm']);self.assertEqual(r['physical_gap_lengths_assigned'],0)
        self.assertEqual(r['crossover_projections'][0]['original_gap']['physical_length'],'unknown');self.assertIsNone(r['crossover_projections'][0]['physical_gap_length_mm'])
    def test_touching_bookkeeping_subdivision_is_coalesced_without_becoming_another_gap(self):
        d,g,u,h=self.fixture();g['edges'][0]['attribute_paths']=[[[0.,0.],[2.,0.]],[[2.,0.],[4.,0.]],[[6.,0.],[10.,0.]]];r=measure(d,g,'E',u,h,'b'*64)
        self.assertEqual(r['complete_horizontal_centerline_projection_mm'],10);self.assertEqual([(p['path_index'],p['segment_index'])for p in r['pipe_pieces']],[(0,0),(1,0),(2,0)])
    def test_wave_inline_and_detail_are_not_drafting_crossovers(self):
        for field in('source_flexible_joints','source_view_context','source_wave_omission','source_omission'):
            d,g,u,h=self.fixture();g['edges'][0][field]={'source':'original'}
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'original length owner'):measure(d,g,'E',u,h,'b'*64)
    def test_unproved_circle_connector_and_missing_original_pipe_hold(self):
        d,g,u,h=self.fixture();g['nodes'][0]['x']=-.1
        with self.assertRaisesRegex(ValueError,'distinct T endpoints'):measure(d,g,'E',u,h,'b'*64)
        d,g,u,h=self.fixture();d.entitydb[g['edges'][0]['source_handles'][0]].dxf.layer=LAYERS['supply']
        with self.assertRaises(ValueError):measure(d,g,'E',u,h,'b'*64)
    def test_same_system_crossing_or_noncollinear_tails_hold(self):
        d,g,u,h=self.fixture();g['edges'][0]['source_normalized_crossovers'][0]['crossings'][0]['crossed_source_system']='return'
        with self.assertRaisesRegex(ValueError,'independent supply/return'):measure(d,g,'E',u,h,'b'*64)
        d,g,u,h=self.fixture();d.entitydb[g['edges'][0]['source_handles'][0]].dxf.start=(0,1,0)
        with self.assertRaises(ValueError):measure(d,g,'E',u,h,'b'*64)
    def test_ordinary_unmarked_gap_units_and_window_are_not_enough(self):
        d,g,u,h=self.fixture();g['edges'][0]['source_normalized_crossovers']=[]
        with self.assertRaisesRegex(ValueError,'source-normalized'):measure(d,g,'E',u,h,'b'*64)
        d,g,u,h=self.fixture();u['status']='assumed_mm'
        with self.assertRaisesRegex(ValueError,'corroborated'):measure(d,g,'E',u,h,'b'*64)

if __name__=='__main__':unittest.main()
