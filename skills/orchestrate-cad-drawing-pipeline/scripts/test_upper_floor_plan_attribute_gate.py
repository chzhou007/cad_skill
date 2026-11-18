import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_upper_floor_plan_attributes


class Tests(unittest.TestCase):
    def data(self):
        rows=[]
        for system in ('supply','return'):
            for kind in ('approach','network_link'):
                key=system+kind
                rows.append(dict(mapping_id=key,system=system,kind='named_riser_floor_segment_'+kind,
                    plan_edges=[key],iso_edges=['axis'+key],diameter=dict(edge_id=key,system=system,nominal_mm=300,
                        lineage=[dict(evidence=[dict(evidence_id='source:DN')])]),
                    iso_segment_scopes=[dict(edge_id='axis'+key,segment_indices=[1],scope_paths=[[[0,0],[1,0]]],whole_local_edge=kind=='network_link')],
                    horizontal_projection=dict(value_mm=1000,pieces=[dict(source_line_handle='L')],installed_whole_edge_length_mm=None,unshown_connection_length_mm=None),
                    whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,physical_port_verified=False,human_accepted=False))
        return dict(status='source_checked_upper_floor_plan_DN_and_XY_scopes_not_fused',records=rows,source_sha256='S',graph_sha256='G',mapping_sha256='M',
            local_graphs_mutated=False,physical_values_fused=False,physical_ports_verified=False,human_accepted=False,whole_axis_DN_assigned=0,installed_lengths_assigned=0)

    def test_fresh_native_replay_retains_partial_scope_and_unknown_lengths(self):
        data=self.data();before=copy.deepcopy(data)
        with patch('named_upper_floor_plan_attributes.verify_output',return_value=data) as verify:
            result=validate_upper_floor_plan_attributes('RUN')
        verify.assert_called_once_with('RUN');self.assertEqual(result['mapped_DN_XY_scopes'],4)
        self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready']);self.assertEqual(before,data)

    def test_physical_claims_missing_services_stale_and_wrong_scope_block(self):
        for case in ('mixed_whole','physical','whole_DN','length','HIL','system','partial_rows','DN_nan','projection_zero','lost_source','fused'):
            data=self.data();row=data['records'][0]
            if case=='mixed_whole':row['iso_segment_scopes'][0]['whole_local_edge']=True
            elif case=='physical':row['physical_port_verified']=True
            elif case=='whole_DN':row['whole_axis_DN_selected']=True
            elif case=='length':row['horizontal_projection']['installed_whole_edge_length_mm']=1000
            elif case=='HIL':data['human_accepted']=True
            elif case=='system':row['diameter']['system']='return'
            elif case=='partial_rows':data['records'].pop()
            elif case=='DN_nan':row['diameter']['nominal_mm']=float('nan')
            elif case=='projection_zero':row['horizontal_projection']['value_mm']=0
            elif case=='lost_source':row['diameter']['lineage']=[]
            else:data['physical_values_fused']=True
            with self.subTest(case=case),patch('named_upper_floor_plan_attributes.verify_output',return_value=data),self.assertRaises(ValueError):
                validate_upper_floor_plan_attributes('RUN')
        with patch('named_upper_floor_plan_attributes.verify_output',side_effect=ValueError('source changed')),self.assertRaises(ValueError):
            validate_upper_floor_plan_attributes('RUN')


if __name__=='__main__':unittest.main()
