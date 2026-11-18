import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_crossview_inventory


class Tests(unittest.TestCase):
    def data(self):
        return dict(status='source_comparison_inventory_not_mapping',records=[dict(ready_for_mapping_comparison=True),dict(ready_for_mapping_comparison=False)],
            counts=dict(equipment=2,ready_for_mapping_comparison=1),local_graphs_mutated=False,mapped_paths=0,human_accepted=False,hil_ready=False,
            inherited_circle_branch_extension=dict(mode='inherited_circle_endpoint_branch_inventory_v3',records=[dict(source_scope='replayed')],
                local_graphs_mutated=False,mapped_paths=0,physical_ports_verified=False,human_accepted=False))

    def test_new_mode_uses_independent_versioned_reader_and_stays_mapping_and_HIL_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'inventory-receipt.json').write_text(json.dumps(dict(mode='inherited_circle_endpoint_branch_inventory_v3')),'utf8')
            with patch('inherited_circle_branch_inventory.verify_output',return_value=self.data()) as current,patch('crossview_equipment_branch_inventory_v2.verify_output') as old:
                result=validate_crossview_inventory(tmp)
            current.assert_called_once_with(tmp);old.assert_not_called();self.assertEqual(result['ready_for_mapping_comparison'],1)
            self.assertEqual(result['status'],'pending');self.assertEqual(result['mapped_paths'],0);self.assertFalse(result['hil_ready'])

    def test_native_failure_and_false_local_or_global_claims_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'inventory-receipt.json').write_text(json.dumps(dict(mode='inherited_circle_endpoint_branch_inventory_v3')),'utf8')
            with patch('inherited_circle_branch_inventory.verify_output',side_effect=ValueError('native circle changed')),self.assertRaisesRegex(ValueError,'native circle changed'):validate_crossview_inventory(tmp)
            for case in ('root','physical','local_graph','local_mapping','local_HIL','global_HIL','counts'):
                data=self.data();root=data['inherited_circle_branch_extension']
                if case=='root':root['records']=[]
                elif case=='physical':root['physical_ports_verified']=True
                elif case=='local_graph':root['local_graphs_mutated']=True
                elif case=='local_mapping':root['mapped_paths']=1
                elif case=='local_HIL':root['human_accepted']=True
                elif case=='global_HIL':data['hil_ready']=True
                else:data['counts']['ready_for_mapping_comparison']=2
                with self.subTest(case=case),patch('inherited_circle_branch_inventory.verify_output',return_value=data),self.assertRaises(ValueError):validate_crossview_inventory(tmp)


if __name__=='__main__':unittest.main()
