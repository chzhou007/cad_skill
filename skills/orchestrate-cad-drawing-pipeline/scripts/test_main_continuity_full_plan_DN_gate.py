import unittest
from test_confirmed_overlap_full_plan_DN_gate import fixture as previous_fixture
from main_continuity_full_plan_DN_gate import check


def fixture():
    data=previous_fixture();data.update(previous_overlap_mode=data['mode'],mode='complete_local_plan_native_DN_source_main_continuity_v6')
    result=data['floors']['1'];result['native_main_continuity_nodes']=['U'];result['native_ray_directions_or_graph_geometry_changed']=False
    result['roles']['U']=dict(through=['A','B'],branch='C',original_main_source_edge='ORIGINAL-MAIN',physical_flow_direction_inferred=False,
        role_basis='original_native_center_arm_main_continuity_across_confirmed_circle',source_T_proof=result['user_circle_endpoint_evidence']['U'])
    return data


class Tests(unittest.TestCase):
    def test_semantic_main_basis_keeps_all_prior_features_and_HIL_separate(self):
        report=check(fixture());self.assertEqual(report['native_main_continuity_nodes'],{'1':['U']})
        self.assertFalse(report['human_accepted']);self.assertFalse(report['hil_ready'])

    def test_changed_directions_false_main_partitions_and_missing_native_proofs_fail(self):
        for mode in('inventory','directions','branch','main','proof','flow'):
            data=fixture();result=data['floors']['1'];role=result['roles']['U']
            if mode=='inventory':result['native_main_continuity_nodes']=[]
            elif mode=='directions':result['native_ray_directions_or_graph_geometry_changed']=True
            elif mode=='branch':role['branch']='A'
            elif mode=='main':role['original_main_source_edge']=''
            elif mode=='proof':role['source_T_proof']={}
            else:role['physical_flow_direction_inferred']=True
            with self.subTest(mode=mode),self.assertRaises(ValueError):check(data)


if __name__=='__main__':unittest.main()
