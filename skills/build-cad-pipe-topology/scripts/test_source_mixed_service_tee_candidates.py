import copy
import unittest
from source_mixed_service_tee_candidates import identify


def sample(branch='supply'):
    return {'nodes':[{'node_id':'T1','node_type':'tee','x':0,'y':0,'mixed_source_contact':True}],
        'edges':[{'edge_id':'A','system':'return','start_node_id':'T1','end_node_id':'A1','path_points':[[0,0],[-10,0]],'source_handles':['a']},
                 {'edge_id':'B','system':'return','start_node_id':'B1','end_node_id':'T1','path_points':[[10,0],[0,0]],'source_handles':['b']},
                 {'edge_id':'C','system':branch,'start_node_id':'T1','end_node_id':'C1','path_points':[[0,0],[0,10]],'source_handles':['c']}]}


def run(g):return identify(g,point_tolerance=.1,straight_angle_tolerance_degrees=2,branch_angle_tolerance_degrees=2)


class CandidateTest(unittest.TestCase):
    def test_known_mixed_tee_is_pending_and_does_not_mutate_graph(self):
        g=sample();before=copy.deepcopy(g);a=run(g)
        self.assertEqual(g,before);self.assertEqual(a['counts']['known_supply_return'],1)
        c=a['candidates'][0];self.assertEqual(c['trunk_edges'],['A','B']);self.assertEqual(c['branch_edge'],'C')
        self.assertFalse(c['physical_connection_confirmed']);self.assertEqual(c['status'],'algorithm_pending')
        self.assertFalse(c['is_overlay_repair_candidate']);self.assertEqual(c['overlay_status'],'not_established_requires_source_symbol_and_project_rule')

    def test_orthogonal_crossing_is_not_an_overlay_decision(self):
        g=sample();before=copy.deepcopy(g);c=run(g)['candidates'][0]
        self.assertEqual(g,before);self.assertFalse(c['is_overlay_repair_candidate']);self.assertIn('orthogonal',c['reason'])

    def test_unknown_service_is_not_supply_return(self):
        a=run(sample('unclassified_water'));self.assertEqual(a['counts']['unknown_service'],1)
        self.assertEqual(a['counts']['known_supply_return'],0)

    def test_shape_and_detached_path_are_not_candidates(self):
        g=sample();g['edges'][2]['path_points']=[[0,0],[8,8]]
        a=run(g);self.assertEqual(a['counts']['candidates'],0);self.assertEqual(len(a['excluded']),1)
        g=sample();g['edges'][2]['path_points']=[[1,0],[1,10]]
        self.assertEqual(run(g)['excluded'][0]['reason'],'missing_unambiguous_local_edge_path')

    def test_rotated_and_mirrored_junction(self):
        g=sample()
        for e in g['edges']:e['path_points']=[[-y,x] for x,y in e['path_points']]
        self.assertEqual(run(g)['counts']['known_supply_return'],1)


if __name__=='__main__':unittest.main()
