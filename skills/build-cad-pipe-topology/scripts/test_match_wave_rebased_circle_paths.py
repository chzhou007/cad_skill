import json,tempfile,unittest,copy
from pathlib import Path
from unittest.mock import patch
from match_wave_rebased_circle_paths import compute,verify_output,implementation_hashes,MODE,LOGICAL_MODE,correspond_current,historical_lineage
from wave_rebased_branch_inventory import MODE as INVENTORY_MODE
from confirm_crossview_paths import sha


class Tests(unittest.TestCase):
    def test_private_kernel_replays_ordinary_historical_Ts_without_changing_old_circle_reader(self):
        from test_match_inherited_circle_crossview_paths import fixture
        from match_inherited_circle_crossview_paths import correspond
        from crossview_equipment_branch_inventory import native_tee
        with tempfile.TemporaryDirectory() as temp:
            args=list(fixture(Path(temp)));docs,graphs,inv,cp,policy,hashes=args
            docs['plan']=docs['iso'];graphs['plan']=copy.deepcopy(graphs['iso']);graphs['plan']['metadata']['source_sha256']=hashes['plan']['source_sha256']
            policy['source_main_families']['plan']=copy.deepcopy(policy['source_main_families']['iso'])
            for row in inv['records']:
                row['views']['plan']=copy.deepcopy(row['views']['iso'])
                for state in row['views']['plan']['services'].values():
                    state['junction_evidence']=native_tee(docs['plan'],graphs['plan'],state['trace']['tee'],hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'])
            old_reader=correspond.__globals__['inherited_tee']
            with self.assertRaises(ValueError):correspond(*args)
            result=correspond_current(*args);self.assertEqual(len(result['records']),10)
            self.assertIs(correspond.__globals__['inherited_tee'],old_reader)
            lineage=historical_lineage(result,copy.deepcopy(result),result['plan_graph_sha256'])
            self.assertEqual(len(lineage),10);self.assertTrue(all(not r['human_confirmation_transferred'] for r in lineage))
            previous=copy.deepcopy(result);previous['records'][0]['plan_snapshot']['edges'][0]['system']='return'
            with self.assertRaisesRegex(ValueError,'previously mapped local scope'):historical_lineage(result,previous,result['plan_graph_sha256'])

    def test_new_receipt_requires_complete_new_inventory_native_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ip=root/'inventory.json';rp=root/'inventory-receipt.json';ip.write_text('{}','utf8');rp.write_text(json.dumps(dict(mode=INVENTORY_MODE)),'utf8')
            paths=dict(inventory=ip,inventory_receipt=rp);policy={k+'_sha256':sha(v) for k,v in paths.items()}
            with patch('match_wave_rebased_circle_paths.verify_inventory',side_effect=ValueError('new local graph native replay changed')),self.assertRaisesRegex(ValueError,'new local graph native replay changed'):compute(paths,policy)
            policy['inventory_receipt_sha256']='wrong'
            with self.assertRaisesRegex(ValueError,'input changed'):compute(paths,policy)
            rp.write_text(json.dumps(dict(mode='inherited_circle_endpoint_branch_inventory_v3')),'utf8');policy['inventory_receipt_sha256']=sha(rp)
            with patch('match_wave_rebased_circle_paths.verify_inventory') as verify,self.assertRaisesRegex(ValueError,'new native wave inventory'):compute(paths,policy)
            verify.assert_not_called()

    def test_entry_owner_is_separate_while_logical_schema_reuses_existing_geometry_kernel(self):
        self.assertNotEqual(MODE,LOGICAL_MODE)
        for name in ('wave_rebased_branch_inventory.py','match_inherited_circle_crossview_paths.py','native_canonical_main_family_view.py','inherited_wave_pair_continuity.py'):
            self.assertIn(name,implementation_hashes())
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'source-mapping-receipt.json').write_text(json.dumps(dict(mode=LOGICAL_MODE,logical_mapping_schema=LOGICAL_MODE)),'utf8')
            with self.assertRaisesRegex(ValueError,'owner or implementation'):verify_output(root)


if __name__=='__main__':unittest.main()
