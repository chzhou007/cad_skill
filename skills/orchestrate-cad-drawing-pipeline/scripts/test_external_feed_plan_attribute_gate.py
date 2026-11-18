import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_external_feed_plan_attributes
from test_named_external_feed_plan_attributes import fixture
from named_external_feed_plan_attributes import build_records,MODE


def data():
    rows=build_records(*fixture())
    return dict(mode=MODE,status='source_checked_external_plan_DN_XY_attributes_not_fused',records=rows,known_DN_records=1,inline_length_incomplete_records=1,installed_whole_lengths_assigned=0,local_graphs_mutated=False,physical_values_fused=False,human_accepted=False,hil_ready=False)


class Tests(unittest.TestCase):
    def test_native_owner_replayed_and_even_all_known_DN_keeps_fusion_pending(self):
        with patch('named_external_feed_plan_attributes.verify_output',return_value=data()) as native:result=validate_external_feed_plan_attributes('RUN')
        native.assert_called_once_with('RUN');self.assertEqual(result['known_DN_records'],1);self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
    def test_unknown_lengths_zero_DN_duplicate_and_wrong_summaries_never_pass(self):
        for case in ('whole_length','DN','joint','duplicate','summary','axis_seed','physical'):
            d=data();r=d['records'][0]
            if case=='whole_length':r['installed_whole_edge_length_mm']=0
            elif case=='DN':r['diameter']['nominal_mm']=0
            elif case=='joint':r['horizontal_projection']['joint_graphic_spans_added']=True
            elif case=='duplicate':d['records'].append(copy.deepcopy(r))
            elif case=='summary':d['known_DN_records']=0
            elif case=='axis_seed':r['axis_named_DN_used_as_plan_seed']=True
            else:r['physical_external_connection_verified']=True
            with self.subTest(case=case),patch('named_external_feed_plan_attributes.verify_output',return_value=d),self.assertRaises(ValueError):validate_external_feed_plan_attributes('RUN')
    def test_native_failure_propagates(self):
        with patch('named_external_feed_plan_attributes.verify_output',side_effect=ValueError('label changed')),self.assertRaisesRegex(ValueError,'label changed'):validate_external_feed_plan_attributes('RUN')

if __name__=='__main__':unittest.main()
