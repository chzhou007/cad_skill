import copy
import unittest
import ezdxf
from ezdxf.math import Matrix44
from source_wave_terminals import normalized_form, reconcile


def fixture(terminal=(0,0),pipe_layer='PIPE',rotation=0,mirror=False):
    doc=ezdxf.new();m=doc.modelspace()
    curve=m.add_open_spline([(-2,0,0),(-1.5,1,0),(-.7,1,0),(.7,-1,0),(1.5,-1,0),(2,0,0)],degree=3,dxfattribs={'layer':'PIPE'})
    prototype={'id':'WAVE',**normalized_form(curve)}
    line=m.add_line(terminal,(terminal[0],terminal[1]-5),dxfattribs={'layer':pipe_layer})
    if rotation or mirror:
        import math
        matrix=Matrix44.scale(-1 if mirror else 1,1,1)@Matrix44.z_rotate(math.radians(rotation))@Matrix44.translate(100,200,0)
        curve.transform(matrix);line.transform(matrix)
    p=list(line.dxf.start)[:2];q=list(line.dxf.end)[:2]
    graph={'nodes':[dict(node_id='U',node_type='virtual_equipment',x=p[0],y=p[1],floor='Roof',system='water',
                         source_handles=[line.dxf.handle],ports=[dict(port_id='U-P1',x=p[0],y=p[1],system='water')]),
                     dict(node_id='T',node_type='tee',x=q[0],y=q[1],floor='Roof',system='water')],
           'edges':[dict(edge_id='E',start_node_id='U',end_node_id='T',system='water',path_points=[p,q],attribute_paths=[[p,q]],source_handles=[line.dxf.handle])]}
    profile={'readability_verified':True,'calibration_evidence':['complete native repeated S-curve with one perpendicular pipe terminal'],
             'maximum_terminal_gap_chord_ratio':.025,'contact_tolerance':.001,'source_layers':['PIPE'],
             'shape_prototypes':[prototype],'maximum_shape_error':1e-5,'maximum_tail_chord_alignment':.35,'minimum_contact_end_fraction':.2}
    return doc,graph,profile,curve,line


class SourceWaveTerminals(unittest.TestCase):
    def test_native_transverse_end_mark_changes_role_without_hydraulic_merge(self):
        doc,g,p,_,_=fixture();out,audit=reconcile(doc,g,p)
        self.assertEqual(audit['represented_glyphs'],1)
        self.assertEqual(out['edges'],g['edges'])
        self.assertEqual(out['nodes'][0]['ports'],g['nodes'][0]['ports'])
        self.assertEqual(out['nodes'][0]['boundary_type'],'source_native_wave_terminal')
        self.assertFalse(out['sourceTerminalGlyphs'][0]['remote_continuation_confirmed'])

    def test_bounded_native_drafting_clearance_does_not_move_the_pipe(self):
        doc,g,p,_,_=fixture(terminal=(0,-.06));out,audit=reconcile(doc,g,p)
        self.assertEqual(audit['represented_glyphs'],1)
        self.assertEqual(out['edges'],g['edges'])
        self.assertAlmostEqual(out['sourceTerminalGlyphs'][0]['terminal_to_glyph_distance'],.06,places=4)

    def test_remote_parallel_endpoint_is_not_nearest_matched(self):
        doc,g,p,_,_=fixture(terminal=(0,-.3));out,audit=reconcile(doc,g,p)
        self.assertEqual(audit['represented_glyphs'],0)
        self.assertNotIn('sourceTerminalGlyphs',out)

    def test_rotated_mirrored_source_geometry_matches_complete_form(self):
        doc,g,p,_,_=fixture(rotation=37,mirror=True)
        self.assertEqual(reconcile(doc,g,p)[1]['represented_glyphs'],1)

    def test_other_source_layer_at_same_point_is_not_bound(self):
        doc,g,p,_,_=fixture(pipe_layer='OTHER')
        self.assertEqual(reconcile(doc,g,p)[1]['represented_glyphs'],0)

    def test_real_curved_pipe_with_owning_endpoint_tail_is_rejected(self):
        doc,g,p,curve,_=fixture();tail=doc.modelspace().add_line((-2,0),(-3,0),dxfattribs={'layer':'PIPE'})
        g['edges'].append(dict(edge_id='REAL',start_node_id='A',end_node_id='B',system='water',path_points=[[-2,0],[-3,0]],attribute_paths=[[[-2,0],[-3,0]]],source_handles=[tail.dxf.handle]))
        out,audit=reconcile(doc,g,p)
        self.assertEqual(audit['represented_glyphs'],0)
        self.assertEqual(audit['candidates'][0]['status'],'rejected_curve_endpoint_pipe_contacts')

    def test_unrecognized_curve_form_stays_explicitly_pending(self):
        doc,g,p,curve,_=fixture();points=list(curve.control_points);points[2]=(-.7,2,0);curve.control_points=points
        out,audit=reconcile(doc,g,p)
        self.assertEqual(audit['represented_glyphs'],0)
        self.assertEqual(audit['candidates'][0]['status'],'pending_unrecognized_source_spline_form')

    def test_known_destination_original_chinese_is_preserved(self):
        doc,g,p,_,_=fixture();g['nodes'][0]['interface_destination']={'text':'接至专用排水管','remote_port_confirmed':False}
        out,audit=reconcile(doc,g,p)
        self.assertEqual(out['nodes'][0]['interface_destination'],g['nodes'][0]['interface_destination'])
        self.assertEqual(audit['known_destinations_preserved'],1)

    def test_competing_native_pipe_ends_at_one_marker_are_not_joined(self):
        doc,g,p,_,_=fixture();line=doc.modelspace().add_line((0,0),(0,5),dxfattribs={'layer':'PIPE'})
        g['nodes'].append(dict(node_id='U2',node_type='virtual_equipment',x=0,y=0,floor='Roof',system='water',source_handles=[line.dxf.handle],ports=[]))
        g['edges'].append(dict(edge_id='E2',start_node_id='U2',end_node_id='T2',system='water',path_points=[[0,0],[0,5]],attribute_paths=[[[0,0],[0,5]]],source_handles=[line.dxf.handle]))
        self.assertEqual(reconcile(doc,g,p)[1]['represented_glyphs'],0)

    def test_synthetic_semantic_endpoint_is_not_a_native_terminal_witness(self):
        doc,g,p,_,line=fixture();line.dxf.start=(0,-1,0)
        self.assertEqual(reconcile(doc,g,p)[1]['represented_glyphs'],0)

    def test_missing_readability_calibration_stops_recognition(self):
        doc,g,p,_,_=fixture();p['readability_verified']=False
        with self.assertRaisesRegex(ValueError,'readable source calibration'):
            reconcile(doc,g,p)


if __name__=='__main__':unittest.main()
