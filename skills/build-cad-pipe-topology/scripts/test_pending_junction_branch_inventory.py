import copy
import unittest

from pending_junction_branch_inventory import check_lineage


class JunctionInventoryLineageTests(unittest.TestCase):
    def setUp(self):
        self.local = dict(plan_graph=dict(sha256='OLD'), plan_source=dict(sha256='SOURCE'))
        self.circle = dict(output_graph_sha256='CIRCLE', inputs=dict(graph=dict(sha256='OLD'), source=dict(sha256='SOURCE')))
        self.junction = dict(output_graph_sha256='NEW', inputs=dict(graph=dict(sha256='CIRCLE'), source=dict(sha256='SOURCE')))

    def test_exact_two_stage_descendant(self):
        check_lineage(self.local, self.junction, self.circle, 'NEW')

    def test_same_labels_or_counts_cannot_replace_exact_source_ancestry(self):
        for object_name, path in [('local', ('plan_graph', 'sha256')), ('circle', ('inputs', 'graph', 'sha256')),
                                  ('circle', ('inputs', 'source', 'sha256')), ('junction', ('inputs', 'graph', 'sha256')),
                                  ('junction', ('inputs', 'source', 'sha256')), ('junction', ('output_graph_sha256',))]:
            local, circle, junction = copy.deepcopy((self.local, self.circle, self.junction))
            obj = dict(local=local, circle=circle, junction=junction)[object_name]
            for part in path[:-1]: obj = obj[part]
            obj[path[-1]] = 'WRONG'
            with self.subTest(object_name=object_name, path=path), self.assertRaises(ValueError):
                check_lineage(local, junction, circle, 'NEW')


if __name__ == '__main__':
    unittest.main()
