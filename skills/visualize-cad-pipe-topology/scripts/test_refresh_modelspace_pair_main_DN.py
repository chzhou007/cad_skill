import json,tempfile,unittest
from pathlib import Path
from refresh_modelspace_pair_main_DN import provider_from
from test_refresh_typed_inline_attribute_DN import TypedAdoptionTests

class PairedMainProviderTests(unittest.TestCase):
    def test_previous_main_T_and_all_other_providers_retained(self):
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp)/'provider.json';target=Path(tmp)/'proof.json';target.write_text('{}',encoding='utf8');old=dict(counts=dict(all_current_vertical_DN_domains=411,pure_horizontal_complete_DN_and_centerline=230),all_current_vertical_DN_domains=411,multiline_main_T_DN={'new_domains':26},typed_inline_attribute_DN={'new_domains':8},records=[{'old':'yes'}]);p.write_text(json.dumps(old),encoding='utf8');source=dict(inputs=dict(parent_provider=dict(path=str(p))),counts=dict(previous_known=411,current_known=447),records=[{}]*36,existing_main_T_requalification=dict(count=46));r=provider_from(source,target)
            self.assertEqual(r['counts']['all_current_vertical_DN_domains'],447);self.assertEqual(r['counts']['pure_horizontal_complete_DN_and_centerline'],230)
            for k in('multiline_main_T_DN','typed_inline_attribute_DN','records'):self.assertEqual(r[k],old[k])
            self.assertEqual(r['modelspace_pair_main_DN']['old_main_T_requalified'],46);self.assertEqual(json.loads(p.read_text()),old);source['counts']['previous_known']=410
            with self.assertRaises(ValueError):provider_from(source,target)

if __name__=='__main__':unittest.main()
