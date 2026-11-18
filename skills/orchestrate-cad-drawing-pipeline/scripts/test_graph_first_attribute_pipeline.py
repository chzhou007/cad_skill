import unittest
from pathlib import Path
from unittest.mock import patch
from cycle_gate_plan_lengths import MODE
from pipeline import validate_cycle_gate_plan_lengths,validate_graph_first_attribute_viewer,validate_graph_first_provider_inventory
from graph_first_provider_inventory import MODE as INVENTORY_MODE

class Tests(unittest.TestCase):
    def test_metric_gate_does_not_promote_DN_vertical_or_installed_values(self):
        p=dict(mode=MODE,cycle_correspondences_independently_replayed=True,original_metric_readers_reused=True,local_graphs_changed=False,DN_values_assigned=0,vertical_values_assigned=0,installed_lengths_assigned=0,human_accepted=False,counts={})
        with patch('cycle_gate_plan_lengths.verify_output',return_value=p):self.assertEqual(validate_cycle_gate_plan_lengths(Path('native'))['native_cycle_gate_plan_lengths'],'passed')
        for k in('DN_values_assigned','vertical_values_assigned','installed_lengths_assigned'):
            with self.subTest(key=k),patch('cycle_gate_plan_lengths.verify_output',return_value=dict(p,**{k:1})),self.assertRaises(ValueError):validate_cycle_gate_plan_lengths(Path('native'))
    def test_viewer_and_inventory_pass_remain_pending_HIL(self):
        with patch('refresh_graph_first_attributes.verify',return_value=dict(status='pending',artifact_replay='passed',human_accepted=False)):
            self.assertEqual(validate_graph_first_attribute_viewer(Path('viewer'))['status'],'pending')
        p=dict(mode=INVENTORY_MODE,current_viewer_and_complete_original_inventory_replayed=True,member_namespaces_preserved=True,new_correspondences_assigned=0,DN_or_length_values_assigned=0,human_accepted=False,counts={})
        with patch('graph_first_provider_inventory.verify_output',return_value=p):self.assertEqual(validate_graph_first_provider_inventory(Path('native'))['graph_first_provider_inventory'],'passed')

if __name__=='__main__':unittest.main()
