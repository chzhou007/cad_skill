import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_source_crossview
from match_wave_rebased_circle_paths import MODE
import test_inherited_circle_crossview_gate as existing_fixture


class Tests(unittest.TestCase):
    def data(self):
        import copy
        group=existing_fixture.Tests().data();group.update(group_id='G',plan_graph_sha256='NEW',iso_graph_sha256='ISO',source_sha256=dict(plan='S',iso='I'))
        group['historical_mapping_lineage']=[dict(local_path_semantics_preserved=True,human_confirmation_transferred=False) for _ in group['records']]
        result=copy.deepcopy(group);result.update(mode='independent_native_common_anchor_mapping_groups_v1',groups=[group],records=[dict(row,group_id='G') for row in group['records']])
        result['evidence']=dict(native_wave_inventory_rebase=dict(mode='wave_rebased_plan_branch_inventory_v4',plan_graph_sha256='NEW',axis_evidence_preserved_on_identical_inputs=True,
            local_graphs_mutated=False,mapped_paths=0,physical_values_assigned=0,human_accepted=False))
        return result

    def test_receipt_dispatches_new_native_owner_and_retains_pending_values(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp)/'source-mapping-receipt.json').write_text(json.dumps(dict(mode=MODE)),'utf8')
            with patch('match_wave_rebased_circle_paths.verify_output',return_value=self.data()) as verify,patch('match_inherited_circle_crossview_paths.verify_output') as old:
                result=validate_source_crossview(temp)
            verify.assert_called_once_with(temp);old.assert_not_called();self.assertEqual(result['mapped_paths'],10)
            self.assertEqual(result['path_correspondence'],'native_wave_rebased_inherited_circle_main_order_replayed');self.assertFalse(result['hil_ready'])

    def test_stale_graph_missing_axis_preservation_or_native_failure_blocks(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp)/'source-mapping-receipt.json').write_text(json.dumps(dict(mode=MODE)),'utf8')
            with patch('match_wave_rebased_circle_paths.verify_output',side_effect=ValueError('wave source changed')),self.assertRaisesRegex(ValueError,'wave source changed'):validate_source_crossview(temp)
            for case in ('graph','axis','mapped','HIL'):
                data=self.data();r=data['evidence']['native_wave_inventory_rebase']
                if case=='graph':r['plan_graph_sha256']='OLD'
                elif case=='axis':r['axis_evidence_preserved_on_identical_inputs']=False
                elif case=='mapped':r['mapped_paths']=1
                else:r['human_accepted']=True
                with self.subTest(case=case),patch('match_wave_rebased_circle_paths.verify_output',return_value=data),self.assertRaises(ValueError):validate_source_crossview(temp)


if __name__=='__main__':unittest.main()
