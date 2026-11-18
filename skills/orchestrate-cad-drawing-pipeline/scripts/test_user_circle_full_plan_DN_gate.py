import unittest
from test_current_circle_full_plan_DN_gate import current_fixture
from user_circle_full_plan_DN_gate import check


def fixture():
    data=current_fixture();data.update(previous_circle_mode=data['mode'],mode='complete_local_plan_native_DN_user_circle_endpoint_rays_v4')
    result=data['floors']['1'];review=dict(path='POLICY',sha256='PIN',screen=dict(path='SCREEN',sha256='SCREENPIN'))
    result.update(user_circle_endpoint_nodes=['U'],user_circle_endpoint_review=review,
        user_circle_endpoint_evidence={'U':dict(graph_sha256='G',source_sha256='S',graph_mutated=False,physical_values_assigned=0,
            human_accepted=False,circle_layer_rewritten=False,original_main_rays_replayed=True,
            through_pair_recomputed_from_native_rays=True,original_review=dict(policy=review))})
    result['roles']['U']={}
    return data


class Tests(unittest.TestCase):
    def test_inherited_splits_and_user_corners_both_keep_complete_conflicts_and_unknowns(self):
        report=check(fixture())
        self.assertEqual(report['current_circle_lineage_nodes'],{'1':['T']})
        self.assertEqual(report['user_circle_endpoint_nodes'],{'1':['U']})
        self.assertEqual(report['conflicting_DN_edges'],1)
        self.assertFalse(report['hil_ready'])

    def test_stale_endpoint_proofs_original_policy_and_false_acceptance_fail(self):
        for mode in ('role','exception','graph','source','mutation','metric','human','layer','main','direction','review','inventory'):
            data=fixture();result=data['floors']['1'];proof=result['user_circle_endpoint_evidence']['U']
            if mode=='role':del result['roles']['U']
            elif mode=='exception':result['source_T_exceptions']['U']='missing'
            elif mode=='graph':proof['graph_sha256']='OLD'
            elif mode=='source':proof['source_sha256']='OTHER'
            elif mode=='mutation':proof['graph_mutated']=True
            elif mode=='metric':proof['physical_values_assigned']=1
            elif mode=='human':proof['human_accepted']=True
            elif mode=='layer':proof['circle_layer_rewritten']=True
            elif mode=='main':proof['original_main_rays_replayed']=False
            elif mode=='direction':proof['through_pair_recomputed_from_native_rays']=False
            elif mode=='review':proof['original_review']['policy']={}
            else:result['user_circle_endpoint_nodes']=[]
            with self.subTest(mode=mode),self.assertRaises(ValueError):check(data)


if __name__=='__main__':unittest.main()
