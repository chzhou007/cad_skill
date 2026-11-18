import unittest
from unittest.mock import patch
from pipeline import validate_legacy_named_provider_inventory, reconstruct_legacy_named_provider_inventory
from legacy_named_provider_inventory import MODE


class Tests(unittest.TestCase):
    def data(self):
        return dict(mode=MODE, complete_original_contact_provider_replayed=True,
            current_native_legacy_scopes_replayed=True, all_old_provider_observations_preserved=True,
            all_old_pipe_attributes_and_components_preserved=True, all_legacy_interfaces_and_member_namespaces_separate=True,
            DN_or_length_values_assigned=0, new_correspondences_assigned=0, human_accepted=False, counts={})

    def test_formal_entry_replays_owner_and_keeps_HIL_pending(self):
        with patch('legacy_named_provider_inventory.verify_output', return_value=self.data()):
            self.assertEqual(validate_legacy_named_provider_inventory('run')['status'], 'pending')
        with patch('legacy_named_provider_inventory.produce') as owner, patch('pipeline.validate_legacy_named_provider_inventory', return_value={}):
            reconstruct_legacy_named_provider_inventory('manifest', 'run')
        owner.assert_called_once_with('manifest', 'run')

    def test_incomplete_ancestry_or_scalar_filling_is_rejected(self):
        for key, value in [('complete_original_contact_provider_replayed', False), ('current_native_legacy_scopes_replayed', False), ('all_legacy_interfaces_and_member_namespaces_separate', False), ('DN_or_length_values_assigned', 1)]:
            result = self.data(); result[key] = value
            with self.subTest(key=key), patch('legacy_named_provider_inventory.verify_output', return_value=result), self.assertRaises(ValueError):
                validate_legacy_named_provider_inventory('run')


if __name__ == '__main__': unittest.main()
