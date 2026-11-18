import unittest
from pathlib import Path
from unittest.mock import patch
from rebuild_alias_member_inline_bridges import MODE
from pipeline import validate_alias_member_inline_bridges,reconstruct_alias_member_inline_bridges

class Tests(unittest.TestCase):
    def test_technical_proof_keeps_lengths_and_HIL_separate(self):
        proof=dict(mode=MODE,parent_alias_interfaces_independently_replayed=True,old_interface_records_retained=True,
            all_vertical_attributes_from11=True,source_drawing_graphs_unchanged=True,member_topology_rebuilt=True,
            original_component_assignments_mutated=False,whole_centerline_lengths_assigned=0,installed_lengths_assigned=0,
            human_accepted=False,counts={},pending=[])
        with patch('rebuild_alias_member_inline_bridges.verify_output',return_value=proof):r=validate_alias_member_inline_bridges(Path('run'))
        self.assertEqual(r['status'],'pending');self.assertEqual(r['native_alias_member_inline_bridges'],'passed');self.assertFalse(r['human_accepted'])
        for key,value in [('whole_centerline_lengths_assigned',1),('all_vertical_attributes_from11',False),('original_component_assignments_mutated',True),('human_accepted',True)]:
            changed=dict(proof,**{key:value})
            with self.subTest(key=key),patch('rebuild_alias_member_inline_bridges.verify_output',return_value=changed),self.assertRaises(ValueError):validate_alias_member_inline_bridges(Path('run'))
    def test_formal_reconstruction_replays_native_owner_and_validation(self):
        with patch('rebuild_alias_member_inline_bridges.produce')as produce,patch('pipeline.validate_alias_member_inline_bridges',return_value={})as verify:
            reconstruct_alias_member_inline_bridges(Path('manifest'),Path('output'))
        produce.assert_called_once_with(Path('manifest'),Path('output'));verify.assert_called_once_with(Path('output'))
if __name__=='__main__':unittest.main()
