import copy,json,tempfile,unittest
from pathlib import Path
from refresh_reviewed_fragment_detail import provider_binding,provider_from
from confirm_crossview_paths import sha


class ReviewedFragmentPublicationTests(unittest.TestCase):
    def test_actual_provider_requires_current_bundle_receipt_and_current_component_census(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);(root/'public/data').mkdir(parents=True);p=root/'latest-provider.json'
            p.write_text(json.dumps(dict(counts=dict(rendered_component_instances=2))),encoding='utf8')
            (root/'public/data/graph.json').write_text(json.dumps(dict(instances=[{},{}])),encoding='utf8')
            manifest=root/'public/data/manifest.json';manifest.write_text(json.dumps(dict(bundleId='NEW')),encoding='utf8')
            audit=root/'latest-refresh.json';audit.write_text(json.dumps(dict(bundle_id='NEW',output_hashes={p.name:sha(p)})),encoding='utf8')
            self.assertEqual(provider_binding(root,p)['provider']['sha256'],sha(p))
            manifest.write_text(json.dumps(dict(bundleId='OLDER')),encoding='utf8')
            with self.assertRaises(ValueError):provider_binding(root,p)
            manifest.write_text(json.dumps(dict(bundleId='NEW')),encoding='utf8');(root/'public/data/graph.json').write_text(json.dumps(dict(instances=[{}])),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'stale'):provider_binding(root,p)

    def test_old_mapping_DN_frontier_and_original_component_history_are_preserved(self):
        with tempfile.TemporaryDirectory()as folder:
            p=Path(folder)/'native.json';p.write_text(json.dumps(dict(components=[{},{}],records=[])),encoding='utf8')
            old=dict(mode='current',counts=dict(rendered_component_instances=1,current_effective_whole_DN_known=285,pure_horizontal_complete_DN_and_centerline=248),
                current_component_inventory={},records=[dict(edge_id='E',DN=250)],member_domain_observations=[dict(id='M')],ordinary_junction_mappings={'3':{'T1':'T2'}},remaining_horizontal_attributes=[dict(edge_id='X')],
                fragment_component_index={'original':True},history_before_fragment_component_index={'keep_first_history':True},pending_component_detail_differences=[dict(source_handle='NEW')])
            proof=dict(inputs=dict(source_inventory=dict(path=str(p),sha256=sha(p))),audit=dict(current_instances=2),pending_source_components=[],classifications=[],current_component_conservation=dict(new_instances=1))
            result=provider_from(old,proof,'a'*64,p)
            for k in('records','member_domain_observations','ordinary_junction_mappings','remaining_horizontal_attributes','history_before_fragment_component_index'):
                self.assertEqual(result[k],old[k])
            self.assertEqual(result['counts']['current_effective_whole_DN_known'],285);self.assertEqual(result['counts']['pure_horizontal_complete_DN_and_centerline'],248)
            self.assertEqual(result['counts']['rendered_component_instances'],2);self.assertEqual(result['pending_component_detail_differences'],[])
            self.assertEqual(result['history_before_received_fragment_detail']['previous_fragment_index'],old['fragment_component_index'])


if __name__=='__main__':unittest.main()
