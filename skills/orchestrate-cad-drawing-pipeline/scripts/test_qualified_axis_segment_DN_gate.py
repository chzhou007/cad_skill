import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_axis_segment_DN


class QualifiedAxisDNGateTests(unittest.TestCase):
    def data(self):return dict(status='segment_candidates_not_accepted',source_sha256='S',graph_sha256='G',observations=[{'DN':450}],
        excluded_competing_source_chains=[['ROOT','STEM']],local_graph_mutated=False,graph_mutated=False,physical_values_fused=False,
        human_accepted=False,original_native_document_unchanged=True,all_other_native_competitors_retained=True)
    def test_formal_source_replay_keeps_whole_riser_and_physical_values_unaccepted(self):
        with patch('native_segment_dn_candidates_v2.verify_output',return_value=self.data()) as verify:
            result=validate_axis_segment_DN('RUN');verify.assert_called_once_with('RUN')
        self.assertEqual(result['source_replay'],'passed');self.assertEqual(result['segment_DN_observations'],1)
        self.assertEqual(result['qualified_display_stems'],1);self.assertEqual(result['whole_edge_DN_assigned'],0);self.assertFalse(result['hil_ready'])
    def test_stale_native_evidence_and_false_acceptance_claims_fail(self):
        with patch('native_segment_dn_candidates_v2.verify_output',side_effect=ValueError('source changed')):
            with self.assertRaisesRegex(ValueError,'source changed'):validate_axis_segment_DN('RUN')
        for key in ('local_graph_mutated','graph_mutated','physical_values_fused','human_accepted','original_native_document_unchanged','all_other_native_competitors_retained'):
            data=self.data();data[key]=not data[key]
            with patch('native_segment_dn_candidates_v2.verify_output',return_value=data):
                with self.subTest(key=key),self.assertRaises(ValueError):validate_axis_segment_DN('RUN')


if __name__=='__main__':unittest.main()
