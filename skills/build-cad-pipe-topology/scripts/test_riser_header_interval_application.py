import copy,unittest
import ezdxf
from riser_header_interval_application import clear_cycle_records,member_dn_guard
from native_paired_caption_geometry import collect
from native_line_path_evidence import LAYERS

class Tests(unittest.TestCase):
    def clearing(self):
        row=dict(axis_edge_id='A',mapping_id='M',plan_edge_id='P',complete_horizontal_centerline_mm=100,system='supply',axis_nodes=['X','Y'],axis_attribute_paths=[[[0,0],[100,0]]])
        held=dict(row,prior_complete_centerline_mm=100,barriers=[dict(source_LINE='VERT',declarations=[dict(handle='TEXT')])]);origin=dict(corridors=[],excluded_other_arm_origins=[dict(source_LINE='VERT',declaration=dict(handle='TEXT'),native_atom_origins=[dict(source_LINE='HORZ')])]);plan=dict(edges=[dict(edge_id='P',system='supply',source_handles=['VERT'],attribute_paths=[[[0,0],[0,100]]])]);return row,held,origin,plan
    def test_only_actual_excluded_origins_clear_old_metric(self):
        row,held,origin,plan=self.clearing();before=copy.deepcopy((row,held,origin,plan));rows,pending=clear_cycle_records([row],[held],origin,plan);self.assertEqual(len(rows),1);self.assertEqual(pending,[]);self.assertEqual((row,held,origin,plan),before)
        origin['excluded_other_arm_origins']=[]
        with self.assertRaisesRegex(ValueError,'not independently excluded'):clear_cycle_records([row],[held],origin,plan)
    def test_real_remaining_compound_carrier_is_not_cleared(self):
        row,held,origin,plan=self.clearing();origin['corridors']=[dict(source_LINE='VERT',system='supply',native_endpoints=[[0,0],[0,100]])];rows,pending=clear_cycle_records([row],[held],origin,plan);self.assertEqual(rows,[]);self.assertEqual(len(pending),1)
    def test_incomplete_or_changed_old_metric_is_rejected(self):
        row,held,origin,plan=self.clearing()
        with self.assertRaises(ValueError):clear_cycle_records([], [held],origin,plan)
        row['complete_horizontal_centerline_mm']=101
        with self.assertRaises(ValueError):clear_cycle_records([row],[held],origin,plan)
    def dn_fixture(self):
        doc=ezdxf.new();m=doc.modelspace();line=m.add_line((0,0),(100,0),dxfattribs={'layer':LAYERS['supply']});text=m.add_text('DN300(3.2)/DN200(2.6)',dxfattribs=dict(height=2,insert=(20,2),layer='NOTE'));direct=m.add_text('DN300(3.2)',dxfattribs=dict(height=2,insert=(60,2),layer='NOTE'))
        edge=dict(source_handles=[line.dxf.handle],member=dict(nominal_mm=300,plan_declarations=[dict(text_handle=text.dxf.handle)]));origin=dict(reserved_leader_texts={},corridors=[dict(declarations=[dict(handle=text.dxf.handle,raw_text=text.plain_text())])]);return doc,edge,origin,text,direct
    def test_compound_owned_projection_keeps_direct_DN_and_source_immutable(self):
        d,e,o,t,direct=self.dn_fixture();before=list(d.modelspace());r=member_dn_guard(d,e,collect(d),o);self.assertEqual(r['owned_compound_captions'][0]['handle'],t.dxf.handle);self.assertTrue(r['other_native_DN_checks']);self.assertEqual(list(d.modelspace()),before)
        direct.dxf.text='DN80(3.2)'
        with self.assertRaisesRegex(ValueError,'changes'):member_dn_guard(d,e,collect(d),o)
    def test_F_precedence_and_changed_declaration_stop_DN_application(self):
        d,e,o,t,direct=self.dn_fixture();o['reserved_leader_texts']={t.dxf.handle:{}}
        with self.assertRaisesRegex(ValueError,'F/leader'):member_dn_guard(d,e,collect(d),o)
        o['reserved_leader_texts']={};t.dxf.text='DN400(3.2)/DN200(2.6)'
        with self.assertRaisesRegex(ValueError,'changed'):member_dn_guard(d,e,collect(d),o)
if __name__=='__main__':unittest.main()
