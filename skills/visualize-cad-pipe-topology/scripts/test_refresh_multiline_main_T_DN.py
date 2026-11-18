import json,tempfile,unittest
from pathlib import Path
from refresh_multiline_main_T_DN import provider_from
from test_refresh_typed_inline_attribute_DN import TypedAdoptionTests

class MultilineProviderTests(unittest.TestCase):
    def test_all_previous_source_observations_and_plan_counts_retained(self):
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp)/'provider.json';path=Path(tmp)/'proof.json';path.write_text('{}',encoding='utf8');old=dict(counts=dict(all_current_vertical_DN_domains=385,pure_horizontal_complete_DN_and_centerline=230),all_current_vertical_DN_domains=385,records=[{'old':'source'}],typed_inline_attribute_DN={'new_domains':8},axis_rule_vertical_DN={'new_domains':20});p.write_text(json.dumps(old),encoding='utf8');proof=dict(inputs=dict(parent_provider=dict(path=str(p))),counts=dict(previous_known=385,current_known=415),records=[{}]*30);out=provider_from(proof,path)
            self.assertEqual(out['counts']['all_current_vertical_DN_domains'],415);self.assertEqual(out['counts']['pure_horizontal_complete_DN_and_centerline'],230)
            for key in('records','typed_inline_attribute_DN','axis_rule_vertical_DN'):self.assertEqual(out[key],old[key])
            self.assertEqual(json.loads(p.read_text()),old);self.assertEqual(out['multiline_main_T_DN']['new_domains'],30);proof['counts']['previous_known']=377
            with self.assertRaises(ValueError):provider_from(proof,path)

if __name__=='__main__':unittest.main()
