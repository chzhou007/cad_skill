import copy,json,tempfile,unittest
from pathlib import Path
from refresh_axis_rule_vertical_DN import delta,provider_from

class AxisRulePublicationTests(unittest.TestCase):
    def fixture(self):
        rows=[dict(edge_id='E',path_index=0,segment_index=0,nominal_mm=80),dict(edge_id='E',path_index=0,segment_index=2,nominal_mm=80)]
        context=dict(axis_rule_vertical_DN=dict(records=rows,source_bindings=dict(native_source='S')))
        old=[dict(edge_id='E',values=dict(old_plan_DN=300,axis_nested_pair_vertical_DN_segments_json='old-pair',axis_omission_vertical_DN_segments_json='old-omission',unknown_length=None)),dict(edge_id='OTHER',values={'unchanged':'yes'})]
        new=copy.deepcopy(old);new[0]['values'].update(axis_rule_vertical_DN_segment_count=2,axis_rule_vertical_DN_segments_json=json.dumps(rows),axis_rule_vertical_DN_source_sha256='S');return old,new,context
    def test_full_older_reader_values_remain_exact(self):
        old,new,c=self.fixture();r=delta(old,new,c);self.assertEqual(r['changed_edges'],['E']);self.assertEqual(r['new_vertical_domains'],2);self.assertTrue(r['all_old_effective_values_exact']);self.assertEqual(r['new_physical_lengths'],0)
    def test_changes_to_old_DN_length_context_or_unrelated_edges_are_rejected(self):
        for field in('old_plan_DN','axis_nested_pair_vertical_DN_segments_json','axis_omission_vertical_DN_segments_json','unknown_length'):
            old,new,c=self.fixture();new[0]['values'][field]=0
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'historical'):delta(old,new,c)
        old,new,c=self.fixture();new[1]['values']['unchanged']='changed'
        with self.assertRaises(ValueError):delta(old,new,c)
    def test_missing_or_wrong_new_native_domain_is_rejected(self):
        for field,value in [('axis_rule_vertical_DN_segment_count',1),('axis_rule_vertical_DN_segments_json','[]'),('axis_rule_vertical_DN_source_sha256','other')]:
            old,new,c=self.fixture();new[0]['values'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):delta(old,new,c)
    def test_provider_keeps_all_prior_observations_and_records_legacy_stale_counter(self):
        old=dict(counts=dict(all_current_vertical_DN_domains=309,existing_correspondence_edges=506),all_current_vertical_DN_domains=260,records=[{'old':'unchanged'}],ordinary_junction_mappings=[{'T':'source'}],nested_pair_axis_vertical_DN={'new_domains':16})
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp)/'provider.json';p.write_text(json.dumps(old),encoding='utf8');proofpath=Path(tmp)/'proof.json';proofpath.write_text('{}',encoding='utf8');proof=dict(inputs=dict(parent_provider=dict(path=str(p))),counts=dict(previous_known=309,current_known=357),records=[{}]*48);r=provider_from(proof,proofpath)
            self.assertEqual(r['all_current_vertical_DN_domains'],357);self.assertEqual(r['counts']['all_current_vertical_DN_domains'],357);self.assertEqual(r['history_counts_before_axis_rule_axis_DN'],dict(counts=old['counts'],legacy_top_level_vertical_domains=260));self.assertEqual(r['axis_rule_vertical_DN']['new_domains'],48)
            for name in('records','ordinary_junction_mappings','nested_pair_axis_vertical_DN'):self.assertEqual(r[name],old[name])
            self.assertEqual(json.loads(p.read_text()),old);proof['counts']['previous_known']=308
            with self.assertRaises(ValueError):provider_from(proof,proofpath)

if __name__=='__main__':unittest.main()
