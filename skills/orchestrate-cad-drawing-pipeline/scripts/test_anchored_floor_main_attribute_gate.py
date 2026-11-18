import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_anchored_floor_main_attributes
from anchored_floor_main_plan_attributes import MODE

def fixture():
    metric=dict(value_mm=123.,pieces=[dict(source_line_handle='A')],installed_whole_edge_length_mm=None,unshown_connection_length_mm=None)
    row=dict(mapping_id='M',floor=1,system='supply',plan_edges=['P'],iso_edges=['I'],diameter=dict(edge_id='P',system='supply',nominal_mm=100,status='direct_plan_DN',lineage=[dict(evidence='native')]),
        horizontal_projection=metric,installed_whole_edge_length_mm=None,inline_interiors_unknown=False,physical_ports_verified=False,human_accepted=False)
    return dict(mode=MODE,floor=1,records=[row],local_graphs_mutated=False,physical_values_fused=False,human_accepted=False,hil_ready=False,
        known_DN_records=1,unresolved_DN_records=0,inline_length_incomplete_records=0,source_sha256={},graph_sha256={},preserved_main_value_comparisons=[])

class Tests(unittest.TestCase):
    def test_actual_owner_replayed_pending_even_when_all_values_known(self):
        with patch('anchored_floor_main_plan_attributes.verify_output',return_value=fixture()) as replay:
            result=validate_anchored_floor_main_attributes('RUN')
        replay.assert_called_once_with('RUN');self.assertEqual(result['known_DN_records'],1);self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
    def test_conflict_remains_unknown_with_both_lineages(self):
        data=fixture();dn=data['records'][0]['diameter'];dn.update(nominal_mm=None,status='conflict',lineage=[dict(nominal_mm=200),dict(nominal_mm=450)])
        data.update(known_DN_records=0,unresolved_DN_records=1)
        with patch('anchored_floor_main_plan_attributes.verify_output',return_value=data):result=validate_anchored_floor_main_attributes('RUN')
        self.assertEqual(result['unresolved_DN_records'],1);self.assertEqual(len(result['DN_pending_scopes'][0]['lineage']),2)
    def test_native_failure_is_not_converted_to_pending(self):
        with patch('anchored_floor_main_plan_attributes.verify_output',side_effect=ValueError('native label moved')),self.assertRaisesRegex(ValueError,'native label moved'):
            validate_anchored_floor_main_attributes('RUN')
    def test_duplicate_zero_forged_physical_and_summary_rejected(self):
        for case in ('duplicate','zero_dn','nan_XY','ports','whole_length','inline_span','bad_count','known_conflict','mutated'):
            data=fixture();row=data['records'][0]
            if case=='duplicate':data['records'].append(copy.deepcopy(row))
            elif case=='zero_dn':row['diameter']['nominal_mm']=0
            elif case=='nan_XY':row['horizontal_projection']['value_mm']=float('nan')
            elif case=='ports':row['physical_ports_verified']=True
            elif case=='whole_length':row['installed_whole_edge_length_mm']=123
            elif case=='inline_span':row['inline_interiors_unknown']=True;row['horizontal_projection']['joint_graphic_spans_added']=True
            elif case=='bad_count':data['known_DN_records']=2
            elif case=='known_conflict':row['diameter']['status']='conflict'
            else:data['local_graphs_mutated']=True
            with self.subTest(case=case),patch('anchored_floor_main_plan_attributes.verify_output',return_value=data),self.assertRaises(ValueError):validate_anchored_floor_main_attributes('RUN')
if __name__=='__main__':unittest.main()
