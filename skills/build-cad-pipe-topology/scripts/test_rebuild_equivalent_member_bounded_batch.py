import copy,unittest
from rebuild_equivalent_member_bounded_batch import metric_state,_prior_inventory
class Tests(unittest.TestCase):
    def fixture(self):
        g=dict(nodes=[dict(node_id='a',x=0,y=0),dict(node_id='b',x=1000,y=0)])
        e=dict(attribute_paths=[[[0,0],[400,0]],[[400,0],[1000,0]]]);r=dict(plan_start='a',plan_end='b');m=dict(projection=dict(value_mm=1000));return e,m,g,r
    def test_touching_arrays_with_both_source_T_extents_are_complete(self):
        e,m,g,r=self.fixture();self.assertEqual(metric_state(e,m,g,r)['complete_horizontal_centerline_mm'],1000)
        e['attribute_paths']=[list(reversed(p))for p in e['attribute_paths'][::-1]];self.assertEqual(metric_state(e,m,g,r)['complete_horizontal_centerline_mm'],1000)
    def test_inline_gap_or_source_endpoint_omission_never_becomes_complete(self):
        for mode in('explicit','crossover','flexible','gap','rim','missing'):
            e,m,g,r=self.fixture()
            if mode=='explicit':e['path_length_complete']=False
            elif mode=='crossover':e['source_normalized_crossovers']=[{}]
            elif mode=='flexible':e['source_flexible_joints']=[{}]
            elif mode=='gap':e['attribute_paths'][1][0]=[450,0]
            elif mode=='rim':e['attribute_paths'][0][0]=[80,0]
            else:m['projection']=None
            s=metric_state(e,m,g,r)
            with self.subTest(mode=mode):self.assertIsNone(s['complete_horizontal_centerline_mm']);self.assertTrue(s['incomplete_reasons']);self.assertIsNone(s['installed_length_mm'])
    def test_prior_inventory_reserves_all_axis_writers_and_keeps_foreign_plan_namespaces_separate(self):
        axis=dict(edges=[dict(edge_id='a',floor_start=3),dict(edge_id='b',floor_start=2)])
        provider=dict(ordinary_junction_mappings={'3':{'T':'A'}},records=[dict(edge_id='a',correspondence_observations=[dict(plan_edges=['p'],grouped_axis_edges=['a','c'])]),dict(edge_id='b',correspondence_observations=[dict(plan_edges=['p'])])])
        old=copy.deepcopy(provider);r=_prior_inventory(provider,axis,3);self.assertEqual(r['records'],[dict(plan_edges=['p'],iso_edges=['a','c']),dict(plan_edges=[],iso_edges=['b'])]);self.assertEqual(provider,old)
if __name__=='__main__':unittest.main()
