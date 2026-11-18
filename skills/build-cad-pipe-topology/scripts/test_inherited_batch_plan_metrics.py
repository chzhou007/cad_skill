import copy,unittest
from test_native_inline_joint_path_coverage import fixture
from inherited_batch_plan_metrics import extend


class Tests(unittest.TestCase):
    def test_source_inline_pipe_length_reused_without_marker_length_or_graph_change(self):
        doc,g,instances,policy,hashes=fixture();eid=policy['edges'][0];before=copy.deepcopy(g)
        mapping=dict(mapping_id='M',plan_edges=[eid],iso_edges=['AX'],system='supply')
        previous=[dict(mapping_id='M',plan_edges=[eid],iso_edges=['AX'],projection=None,reason='separate paths')]
        origin=dict(block_name=policy['block_name'],block_fingerprint_sha256=policy['block_fingerprint_sha256'],confirmation_basis='source_geometry_calibrated',expert_evidence='native source control')
        r=extend(doc,g,instances,[mapping],previous,dict(plan_window=[-1000,1000,-1000,1000]),hashes,origin)
        self.assertEqual(r['additional_metric_scopes'],1);self.assertEqual(r['records'][0]['projection']['value_mm'],40)
        self.assertIsNone(r['records'][0]['projection']['inline_joint_interior_length_mm']);self.assertEqual(g,before)
    def test_nonmetric_detail_is_not_measured_by_global_units_or_inline_symbols(self):
        doc,g,instances,policy,hashes=fixture();eid=policy['edges'][0];g['edges'][0]['source_view_context']=dict(kind='detail')
        mapping=dict(mapping_id='M',plan_edges=[eid],iso_edges=['AX'],system='supply')
        previous=[dict(mapping_id='M',plan_edges=[eid],iso_edges=['AX'],projection=None,reason='detail')]
        origin=dict(block_name=policy['block_name'],block_fingerprint_sha256=policy['block_fingerprint_sha256'],confirmation_basis='source_geometry_calibrated',expert_evidence='source')
        r=extend(doc,g,instances,[mapping],previous,dict(plan_window=[-1000,1000,-1000,1000]),hashes,origin)
        self.assertIsNone(r['records'][0]['projection']);self.assertEqual(r['additional_metric_scopes'],0)


if __name__=='__main__':unittest.main()
