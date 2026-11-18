import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_wave_rebased_plan_attributes
from wave_rebased_plan_attributes import MODE
import test_inherited_circle_plan_attribute_gate as old_gate


def data():
    group=old_gate.Tests().data();group['group_id']='A'
    return dict(mode=MODE,status='native_plan_DN_XY_recomputed_view_comparison_and_fusion_pending',groups=[group],
        records=[dict(row,group_id='A') for row in group['records']],equipment_scope=group['equipment_scope'],source_sha256='S',graph_sha256='G',mapping_sha256='M',
        old_calibration_acceptance_reused=False,local_graphs_mutated=False,physical_values_fused=False,axis_conflicts_resolved=False,
        whole_axis_DN_assigned=0,installed_lengths_assigned=0,human_accepted=False,hil_ready=False)


class Tests(unittest.TestCase):
    def test_formal_entry_requires_independent_native_owner_and_keeps_pending(self):
        with patch('wave_rebased_plan_attributes.verify_output',return_value=data()) as verify:
            result=validate_wave_rebased_plan_attributes('run')
        verify.assert_called_once_with('run');self.assertEqual(result['mapped_DN_XY_scopes'],10)
        self.assertEqual(result['independent_groups'],1);self.assertFalse(result['physical_values_fused']);self.assertFalse(result['hil_ready'])

    def test_native_dependency_failure_or_whole_edge_promotion_blocks(self):
        with patch('wave_rebased_plan_attributes.verify_output',side_effect=ValueError('native mapping changed')),self.assertRaisesRegex(ValueError,'native mapping changed'):
            validate_wave_rebased_plan_attributes('run')
        changed=data();changed['groups'][0]['records'][0]['whole_axis_DN_selected']=True
        with patch('wave_rebased_plan_attributes.verify_output',return_value=changed),self.assertRaises(ValueError):validate_wave_rebased_plan_attributes('run')


if __name__=='__main__':unittest.main()
