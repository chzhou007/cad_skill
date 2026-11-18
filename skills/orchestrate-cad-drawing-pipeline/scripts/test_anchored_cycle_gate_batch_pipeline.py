import unittest
from pathlib import Path
from unittest.mock import patch
from rebuild_anchored_cycle_gate_batch import MODE
from pipeline import validate_anchored_cycle_gate_batch,reconstruct_anchored_cycle_gate_batch

class Tests(unittest.TestCase):
    def test_gate_correspondence_cannot_claim_interior_attributes_or_acceptance(self):
        proof=dict(mode=MODE,current_provider_inventory_independently_replayed=True,raw_graphs_unchanged=True,
                   member_namespaces_preserved=True,interior_node_identities_assigned=False,DN_used_for_matching=False,
                   coordinates_used_for_matching=False,shortest_path_used=False,physical_values_assigned=0,human_accepted=False,counts={})
        with patch('rebuild_anchored_cycle_gate_batch.verify_output',return_value=proof):r=validate_anchored_cycle_gate_batch(Path('native'))
        self.assertEqual(r['native_anchored_cycle_gate_batch'],'passed');self.assertEqual(r['status'],'pending')
        for key,value in [('interior_node_identities_assigned',True),('DN_used_for_matching',True),('physical_values_assigned',1),('raw_graphs_unchanged',False),('member_namespaces_preserved',False),('human_accepted',True)]:
            with self.subTest(key=key),patch('rebuild_anchored_cycle_gate_batch.verify_output',return_value=dict(proof,**{key:value})),self.assertRaises(ValueError):validate_anchored_cycle_gate_batch(Path('native'))
    def test_formal_entry_reconstructs_then_independently_validates(self):
        with patch('rebuild_anchored_cycle_gate_batch.produce')as produce,patch('pipeline.validate_anchored_cycle_gate_batch',return_value={})as validate:
            reconstruct_anchored_cycle_gate_batch(Path('manifest'),Path('new'))
        produce.assert_called_once_with(Path('manifest'),Path('new'));validate.assert_called_once_with(Path('new'))

if __name__=='__main__':unittest.main()
