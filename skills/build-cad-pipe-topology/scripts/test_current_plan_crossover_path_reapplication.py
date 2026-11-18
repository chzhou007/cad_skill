import unittest
from unittest.mock import patch
from current_plan_crossover_path_reapplication import audit
class CurrentMainCrossover(unittest.TestCase):
    def fixture(self):
        graph=dict(nodes=[dict(node_id='T')],edges=[dict(edge_id=e,start_node_id='T',end_node_id=e,system='return',attribute_paths=[[[0,0],[1,0]],[[2,0],[3,0]]])for e in ['B','M1','M2']])
        # The helper index requires complete endpoint inventory.
        graph['nodes'] += [dict(node_id=e)for e in ['B','M1','M2']]
        current=dict(status='native_historical_circle_ray_evidence_unreviewed',source_sha256='S',graph_sha256='G',graph_mutated=False,historical_reader_or_globals_changed=False,
            junctions=[dict(node_id='T',source_rays=[dict(edge_id='B',scope='historical_source_reviewed_circle_rim'),dict(edge_id='M1'),dict(edge_id='M2')])],
            current_main_lineage=[dict(kind='source_bound_main_split',current_edge_id='M1',original_edge_id='OLD',parent_sha256='a'*64)])
        return graph,current
    def test_reuses_current_native_main_ancestry_and_original_gap_replayer(self):
        graph,current=self.fixture();proof=dict(status='native_source_paths_and_excluded_crossovers_replayed',graph_mutated=False,paths=[dict(original_path_index=0,coverage=dict(segments=[dict(drawing_length=1)]))],crossovers=[{}])
        with patch('current_plan_crossover_path_reapplication.branch_coverage',return_value=proof)as old:
            value=audit(None,graph,'B','T','S','G',lambda *args:current);old.assert_called_once_with(None,graph,graph['edges'][0],'S','G')
        self.assertTrue(value['edges'][0]['current_main_lineage_reapplied']);self.assertEqual(value['physical_gap_lengths_assigned'],0)
    def test_wrong_hash_branch_star_or_parent_never_bypasses_original_source_rules(self):
        for mutate in [lambda c:c.update(graph_sha256='WRONG'),lambda c:c['junctions'][0]['source_rays'][0].update(edge_id='M1'),lambda c:c['current_main_lineage'][0].update(parent_sha256='bad')]:
            graph,current=self.fixture();mutate(current)
            with patch('current_plan_crossover_path_reapplication.branch_coverage')as old,self.assertRaises(ValueError):audit(None,graph,'B','T','S','G',lambda *args:current)
            old.assert_not_called()
    def test_no_current_lineage_uses_original_whole_path_owner(self):
        graph,current=self.fixture();current['current_main_lineage']=[]
        with patch('current_plan_crossover_path_reapplication.original_audit',return_value={'old':'exact'})as old:
            self.assertEqual(audit(None,graph,'B','T','S','G',lambda *args:current),{'old':'exact'});self.assertTrue(old.called)
if __name__=='__main__':unittest.main()
