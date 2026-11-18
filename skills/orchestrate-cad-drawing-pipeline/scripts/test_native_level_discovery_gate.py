import unittest
from test_discover_native_level_markers import fixture
from discover_native_level_markers import discover
from native_level_discovery_gate import check

class Tests(unittest.TestCase):
    def test_original_source_marker_proof_does_not_assign_pipe_length_or_HIL(self):
        doc,_,source=fixture();report=check(discover(doc,source));self.assertEqual(report['accepted_markers'],3);self.assertEqual(report['accepted_stacks'],1);self.assertFalse(report['hil_ready'])

    def test_source_change_shared_symbols_and_metric_promotion_are_rejected(self):
        import copy
        for mode in('source','shared','metric','floor','group_metric','HIL'):
            doc,_,source=fixture();result=discover(doc,source)
            if mode=='source':result['groups'][0]['verification']['source_sha256']='b'*64
            elif mode=='shared':result['groups'].append(copy.deepcopy(result['groups'][0]))
            elif mode=='metric':result['physical_lengths_assigned']=1
            elif mode=='floor':result['pipe_floors_assigned']=1
            elif mode=='group_metric':result['groups'][0]['verification']['consecutive_datum_differences'][0]['physical_pipe_length']=0
            else:result['hil_ready']=True
            with self.subTest(mode=mode),self.assertRaises(ValueError):check(result)

if __name__=='__main__':unittest.main()
