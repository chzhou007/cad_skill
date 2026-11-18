import copy,json,tempfile,unittest
from unittest.mock import patch
import test_axis_riser_attribute_viewer as fixtures
from build_visualization import verified_source_attribute_ancestor


class Tests(unittest.TestCase):
    def fixture(self,folder):
        gp,data,axis,common,ba,sha=fixtures.Tests().data(folder)
        parent=gp.parent/'axis-parent.json';parent.write_text(json.dumps(data));axis['output_graph_sha256']=sha(parent)
        data['sourceNamedRiserPlanAttributeFusion']={'new':True};gp.write_text(json.dumps(data))
        audit=dict(output_graph_sha256=sha(gp),parent_graph=dict(path=str(parent),sha256=sha(parent)),
            verified_axis_segment_parent=axis,prior_edges_and_vertical_attributes_preserved=True,physical_ports_verified=False,
            whole_edge_DN_assigned=0,installed_lengths_assigned=0,related_HIL_confirmation_inherited=False,
            records=['NAMED'],plan_DN_scope_fusion=['NAMED-DN'])
        return gp,data,audit,common,ba,sha,parent
    def test_fresh_named_replay_reuses_only_its_just_verified_parent_context(self):
        with tempfile.TemporaryDirectory() as folder:
            gp,data,audit,common,ba,sha,parent=self.fixture(folder)
            with patch('attach_named_riser_plan_attributes.verify_output',return_value=audit) as current,patch('attach_axis_riser_segment_attributes.verify_output',side_effect=AssertionError('duplicate parent replay')):
                ancestor,proof=verified_source_attribute_ancestor(gp,data)
            current.assert_called_once_with(gp.parent);self.assertEqual(ancestor,common)
            self.assertEqual(proof['records'],['OLD','NEW','NAMED']);self.assertEqual(proof['plan_DN_scope_fusion'],['OLD-DN','NEW-DN','NAMED-DN'])
            self.assertEqual(proof['axis_riser_attribute_parent_graph_path'],str(parent));self.assertFalse(proof['hil_ready'])
    def test_missing_stage_stale_parent_and_false_physical_extent_cannot_enter_viewer(self):
        with self.assertRaisesRegex(ValueError,'verified extension'):
            verified_source_attribute_ancestor(None,dict(edges=[dict(cross_view_attributes=dict(mapping_basis='native_named_riser_and_independent_equipment_service'))]))
        for case in ('graph','parent','context','preservation','port','length','replay'):
            with tempfile.TemporaryDirectory() as folder:
                gp,data,audit,common,ba,sha,parent=self.fixture(folder)
                if case=='graph':audit['output_graph_sha256']='other'
                elif case=='parent':parent.write_text('{}')
                elif case=='context':ba.write_text('{}')
                elif case=='preservation':audit['prior_edges_and_vertical_attributes_preserved']=False
                elif case=='port':audit['physical_ports_verified']=True
                elif case=='length':audit['installed_lengths_assigned']=1
                def verify(_):
                    if case=='replay':raise ValueError('native source changed')
                    return audit
                with self.subTest(case=case),patch('attach_named_riser_plan_attributes.verify_output',side_effect=verify),self.assertRaises(ValueError):
                    verified_source_attribute_ancestor(gp,data)


if __name__=='__main__':unittest.main()
