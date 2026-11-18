import unittest
from unittest.mock import patch
from pathlib import Path
from cycle_carrier_guards import MODE
from pipeline import validate_cycle_carrier_guards,reconstruct_cycle_carrier_guards,validate_cycle_carrier_correction_viewer
class Tests(unittest.TestCase):
    def test_guard_cannot_claim_members_lengths_or_human_acceptance(self):
        r=dict(mode=MODE,original_compound_carrier_reader_reused=True,original_provider_and_riser_sources_independently_replayed=True,physical_lengths_assigned=0,physical_member_ids_assigned=0,human_accepted=False,records=[dict(complete_physical_horizontal_length_mm=None,physical_correspondence_confirmed=False)],held_cycle_lengths=1,held_riser_roles=1)
        with patch('cycle_carrier_guards.verify_output',return_value=r):a=validate_cycle_carrier_guards(Path('native'))
        self.assertEqual(a['native_cycle_carrier_guards'],'passed');self.assertEqual(a['status'],'pending')
        for k,v in [('physical_lengths_assigned',1),('physical_member_ids_assigned',1),('human_accepted',True),('original_compound_carrier_reader_reused',False)]:
            with self.subTest(key=k),patch('cycle_carrier_guards.verify_output',return_value=dict(r,**{k:v})),self.assertRaises(ValueError):validate_cycle_carrier_guards(Path('native'))
    def test_rebuild_and_viewer_entries_retain_native_owners(self):
        with patch('cycle_carrier_guards.produce')as p,patch('pipeline.validate_cycle_carrier_guards',return_value={}):reconstruct_cycle_carrier_guards(Path('manifest'),Path('new'))
        p.assert_called_once_with(Path('manifest'),Path('new'))
        with patch('refresh_cycle_carrier_guards.verify',return_value={'artifact_replay':'passed'})as v:validate_cycle_carrier_correction_viewer(Path('bundle'))
        v.assert_called_once_with(Path('bundle'))
if __name__=='__main__':unittest.main()
