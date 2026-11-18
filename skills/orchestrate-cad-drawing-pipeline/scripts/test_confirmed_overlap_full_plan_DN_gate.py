import unittest
from test_user_circle_full_plan_DN_gate import fixture as previous_fixture
from confirmed_overlap_full_plan_DN_gate import check


def fixture():
    data=previous_fixture();data.update(previous_user_circle_mode=data['mode'],mode='complete_local_plan_native_DN_confirmed_overlap_roles_v5')
    result=data['floors']['1'];owner=dict(policy={'path':'P','sha256':'P'})
    result.update(confirmed_overlap_T_nodes=['O'],confirmed_overlap_owner_inputs=[owner],
        confirmed_overlap_T_evidence={'O':dict(graph_sha256='G',source_sha256='S',original_owner=owner,original_owner_replayed=True,
            graph_mutated=False,physical_values_assigned=0,human_accepted=False,display_route_is_physical=False,hidden_connection_length_mm=None)})
    result['roles']['O']={};return data


class Tests(unittest.TestCase):
    def test_all_prior_scope_readers_and_overlap_unknown_lengths_are_retained(self):
        report=check(fixture())
        self.assertEqual(report['confirmed_overlap_T_nodes'],{'1':['O']})
        self.assertEqual(report['user_circle_endpoint_nodes'],{'1':['U']})
        self.assertEqual(report['current_circle_lineage_nodes'],{'1':['T']})
        self.assertEqual(report['conflicting_DN_edges'],1);self.assertFalse(report['hil_ready'])

    def test_stale_roots_false_metrics_and_symbolic_pipes_are_rejected(self):
        for mode in('role','exception','graph','source','owner','replay','mutation','metric','human','display','length','inventory'):
            data=fixture();result=data['floors']['1'];proof=result['confirmed_overlap_T_evidence']['O']
            if mode=='role':del result['roles']['O']
            elif mode=='exception':result['source_T_exceptions']['O']='missing'
            elif mode=='graph':proof['graph_sha256']='OLD'
            elif mode=='source':proof['source_sha256']='OTHER'
            elif mode=='owner':result['confirmed_overlap_owner_inputs']=[]
            elif mode=='replay':proof['original_owner_replayed']=False
            elif mode=='mutation':proof['graph_mutated']=True
            elif mode=='metric':proof['physical_values_assigned']=1
            elif mode=='human':proof['human_accepted']=True
            elif mode=='display':proof['display_route_is_physical']=True
            elif mode=='length':proof['hidden_connection_length_mm']=0
            else:result['confirmed_overlap_T_nodes']=[]
            with self.subTest(mode=mode),self.assertRaises(ValueError):check(data)


if __name__=='__main__':unittest.main()
