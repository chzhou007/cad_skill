import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_named_riser_plan_attributes


class Tests(unittest.TestCase):
    def data(self):
        return dict(status='source_checked_named_floor_approach_DN_and_XY_projection_not_fused',
            source_sha256='P',graph_sha256='PG',local_graphs_mutated=False,physical_ports_verified=False,
            physical_values_fused=False,human_accepted=False,installed_lengths_assigned=0,
            records=[dict(system=s,diameter=dict(nominal_mm=300),horizontal_projection=dict(value_mm=5000,installed_whole_edge_length_mm=None),
                          installed_whole_edge_length_mm=None,plan_glyph_radius_added_to_length=False,
                          physical_port_verified=False,human_accepted=False) for s in ('supply','return')])
    def test_fresh_source_replay_retains_partial_attribute_and_acceptance_status(self):
        with patch('named_riser_plan_attributes.verify_output',return_value=self.data()) as verify:
            result=validate_named_riser_plan_attributes('RUN')
        verify.assert_called_once_with('RUN')
        self.assertEqual(result['source_replay'],'passed');self.assertEqual(result['named_floor_approach_DN_and_plan_projection_scopes'],2)
        self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
    def test_no_radius_installed_length_wrong_system_or_nonfinite_value_is_promoted(self):
        bad=[]
        for key in ('local_graphs_mutated','physical_ports_verified','physical_values_fused','human_accepted'):
            item=self.data();item[key]=True;bad.append(item)
        for key,value in [('plan_glyph_radius_added_to_length',True),('installed_whole_edge_length_mm',5000),('system','return')]:
            item=self.data();item['records'][0][key]=value;bad.append(item)
        for value in (True,float('nan'),0):
            item=self.data();item['records'][0]['diameter']['nominal_mm']=value;bad.append(item)
        for item in bad:
            with self.subTest(item=item),patch('named_riser_plan_attributes.verify_output',return_value=item),self.assertRaises(ValueError):
                validate_named_riser_plan_attributes('RUN')
        with patch('named_riser_plan_attributes.verify_output',side_effect=ValueError('source changed')),self.assertRaises(ValueError):
            validate_named_riser_plan_attributes('RUN')


if __name__=='__main__':unittest.main()
