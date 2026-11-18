import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_inherited_circle_plan_attributes


class Tests(unittest.TestCase):
    def data(self):
        from inherited_circle_plan_attributes import MODE
        rows=[]
        for system in ('supply','return'):
            for kind,count in [('equipment_branch',3),('main_between_equipment_branches',2)]:
                for i in range(count):
                    key=system+kind+str(i)
                    rows.append(dict(mapping_id=key,kind=kind,floor=3,system=system,plan_edges=[key],iso_edges=['I'+key],
                        diameter=dict(edge_id=key,system=system,nominal_mm=150,lineage=[dict(evidence=['source'])]),
                        horizontal_projection=dict(value_mm=500,pieces=[dict(length_mm=500)],installed_whole_edge_length_mm=None,unshown_connection_length_mm=None),
                        physical_source_identity_resolved=False,physical_ports_verified=False,whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,human_accepted=False))
        return dict(mode=MODE,status='source_checked_inherited_circle_plan_DN_and_XY_not_fused',floor=3,equipment_scope=['D0','D1','D2'],records=rows,
            source_sha256='S',graph_sha256='G',mapping_sha256='M',local_graphs_mutated=False,physical_values_fused=False,physical_ports_verified=False,
            physical_source_identity_resolved=False,whole_axis_DN_assigned=0,installed_lengths_assigned=0,human_accepted=False)

    def test_formal_entry_runs_independent_owner_and_keeps_fusion_and_HIL_pending(self):
        with patch('inherited_circle_plan_attributes.verify_output',return_value=self.data()) as verify:
            result=validate_inherited_circle_plan_attributes('run')
        verify.assert_called_once_with('run');self.assertEqual(result['source_replay'],'passed');self.assertEqual(result['mapped_DN_XY_scopes'],10)
        self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready']);self.assertFalse(result['physical_values_fused'])

    def test_stale_native_inputs_missing_scope_or_promoted_physical_values_fail(self):
        with patch('inherited_circle_plan_attributes.verify_output',side_effect=ValueError('source changed')),self.assertRaisesRegex(ValueError,'source changed'):
            validate_inherited_circle_plan_attributes('run')
        for case in ('extent','system','DN','metric','duplicate','physical','HIL','axisDN','identity','source_edge','floor'):
            data=self.data();row=data['records'][0]
            if case=='extent':data['records'].pop()
            elif case=='system':row['system']='return'
            elif case=='DN':row['diameter']['nominal_mm']=None
            elif case=='metric':row['horizontal_projection']['value_mm']=float('nan')
            elif case=='duplicate':row['mapping_id']=data['records'][1]['mapping_id']
            elif case=='physical':row['horizontal_projection']['installed_whole_edge_length_mm']=500
            elif case=='HIL':data['human_accepted']=True
            elif case=='axisDN':row['whole_axis_DN_selected']=True
            elif case=='identity':data['physical_source_identity_resolved']=True
            elif case=='source_edge':row['diameter']['edge_id']='other'
            else:row['floor']=2
            with self.subTest(case=case),patch('inherited_circle_plan_attributes.verify_output',return_value=data),self.assertRaises(ValueError):validate_inherited_circle_plan_attributes('run')


if __name__=='__main__':unittest.main()
