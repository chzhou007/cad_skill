import copy
import unittest
import test_repair_confirmed_overlapping_branches as overlap_fixture
from repair_confirmed_overlapping_branches import apply
from reconcile_resolved_circle_crossovers import reconcile, digest


class ReconcileCrossoversTests(unittest.TestCase):
    def setUp(self):
        base = overlap_fixture.OverlappingBranchesTests(); base.setUp()
        self.doc, self.repair = base.doc, base.policy
        a, c = self.repair['connections']
        conflict = {'source_handles': [a['branch_handle'], c['branch_handle']],
                    'a': [300, 80], 'b': [300, -80], 'status': 'pending',
                    'reason': 'source_circle_at_crossing_requires_comparison',
                    'crossings': [{'crossed_handle': a['main_handle'], 'crossed_source_system': 'supply'}],
                    'circle_conflicts': [{'circle_handle': a['circle_handle']}]}
        base.graph['sourceCircleCrossoverConflicts'] = [conflict]
        self.graph, _ = apply(self.doc, base.graph, [], self.repair, 's', 'g', 'ev')
        self.policy = {'source_sha256': 's', 'graph_sha256': 'current', 'conflict_sha256s': [digest(conflict)]}

    def run_reconcile(self, graph=None, policy=None):
        return reconcile(self.doc, graph or self.graph, policy or self.policy, self.repair, 's', 'current', 'ev')

    def test_archive_preserves_topology_attributes_and_history(self):
        self.graph['sourceCircleCrossoverConflicts'].append({'status': 'pending', 'unrelated': True})
        out, audit = self.run_reconcile()
        self.assertEqual(out['sourceCircleCrossoverConflicts'], [{'status': 'pending', 'unrelated': True}])
        for key in ('nodes', 'edges', 'virtual_equipment_ports', 'userConfirmedOverlappingBranches'):
            self.assertEqual(out[key], self.graph[key])
        self.assertEqual(out['preHilComparison']['previous_comparison'], self.graph['preHilComparison'])
        self.assertEqual(audit['records'][0]['original_conflict'], self.graph['sourceCircleCrossoverConflicts'][0])
        self.assertFalse(out['metadata']['hil_ready'])

    def test_reject_stale_scope_and_missing_confirmation(self):
        for key, value in [('source_sha256', 'stale'), ('graph_sha256', 'stale'), ('conflict_sha256s', ['wrong'])]:
            p = dict(self.policy); p[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.run_reconcile(policy=p)
        self.repair['confirmed_by'] = 'algorithm'
        with self.assertRaises(ValueError): self.run_reconcile()

    def test_reject_fourway_wrong_ownership_and_system(self):
        for mode in ('fourway', 'wrong_target', 'wrong_system', 'unproven_length', 'forged_evidence', 'direct_gap'):
            g = copy.deepcopy(self.graph); branch = next(e for e in g['edges'] if e['edge_id'] == 'C')
            if mode == 'fourway':
                other = copy.deepcopy(branch); other['edge_id'] = 'EXTRA'; g['edges'].append(other)
            elif mode == 'wrong_target': branch['end_node_id'] = 'T-OVERLAP-'+self.repair['connections'][0]['circle_handle']
            elif mode == 'wrong_system': branch['system'] = 'return'
            elif mode == 'unproven_length': branch['physical_length'] = 0
            elif mode == 'forged_evidence': branch['user_confirmed_overlap_connection']['circle_handle'] = 'wrong'
            elif mode == 'direct_gap':
                other = copy.deepcopy(branch); other['edge_id'] = 'GAP'; other['start_node_id'] = 'VC'; other['end_node_id'] = 'VA'
                other['source_handles'] = [c['branch_handle'] for c in self.repair['connections']]; g['edges'].append(other)
            with self.subTest(mode=mode), self.assertRaises(ValueError): self.run_reconcile(graph=g)

    def test_reject_changed_source_circle_and_broken_main(self):
        circle = self.doc.entitydb[self.repair['connections'][1]['circle_handle']]
        circle.dxf.center = (701, 0)
        with self.assertRaises(ValueError): self.run_reconcile()
        circle.dxf.center = (700, 0)
        edge = next(e for e in self.graph['edges'] if e['start_node_id'].startswith('T-OVERLAP') and e['end_node_id'].startswith('T-OVERLAP'))
        edge['source_handles'] = ['wrong']
        with self.assertRaises(ValueError): self.run_reconcile()

    def test_repair_chain_and_duplicate_conflicts(self):
        self.graph['userConfirmedOverlappingBranches'] = {'records': [], 'previous_repair': self.graph['userConfirmedOverlappingBranches']}
        out, _ = self.run_reconcile()
        self.assertEqual(out['sourceCircleCrossoverConflicts'], [])
        self.graph['sourceCircleCrossoverConflicts'] *= 2
        with self.assertRaises(ValueError): self.run_reconcile()


if __name__ == '__main__':
    unittest.main()
