import copy,unittest
from unittest.mock import patch
from confirmed_circle_crossover_path_reapplication import audit
from source_main_DN_continuity import STATUS
class ConfirmedCirclePaths(unittest.TestCase):
    def data(self):
        meta=dict(circle_handle='C',source_graph_sha256='P',screen_sha256='SCREEN')
        graph=dict(nodes=[dict(node_id='T',user_confirmed_circle=meta)]+[dict(node_id=n)for n in('B','M1','M2')],edges=[dict(edge_id=n,start_node_id='T',end_node_id=n,system='return',attribute_paths=[[[0,0],[1,0]],[[2,0],[3,0]]],source_user_circle_connection=copy.deepcopy(meta))for n in('B','M1','M2')])
        proof=dict(status=STATUS,source_sha256='S',graph_sha256='G',original_main_rays_replayed=True,graph_mutated=False,original_review=dict(circle_handle='C',original_graph_sha256='P',native_screen_sha256='SCREEN'),junctions=[dict(node_id='T',system='return',source_rays=[dict(edge_id='B',scope='confirmed_native_circle_rim'),dict(edge_id='M1',scope='confirmed_native_circle_center_LINE_endpoint'),dict(edge_id='M2',scope='confirmed_native_circle_center_LINE_endpoint')])])
        paths=dict(status='native_source_paths_and_excluded_crossovers_replayed',graph_mutated=False,paths=[dict(original_path_index=0,coverage=dict(segments=[dict(drawing_length=1)]))])
        return graph,proof,paths
    def test_explicit_user_circle_branch_uses_original_crossovers(self):
        g,p,paths=self.data()
        with patch('confirmed_circle_crossover_path_reapplication.branch_coverage',return_value=paths)as old:r=audit(None,g,'B','T','S','G',lambda *a:p);old.assert_called_once()
        self.assertTrue(r['edges'][0]['original_user_circle_and_crossover_owners_replayed']);self.assertEqual(r['physical_gap_lengths_assigned'],0)
    def test_changed_confirmation_wrong_source_or_center_arm_never_pass(self):
        for mutate in [lambda p:p.update(source_sha256='wrong'),lambda p:p['original_review'].update(native_screen_sha256='wrong'),lambda p:p['junctions'][0]['source_rays'][0].update(scope='confirmed_native_circle_center_LINE_endpoint')]:
            g,p,paths=self.data();mutate(p)
            with patch('confirmed_circle_crossover_path_reapplication.branch_coverage')as old,self.assertRaises(ValueError):audit(None,g,'B','T','S','G',lambda *a:p)
            old.assert_not_called()
if __name__=='__main__':unittest.main()
