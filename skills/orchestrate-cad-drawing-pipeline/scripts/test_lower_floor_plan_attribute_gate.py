import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_upper_floor_plan_attributes
import test_upper_floor_plan_attribute_gate as upper_fixture


class Tests(unittest.TestCase):
    def data(self):
        data=upper_fixture.Tests().data();data['status']='source_checked_lower_floor_plan_DN_and_XY_scopes_not_fused'
        for r in data['records']:
            r['kind']=r['kind'].replace('named_riser_floor_segment_','named_riser_lower_floor_segment_')
            r['iso_segment_scopes'][0]['segment_indices']=[0,1];r['diameter']['nominal_mm']=200
        return data
    def test_formal_lower_attribute_dispatch_retains_partial_axis_and_unknown_lengths(self):
        with patch('named_lower_floor_plan_attributes.verify_output',return_value=self.data()) as lower,patch('named_upper_floor_plan_attributes.verify_output') as upper:
            result=validate_upper_floor_plan_attributes('RUN',lower=True)
        lower.assert_called_once_with('RUN');upper.assert_not_called();self.assertEqual(result['mapped_DN_XY_scopes'],4)
        self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
    def test_wrong_domain_whole_mixed_length_service_or_missing_source_block(self):
        for case in ('domain','prefix','whole_DN','length','system','no_source','zero','HIL'):
            data=self.data();row=data['records'][0]
            if case=='domain':row['kind']='named_riser_floor_segment_approach'
            elif case=='prefix':row['iso_segment_scopes'][0]['segment_indices']=[1]
            elif case=='whole_DN':row['whole_axis_DN_selected']=True
            elif case=='length':row['whole_axis_physical_length_mm']=4800
            elif case=='system':row['diameter']['system']='return'
            elif case=='no_source':row['diameter']['lineage']=[]
            elif case=='zero':row['horizontal_projection']['value_mm']=0
            else:data['human_accepted']=True
            with self.subTest(case=case),patch('named_lower_floor_plan_attributes.verify_output',return_value=data),self.assertRaises(ValueError):validate_upper_floor_plan_attributes('RUN',lower=True)
        with patch('named_lower_floor_plan_attributes.verify_output',side_effect=ValueError('source changed')),self.assertRaises(ValueError):validate_upper_floor_plan_attributes('RUN',lower=True)


if __name__=='__main__':unittest.main()
