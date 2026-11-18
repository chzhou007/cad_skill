import copy,unittest
import ezdxf
from alias_member_circle_interfaces import source_domains,provider_index,detail_bracket
from axis_attribute_source_routing import collect as routing
from batch_native_path_coverage import collect as coverage

class Tests(unittest.TestCase):
    def test_mixed_local_rise_never_takes_vertical_attributes_from_plan(self):
        g=dict(edges=[dict(edge_id='E',system='supply',floor_start=2,floor_end=2,attribute_paths=[[[0,0],[10,0],[10,20]]])]);p=dict(isometric_horizontal_directions_degrees=[0,45,135],source_rule_evidence='all vertical segments use11')
        directions=routing(g,p);r=dict(axis_edge_id='E',kind='lower_member_approach_with_local_rise',nominal_mm=200,plan_projection=dict(value_mm=800),complete_horizontal_centerline_route_mm=None)
        doc=ezdxf.new()
        for a,b in [((0,0),(10,0)),((10,0),(10,20))]:doc.modelspace().add_line(a,b,dxfattribs=dict(layer='空调冷冻水供水'))
        r['native_axis_coverage']=coverage(doc,g,['E'],'s','g')
        out=source_domains(r,directions);self.assertEqual(out['horizontal_complete_centerline_mm'],800);self.assertIsNone(out['whole_edge_nominal_mm']);self.assertIsNone(out['whole_edge_complete_centerline_mm']);self.assertEqual(out['vertical_DN_and_length_source'],'axis_11_native_vertical');self.assertEqual(out['vertical_lengths_assigned'],0);self.assertTrue(all(x['source_line_coverage_checked']for x in out['records']))
        r['kind']='primary_member_main'
        with self.assertRaisesRegex(ValueError,'pure horizontal'):source_domains(r,directions)
    def test_provider_namespaces_do_not_silently_duplicate_intervals(self):
        row=dict(floor=2,system='supply',plan_edge_id='P')
        with self.assertRaisesRegex(ValueError,'overlap'):provider_index(dict(member_plan_runs=dict(records=[row]),ordered_owner_plan_runs=dict(records=[row])))
        self.assertEqual(len(provider_index(dict(member_plan_runs=dict(records=[row])))),1)
    def fixture(self):
        doc=ezdxf.new();m=doc.modelspace();line=m.add_line((0,0),(100,0),dxfattribs=dict(layer='空调冷冻水供水'));circle=m.add_circle((30,0),4,dxfattribs=dict(layer='空调冷冻水供水'))
        graph=dict(nodes=[dict(node_id='T',x=100,y=0),dict(node_id='U',x=0,y=0,subtype='unresolved_source_terminal')],edges=[dict(edge_id='P',system='supply',start_node_id='T',end_node_id='U',attribute_paths=[[[0,0],[100,0]]],source_handles=[line.dxf.handle])]);return doc,graph,circle
    def test_detail_circle_requires_native_visible_paths_and_retains_extent_end(self):
        doc,g,c=self.fixture();before=copy.deepcopy(g);r=detail_bracket(doc,g,dict(plan_T='T'),'supply','s','g');self.assertEqual(r['source_circle']['handle'],c.dxf.handle);self.assertEqual(r['retained_drawing_extent_end'],'U');self.assertTrue(r['extra_tail_not_promoted_to_physical_pipe']);self.assertEqual(g,before)
    def test_missing_competing_or_opposite_service_circle_does_not_become_a_tee(self):
        for case in('missing','competing','opposite','represented'):
            doc,g,c=self.fixture()
            if case=='missing':doc.modelspace().delete_entity(c)
            elif case=='competing':doc.modelspace().add_circle((40,0),4,dxfattribs=dict(layer='空调冷冻水供水'))
            elif case=='opposite':c.dxf.layer='空调冷冻水回水'
            else:g['nodes'].append(dict(node_id='existing',x=30,y=0))
            with self.assertRaises(ValueError):detail_bracket(doc,g,dict(plan_T='T'),'supply','s','g')
if __name__=='__main__':unittest.main()
