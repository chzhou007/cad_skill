import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_source_crossview


class Tests(unittest.TestCase):
    def data(self):
        equipment=['D0','D1','D2'];rows=[]
        for system in ('supply','return'):
            for did in equipment:rows.append(dict(kind='equipment_branch',equipment_id=did,system=system))
            for i in range(2):rows.append(dict(kind='main_between_equipment_branches',endpoint_equipment_ids=equipment[i:i+2],system=system))
        for i,row in enumerate(rows):row.update(mapping_id='M'+str(i),physical_source_identity_resolved=False,physical_ports_verified=False,human_accepted=False)
        return dict(status='source_checked_path_correspondence_attributes_pending',records=rows,equipment_scope=equipment,
            local_graphs_mutated=False,expert_confirmation_claimed=False,physical_source_identity_resolved=False,physical_values_assigned=0,human_accepted=False,hil_ready=False)

    def test_formal_entry_replays_new_owner_and_retains_attribute_and_HIL_pending(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp)/'source-mapping-receipt.json').write_text(json.dumps(dict(mode='source_checked_inherited_circle_main_order_paths_v1')),'utf8')
            with patch('match_inherited_circle_crossview_paths.verify_output',return_value=self.data()) as current,patch('match_source_checked_crossview_paths.verify_output') as old:
                result=validate_source_crossview(temp)
            current.assert_called_once_with(temp);old.assert_not_called();self.assertEqual(result['mapped_paths'],10)
            self.assertEqual(result['path_correspondence'],'native_inherited_circle_main_order_replayed');self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])

    def test_native_failure_incomplete_extent_or_physical_identity_claim_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp)/'source-mapping-receipt.json').write_text(json.dumps(dict(mode='source_checked_inherited_circle_main_order_paths_v1')),'utf8')
            with patch('match_inherited_circle_crossview_paths.verify_output',side_effect=ValueError('source changed')),self.assertRaisesRegex(ValueError,'source changed'):validate_source_crossview(temp)
            for case in ('identity','ports','values','HIL','extent','duplicate','missing_branch','system','graph'):
                data=self.data()
                if case=='identity':data['physical_source_identity_resolved']=True
                elif case=='ports':data['records'][0]['physical_ports_verified']=True
                elif case=='values':data['physical_values_assigned']=1
                elif case=='HIL':data['human_accepted']=True
                elif case=='extent':data['records'].pop()
                elif case=='duplicate':data['records'][0]['mapping_id']=data['records'][1]['mapping_id']
                elif case=='missing_branch':data['records'][0]['equipment_id']='unknown'
                elif case=='system':data['records'][0]['system']='unknown'
                else:data['local_graphs_mutated']=True
                with self.subTest(case=case),patch('match_inherited_circle_crossview_paths.verify_output',return_value=data),self.assertRaises(ValueError):validate_source_crossview(temp)


if __name__=='__main__':unittest.main()
