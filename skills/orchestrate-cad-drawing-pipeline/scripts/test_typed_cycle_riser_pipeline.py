import unittest
from pathlib import Path
from unittest.mock import patch
from rebuild_typed_cycle_riser_batch import MODE
from pipeline import validate_typed_cycle_riser_batch,reconstruct_typed_cycle_riser_batch

class Tests(unittest.TestCase):
    def test_source_gate_preserves_bounded_route_uncertainty_and_domains(self):
        p=dict(mode=MODE,current_complete_provider_inventory_independently_replayed=True,raw_graphs_unchanged=True,ordinary_and_riser_port_domains_separate=True,DN_used_for_matching=False,coordinates_used_for_matching=False,ordinal_identities_assigned=False,physical_values_assigned=0,human_accepted=False,counts={},floors={'2':dict(bounded_route_differences=[dict(individual_mapping_pending=True,attributes_assigned=False)])})
        with patch('rebuild_typed_cycle_riser_batch.verify_output',return_value=p):r=validate_typed_cycle_riser_batch(Path('native'))
        self.assertEqual(r['native_typed_cycle_riser_batch'],'passed');self.assertEqual(r['status'],'pending')
        for key,val in [('ordinary_and_riser_port_domains_separate',False),('ordinal_identities_assigned',True),('physical_values_assigned',1),('human_accepted',True)]:
            with self.subTest(key=key),patch('rebuild_typed_cycle_riser_batch.verify_output',return_value=dict(p,**{key:val})),self.assertRaises(ValueError):validate_typed_cycle_riser_batch(Path('native'))
        p['floors']['2']['bounded_route_differences'][0]['attributes_assigned']=True
        with patch('rebuild_typed_cycle_riser_batch.verify_output',return_value=p),self.assertRaises(ValueError):validate_typed_cycle_riser_batch(Path('native'))
    def test_rebuild_entry_uses_owner_then_source_validation(self):
        with patch('rebuild_typed_cycle_riser_batch.produce')as produce,patch('pipeline.validate_typed_cycle_riser_batch',return_value={})as validate:reconstruct_typed_cycle_riser_batch(Path('manifest'),Path('new'))
        produce.assert_called_once_with(Path('manifest'),Path('new'));validate.assert_called_once_with(Path('new'))

if __name__=='__main__':unittest.main()
