import copy
import unittest
from unittest.mock import patch

import normalized_reviewed_expression_scope as owner


def result(plan_failure=True, path_failure=False):
    answer = dict(decision='同一范围，有省略或多画，见说明', comment='省略具体设备CAD')
    plan = dict(route=dict(nodes=['P', 'Q'], edges=['p']), junctions={},
                junction_failures={'P': 'unproved projected circle'} if plan_failure else {}, path_failures=[])
    iso = dict(route=dict(nodes=['A', 'T', 'B'], edges=['a', 'b']), junctions={},
               junction_failures={'T': 'selected ray insert mismatch'},
               path_failures=[dict(edge_id='a', status='unwitnessed')] if path_failure else [])
    return dict(records=[dict(scope_id='S', answer=answer, views=dict(plan=plan, iso=iso))],
                graph_mutated=False, DN_values_assigned=0, length_values_assigned=0,
                per_axis_edge_correspondence_assigned=False, human_accepted=False)


class NormalizedExpressionTests(unittest.TestCase):
    def run_owner(self, baseline, fail_node=None):
        specs = {k: dict(path=k, sha256=k) for k in ('iso_source', 'iso_graph', 'iso_normalization_audit')}
        def collect(doc, graph, node, *args):
            if node == fail_node:
                raise ValueError('new native source conflict')
            return dict(status='normalization_replayed_native_ray_evidence_unreviewed' if node=='T' else 'native_ray_evidence_unreviewed')
        with patch.object(owner.original, 'compute', return_value=copy.deepcopy(baseline)), \
                patch.object(owner, 'read_source', return_value=(object(), {})), \
                patch.object(owner, 'load', return_value={}), \
                patch.object(owner, 'sha', side_effect=lambda p:p), \
                patch.object(owner.normalized, 'prepare', return_value=object()), \
                patch.object(owner.normalized, 'collect', side_effect=collect) as reader:
            output = owner.compute(dict(inputs=specs))
        self.assertEqual([call.args[2] for call in reader.call_args_list], ['A', 'T', 'B'])
        self.assertEqual(output['DN_values_assigned'], 0); self.assertEqual(output['length_values_assigned'], 0)
        self.assertFalse(output['graph_mutated']); self.assertFalse(output['human_accepted'])
        return output['records'][0]

    def test_normalized_axis_does_not_confirm_pending_plan_circle(self):
        before = result(); previous = copy.deepcopy(before)
        record = self.run_owner(before)
        self.assertEqual(before, previous)
        self.assertEqual(record['status'], 'held_local_source_evidence')
        self.assertEqual(record['views']['iso']['junction_failures'], {})
        self.assertEqual(record['normalized_axis_junctions'], ['T'])
        self.assertEqual(record['failures'][0]['view'], 'plan')
        self.assertFalse(record['internal_node_identities_assigned'])
        self.assertFalse(record['per_axis_edge_metric_allocation_known'])

    def test_path_gap_remains_held_and_new_source_conflicts_are_rechecked(self):
        record = self.run_owner(result(plan_failure=False, path_failure=True))
        self.assertEqual(record['status'], 'held_local_source_evidence')
        self.assertEqual(record['failures'][0]['owner'], 'local_source_path')
        record = self.run_owner(result(plan_failure=False), fail_node='A')
        self.assertEqual(record['views']['iso']['junction_failures'], {'A': 'new native source conflict'})

    def test_complete_range_still_has_no_interior_identity_or_per_edge_values(self):
        record = self.run_owner(result(plan_failure=False))
        self.assertEqual(record['status'], 'native_bounded_range_correspondence')
        self.assertFalse(record['per_axis_edge_metric_allocation_known'])
        self.assertFalse(record['internal_node_identities_assigned'])


if __name__ == '__main__':
    unittest.main()
