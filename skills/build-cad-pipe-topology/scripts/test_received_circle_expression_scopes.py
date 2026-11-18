import copy,tempfile,unittest
from pathlib import Path
import test_received_projected_circle_authority as fixtures
from rebuild_received_circle_expression_scopes import apply_received
from received_projected_circle_authority import OLD_HOLD


class ReceivedScopeTests(unittest.TestCase):
    def fixture(self,root):
        helper=fixtures.ReceivedAuthorityTests();f=helper.fixture(root);doc,g,d,r,b,s,gs=f;a=helper.select(root,f)
        route=dict(nodes=['T','L','R']);plan=dict(route=route,junction_failures={'T':OLD_HOLD},junctions={},path_failures=[])
        iso=dict(route=dict(nodes=['I1','I2','I3','I4']),junction_failures={},junctions={'T306':{'status':'normalization_replayed'}},path_failures=[])
        previous=dict(records=[dict(scope_id='S',system='return',views=dict(plan=plan,iso=iso),answer=dict(decision='同一范围，有省略或多画，见说明',comment='按原图省略表达'),normalized_axis_junctions=['T306'])],
            graph_mutated=False,DN_values_assigned=0,length_values_assigned=0,per_axis_edge_correspondence_assigned=False)
        return doc,g,s,gs,{'T':a},previous

    def test_received_connection_and_original_axis_normalization_compose_without_internal_pairing(self):
        with tempfile.TemporaryDirectory()as folder:
            doc,g,s,gs,a,previous=self.fixture(Path(folder));before=copy.deepcopy(previous)
            result=apply_received(previous,doc,g,s,gs,a)
            self.assertEqual(result['accepted_scope_count'],1);self.assertEqual(result['held_scope_count'],0)
            self.assertEqual(previous,before);self.assertEqual(result['records'][0]['views']['iso'],previous['records'][0]['views']['iso'])
            row=result['records'][0];self.assertFalse(row['internal_node_identities_assigned']);self.assertFalse(row['per_axis_edge_metric_allocation_known'])
            self.assertFalse(row['internal_branch_counts_equal']);self.assertEqual(row['normalized_axis_junctions'],['T306'])

    def test_unrelated_native_error_and_missing_source_path_cannot_be_cleared(self):
        for kind in('junction','path','unexpected-original-error','unused-authority'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory()as folder:
                doc,g,s,gs,a,previous=self.fixture(Path(folder));v=previous['records'][0]['views']['plan']
                if kind=='junction':v['junction_failures']['OTHER']='unproved native junction'
                if kind=='path':v['path_failures']=[dict(edge_id='BR',status='not_source_covered')]
                if kind=='unexpected-original-error':v['junction_failures']['T']='wrong source identity'
                if kind=='unused-authority':v['route']['nodes']=[]
                if kind in('junction','path'):
                    result=apply_received(previous,doc,g,s,gs,a);self.assertEqual(result['held_scope_count'],1)
                    self.assertTrue(result['records'][0]['failures'])
                else:
                    with self.assertRaises(ValueError):apply_received(previous,doc,g,s,gs,a)


if __name__=='__main__':unittest.main()
