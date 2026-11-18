import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_calibrated_equipment_interface_ownership import fixture
from calibrated_equipment_interface_ownership import screen
from calibrated_ownership_scope_composition import compose,verify_ownership_output,entry_for_policy,MODE
from confirm_crossview_paths import encode


class OwnershipScopeCompositionTests(unittest.TestCase):
    def test_formal_entry_routes_explicit_scope_composition_without_replacing_history(self):
        self.assertEqual(entry_for_policy({}),'calibrated_equipment_interface_ownership.py')
        self.assertEqual(entry_for_policy({'preserve_prior_source_scopes':True}),'calibrated_ownership_scope_composition.py')
        for v in (False,0,'true',None):
            with self.assertRaises(ValueError):entry_for_policy({'preserve_prior_source_scopes':v})
    def run_case(self,graph,doc,model):
        return compose(graph,screen(doc,graph,model),model,dict(expected_equipment_bindings=1,control_graph_sha256='C'),'S','G')

    def test_circle_crossover_wave_and_local_dn_survive_new_equipment_ownership(self):
        for angle,mirror in ((0,False),(90,True),(180,False),(270,True)):
            doc,g,model,_=fixture(angle,mirror)
            for e in g['edges']:
                e.update(path_length_scope='drawing_paths_excluding_source_crossover_gaps_physical_length_unknown',physical_length_status='unknown_source_circle_and_omission',path_length_complete=False,drawing_path_length=765,
                    source_normalized_crossovers=[{'source_handles':['A','B']}],source_wave_omission={'omitted_length':'unknown'},pipe_diameter={'observations':[{'nominal_mm':80}]},length_scope_evidence=[{'kind':'previous_circle_check'}])
            before=copy.deepcopy(g);out,records,_=self.run_case(g,doc,model)
            self.assertEqual(g,before);self.assertEqual(len(records),2)
            for old,new in zip(before['edges'],out['edges']):
                for k in ('path_length_scope','physical_length_status','path_length_complete','drawing_path_length','source_normalized_crossovers','source_wave_omission','pipe_diameter','attribute_paths','path_points','path_length','equipment_names','equipment_counts','source_handles'):self.assertEqual(new[k],old[k],k)
                self.assertEqual(new['length_scope_evidence'][0],old['length_scope_evidence'][0]);self.assertIsNone(new['equipment_connector_length_mm']);self.assertFalse(new['path_length_complete'])
                self.assertEqual(out['sourceLayoutEquipmentOwnership']['records'].count(new['source_layout_equipment_interface']),1)
                self.assertEqual(new['physical_length'],'unknown')
            self.assertTrue(out['sourceLayoutEquipmentOwnership']['prior_edge_scopes_preserved']);self.assertFalse(out['sourceLayoutEquipmentOwnership']['human_accepted'])

    def test_absent_and_explicit_unknown_drawing_values_are_not_filled_or_lost(self):
        doc,g,model,_=fixture();g['edges'][0]['drawing_path_length']=None
        out,_,_=self.run_case(g,doc,model)
        self.assertIsNone(out['edges'][0]['drawing_path_length']);self.assertEqual(out['edges'][1]['drawing_path_length'],1000)
        self.assertEqual(out['edges'][1]['path_length_scope'],'source_drawn_pipe_only')

    def test_previous_pipe_complete_cannot_certify_unshown_device_connector(self):
        doc,g,model,_=fixture();g['edges'][0].update(physical_length_status='complete',path_length_complete=True,path_length_scope='previous_drawn_pipe_complete')
        out,records,_=self.run_case(g,doc,model)
        self.assertFalse(out['edges'][0]['path_length_complete']);self.assertIn('unknown',out['edges'][0]['physical_length_status'])
        record=next(r for r in records if r['edge_id']==g['edges'][0]['edge_id'])
        self.assertEqual(record['prior_edge_length_scope']['physical_length_status'],'complete')

    def test_existing_fusion_measured_connector_or_malformed_lineage_require_reconciliation(self):
        for mode in ('fusion','measured','lineage'):
            doc,g,model,_=fixture()
            if mode=='fusion':g['edges'][0]['cross_view_attributes']={}
            elif mode=='measured':g['edges'][0]['equipment_connector_length_mm']=250
            else:g['edges'][0]['length_scope_evidence']={}
            before=copy.deepcopy(g)
            with self.assertRaises(ValueError):self.run_case(g,doc,model)
            self.assertEqual(g,before)

    def test_receipt_dispatch_preserves_old_verifier_and_rejects_unknown_modes(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'calibrated-equipment-ownership-audit.json'
            with patch('calibrated_equipment_interface_ownership.verify_output',return_value={'old':True}) as previous:
                self.assertEqual(verify_ownership_output(folder),{'old':True});previous.assert_called_once_with(folder)
            p.write_bytes(encode({'mode':MODE}))
            with patch('calibrated_ownership_scope_composition.verify_output',return_value={'new':True}) as current:
                self.assertEqual(verify_ownership_output(folder),{'new':True});current.assert_called_once_with(folder)
            p.write_bytes(encode({'mode':'unsupported'}))
            with self.assertRaisesRegex(ValueError,'unsupported'):verify_ownership_output(folder)


if __name__=='__main__':unittest.main()
