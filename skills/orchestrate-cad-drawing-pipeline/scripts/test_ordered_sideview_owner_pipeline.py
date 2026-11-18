import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from ordered_sideview_equipment_owners import MODE
from pipeline import validate_ordered_sideview_owners,reconstruct_ordered_sideview_owners
class Tests(unittest.TestCase):
    def test_new_plan_owners_require_mapping_recomputation_before_axis_fusion(self):
        proof=dict(mode=MODE,physical_lengths_assigned=0,human_accepted=False,crossview_mapping_recomputed=False,counts=dict(new_equipment_owners=2,new_service_branches=4))
        with patch('rebuild_ordered_sideview_owners.verify_output',return_value=proof):r=validate_ordered_sideview_owners(Path('native'))
        self.assertEqual(r['native_ordered_sideview_owners'],'passed');self.assertEqual(r['status'],'pending');self.assertFalse(r['crossview_mapping_recomputed']);self.assertFalse(r['human_accepted'])
    def test_complete_entry_produces_then_independently_validates(self):
        with patch('rebuild_ordered_sideview_owners.produce')as produce,patch('pipeline.validate_ordered_sideview_owners',return_value={'status':'pending'})as verify:
            reconstruct_ordered_sideview_owners(Path('manifest'),Path('new'))
        produce.assert_called_once_with(Path('manifest'),Path('new'));verify.assert_called_once_with(Path('new'))
    def test_source_change_or_unverified_physical_completion_blocks(self):
        with patch('rebuild_ordered_sideview_owners.verify_output',side_effect=ValueError('native source changed')):
            with self.assertRaises(ValueError):validate_ordered_sideview_owners(Path('native'))
        with patch('rebuild_ordered_sideview_owners.verify_output',return_value=dict(mode=MODE,physical_lengths_assigned=4,human_accepted=False,crossview_mapping_recomputed=False)):
            with self.assertRaises(ValueError):validate_ordered_sideview_owners(Path('native'))
if __name__=='__main__':unittest.main()
