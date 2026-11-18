import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_crossview_inventory
from wave_rebased_branch_inventory import MODE


class Tests(unittest.TestCase):
    def data(self):
        return dict(status='source_comparison_inventory_not_mapping',inventory_mode=MODE,records=[dict(ready_for_mapping_comparison=True)],
            counts=dict(equipment=1,ready_for_mapping_comparison=1),local_graphs_mutated=False,mapped_paths=0,human_accepted=False,hil_ready=False,
            wave_reconstruction_inventory_rebase=dict(mode=MODE,old_plan_graph_sha256='OLD',plan_graph_sha256='NEW',
                axis_evidence_preserved_on_identical_inputs=True,transition=dict(equipment_and_owner_roots_preserved=True),
                local_graphs_mutated=False,physical_ports_verified=False,human_accepted=False,mapped_paths=0,physical_values_assigned=0))

    def test_dispatch_runs_new_owner_and_preserves_mapping_and_HIL_pending(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp)/'inventory-receipt.json').write_text(json.dumps(dict(mode=MODE)),'utf8')
            with patch('wave_rebased_branch_inventory.verify_output',return_value=self.data()) as verify,patch('inherited_circle_branch_inventory.verify_output') as old:
                result=validate_crossview_inventory(temp)
            verify.assert_called_once_with(temp);old.assert_not_called();self.assertEqual(result['plan_graph_sha256'],'NEW')
            self.assertEqual(result['source_comparison'],'native_wave_rebased_branch_inventory_replayed');self.assertEqual(result['mapped_paths'],0);self.assertFalse(result['hil_ready'])

    def test_native_failure_wrong_version_axis_or_physical_claim_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp)/'inventory-receipt.json').write_text(json.dumps(dict(mode=MODE)),'utf8')
            with patch('wave_rebased_branch_inventory.verify_output',side_effect=ValueError('new graph changed')),self.assertRaisesRegex(ValueError,'new graph changed'):validate_crossview_inventory(temp)
            for case in ('axis','same_graph','mapped','HIL','owner'):
                data=self.data();r=data['wave_reconstruction_inventory_rebase']
                if case=='axis':r['axis_evidence_preserved_on_identical_inputs']=False
                elif case=='same_graph':r['plan_graph_sha256']='OLD'
                elif case=='mapped':r['mapped_paths']=1
                elif case=='HIL':r['human_accepted']=True
                else:r['transition']['equipment_and_owner_roots_preserved']=False
                with self.subTest(case=case),patch('wave_rebased_branch_inventory.verify_output',return_value=data),self.assertRaises(ValueError):validate_crossview_inventory(temp)


if __name__=='__main__':unittest.main()
