import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_wave_plan_scope_adoption
from adopt_wave_rebased_plan_scopes import MODE


def data():
    rows=[dict(edge_id='E'+str(i),added_attribute=i>0,related_HIL_confirmation_inherited=False,human_accepted=False,equal_plan_axis_segment_extents_proved=False) for i in range(3)]
    return dict(mode=MODE,output_graph_sha256='G',human_accepted=False,hil_ready=False,
        proof=dict(records=rows,retained_historical_attributes=1,added_partial_attributes=2,prior_topology_components_and_other_attributes_preserved=True,
            whole_DN_or_lengths_added=0,related_HIL_confirmation_inherited=False,human_accepted=False))


class Tests(unittest.TestCase):
    def test_native_owner_is_replayed_and_historical_partial_counts_remain_separate(self):
        with patch('adopt_wave_rebased_plan_scopes.verify_output',return_value=data()) as replay:
            result=validate_wave_plan_scope_adoption('run')
        replay.assert_called_once_with('run');self.assertEqual(result['current_scope_edges'],3)
        self.assertEqual(result['retained_historical_attributes'],1);self.assertEqual(result['added_partial_attributes'],2);self.assertFalse(result['hil_ready'])

    def test_changed_native_dependency_claimed_whole_values_or_inherited_confirmation_fail(self):
        with patch('adopt_wave_rebased_plan_scopes.verify_output',side_effect=ValueError('source parent changed')),self.assertRaisesRegex(ValueError,'source parent changed'):
            validate_wave_plan_scope_adoption('run')
        for case in ('whole','HIL','count','duplicate'):
            changed=data();proof=changed['proof']
            if case=='whole':proof['whole_DN_or_lengths_added']=1
            elif case=='HIL':proof['records'][0]['related_HIL_confirmation_inherited']=True
            elif case=='count':proof['added_partial_attributes']=1
            else:proof['records'][1]['edge_id']=proof['records'][0]['edge_id']
            with self.subTest(case=case),patch('adopt_wave_rebased_plan_scopes.verify_output',return_value=changed),self.assertRaises(ValueError):validate_wave_plan_scope_adoption('run')


if __name__=='__main__':unittest.main()
