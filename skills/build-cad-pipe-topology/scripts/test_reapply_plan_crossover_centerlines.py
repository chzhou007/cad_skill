import unittest
from reapply_plan_crossover_centerlines import pending_length_edges
class CurrentLengthScopeTests(unittest.TestCase):
    def test_existing_known_lengths_and_vertical_scopes_never_become_targets(self):
        report=dict(groups=[dict(classification='horizontal_only',state='both_missing',edge_ids=['A']),dict(classification='horizontal_only',state='only_length_missing',edge_ids=['B']),dict(classification='horizontal_only',state='only_DN_missing',edge_ids=['C']),dict(classification='horizontal_only',state='both_known',edge_ids=['D']),dict(classification='mixed',state='both_missing',edge_ids=['E']),dict(classification='vertical_only',state='both_missing',edge_ids=['F'])])
        self.assertEqual(pending_length_edges(report),{'A','B'})
if __name__=='__main__':unittest.main()
