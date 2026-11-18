import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_crossview_inventory

class InventoryGateTests(unittest.TestCase):
    def data(self):
        return dict(status='source_comparison_inventory_not_mapping',records=[dict(ready_for_mapping_comparison=True),dict(ready_for_mapping_comparison=False)],
            counts=dict(equipment=2,ready_for_mapping_comparison=1),local_graphs_mutated=False,mapped_paths=0,human_accepted=False,hil_ready=False)
    def test_native_ready_candidate_never_counts_as_mapping_or_HIL(self):
        with patch('crossview_equipment_branch_inventory.verify_output',return_value=self.data()) as replay:
            result=validate_crossview_inventory('run');replay.assert_called_once_with('run')
        self.assertEqual(result['ready_for_mapping_comparison'],1);self.assertEqual(result['mapped_paths'],0)
        self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
    def test_false_acceptance_and_edited_counts_are_rejected(self):
        for key,value in [('hil_ready',True),('mapped_paths',2),('local_graphs_mutated',True),('counts',{'equipment':2,'ready_for_mapping_comparison':2})]:
            data=self.data();data[key]=value
            with patch('crossview_equipment_branch_inventory.verify_output',return_value=data):
                with self.assertRaises(ValueError):validate_crossview_inventory('run')
    def test_native_replay_failure_is_not_replaced_by_receipt_flags(self):
        with patch('crossview_equipment_branch_inventory.verify_output',side_effect=ValueError('source changed')):
            with self.assertRaisesRegex(ValueError,'source changed'):validate_crossview_inventory('run')
    def test_endpoint_entry_dispatches_to_its_independent_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt=Path(tmp)/'inventory-receipt.json';receipt.write_text(json.dumps(dict(mode='source_endpoint_branch_inventory_v2')),encoding='utf8')
            with patch('crossview_equipment_branch_inventory_v2.verify_output',return_value=self.data()) as replay:
                result=validate_crossview_inventory(tmp);replay.assert_called_once_with(tmp)
            self.assertEqual(result['mapped_paths'],0);self.assertFalse(result['hil_ready'])
            with patch('crossview_equipment_branch_inventory_v2.verify_output',side_effect=ValueError('native endpoint drift')):
                with self.assertRaisesRegex(ValueError,'endpoint drift'):validate_crossview_inventory(tmp)
            receipt.write_text(json.dumps(dict(mode='unknown')),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'entry mode'):validate_crossview_inventory(tmp)

if __name__=='__main__':unittest.main()
