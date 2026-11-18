import copy,unittest
from contact_owner_scope_requalification import logical_branch

class Tests(unittest.TestCase):
    def fixture(self):
        original=dict(kind='equipment_branch',equipment_id='D',mapping_id='M',plan_edges=['P'],iso_edges=['A'])
        obs=dict(plan_edges=['P'],grouped_axis_edges=['A'])
        plan=dict(ready_for_mapping_comparison=True,trace=dict(status='unique_graph_service_to_T',edges=['P'],tee='PT'),physical_ports_verified=False,logical_ownership_basis='source_calibrated_native_layout')
        axis=dict(ready_for_mapping_comparison=True,trace=dict(status='unique_graph_service_to_T',edges=['A'],tee='AT'),physical_ports_verified=False)
        edge=dict(source_layout_equipment_interface=dict(equipment_id='D'),path_length_complete=False)
        return [original,obs,plan,axis,{'PT':'AT'},edge,[{}],[{'ball_valve':1}]]
    def test_source_checked_limited_plan_interface_is_not_compared_to_full_axis_detail(self):
        args=self.fixture();before=copy.deepcopy(args);row=logical_branch(*args)
        self.assertEqual(row['status'],'same_source_checked_logical_port_mapping_retained');self.assertFalse(row['physical_unshown_length_assigned']);self.assertEqual(args,before)
    def test_empty_profile_without_explicit_source_interface_does_not_pass(self):
        args=self.fixture();args[5]={}
        with self.assertRaises(ValueError):logical_branch(*args)
    def test_old_user_confirmed_interface_keeps_missing_derived_port_field_unknown(self):
        args=self.fixture();args[2].pop('physical_ports_verified');args[2].pop('logical_ownership_basis')
        args[5]=dict(confirmed_equipment_interface=dict(confirmation=dict(confirmed_by='user'),physical_port_verified=False),path_length_complete=False)
        self.assertEqual(logical_branch(*args)['status'],'same_source_checked_logical_port_mapping_retained')
        args[5]['confirmed_equipment_interface']['physical_port_verified']=True
        with self.assertRaises(ValueError):logical_branch(*args)
    def test_unready_native_check_changed_T_and_falsely_physical_ports_fail(self):
        for kind in ('ready','tee','ports','scope'):
            args=self.fixture()
            if kind=='ready':args[2]['ready_for_mapping_comparison']=False
            elif kind=='tee':args[4]['PT']='OTHER'
            elif kind=='ports':args[3]['physical_ports_verified']=True
            else:args[1]['plan_edges']=['OTHER']
            with self.subTest(kind=kind),self.assertRaises(ValueError):logical_branch(*args)
    def test_explicit_plan_component_profile_still_must_agree(self):
        args=self.fixture();args[6]=[{'ball_valve':2}]
        with self.assertRaises(ValueError):logical_branch(*args)
        args[7]=args[6];self.assertEqual(logical_branch(*args)['comparison_domain'],'same_explicit_native_component_profile')

if __name__=='__main__':unittest.main()
