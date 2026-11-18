import copy,json,tempfile,unittest
from pathlib import Path
from refresh_typed_inline_attribute_DN import delta,provider_from

class TypedAdoptionTests(unittest.TestCase):
    def fixture(self):
        rows=[dict(edge_id='E',path_index=0,segment_index=2,nominal_mm=80)]
        old=[dict(edge_id='E',values=dict(plan_DN=300,length=None,old_vertical='preserved')),dict(edge_id='OLD',values=dict(axis_rule_vertical_DN_segments_json='old-T-record',axis_rule_vertical_DN_segment_count=1))]
        new=copy.deepcopy(old);new[0]['values'].update(axis_rule_vertical_DN_segment_count=1,axis_rule_vertical_DN_segments_json=json.dumps(rows),axis_rule_vertical_DN_source_sha256='S');context=dict(axis_rule_vertical_DN=dict(records=rows,source_bindings=dict(native_source='S')));return old,new,context,rows
    def test_only_empty_fields_on_native_targets_change(self):
        old,new,c,rows=self.fixture();r=delta(old,new,c,rows);self.assertEqual(r['changed_edges'],['E']);self.assertEqual(r['new_columns'],0);self.assertEqual(r['new_lengths'],0)
    def test_old_T_horizontal_vertical_and_length_changes_rejected(self):
        for field in('plan_DN','length','old_vertical'):
            old,new,c,rows=self.fixture();new[0]['values'][field]=0
            with self.subTest(field=field),self.assertRaises(ValueError):delta(old,new,c,rows)
        old,new,c,rows=self.fixture();new[1]['values']['axis_rule_vertical_DN_segments_json']='changed'
        with self.assertRaises(ValueError):delta(old,new,c,rows)
        old,new,c,rows=self.fixture();old[0]['values']['axis_rule_vertical_DN_segment_count']=0
        with self.assertRaises(ValueError):delta(old,new,c,rows)
    def test_new_scope_missing_or_wrong_proof_rejected(self):
        for field,value in [('axis_rule_vertical_DN_segment_count',0),('axis_rule_vertical_DN_segments_json','[]'),('axis_rule_vertical_DN_source_sha256','OTHER')]:
            old,new,c,rows=self.fixture();new[0]['values'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):delta(old,new,c,rows)
    def test_provider_retains_plan_and_all_old_sources(self):
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp)/'provider.json';proof=Path(tmp)/'proof.json';proof.write_text('{}',encoding='utf8');original=dict(counts=dict(all_current_vertical_DN_domains=377,pure_horizontal_complete_centerline=246),all_current_vertical_DN_domains=377,records=[{'old':'yes'}],axis_rule_vertical_DN={'new_domains':20});p.write_text(json.dumps(original),encoding='utf8');source=dict(inputs=dict(parent_provider=dict(path=str(p))),counts=dict(previous_known=377,current_known=385),records=[{}]*8);result=provider_from(source,proof)
            self.assertEqual(result['counts']['pure_horizontal_complete_centerline'],246);self.assertEqual(result['counts']['all_current_vertical_DN_domains'],385);self.assertEqual(result['records'],original['records']);self.assertEqual(result['axis_rule_vertical_DN'],original['axis_rule_vertical_DN']);self.assertEqual(json.loads(p.read_text()),original)

if __name__=='__main__':unittest.main()
