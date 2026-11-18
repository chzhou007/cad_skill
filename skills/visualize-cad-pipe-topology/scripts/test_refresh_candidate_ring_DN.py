import copy,json,tempfile,unittest
from pathlib import Path
from refresh_candidate_ring_DN import delta,provider_from,encode_manifest,current_parent_provider,sha


class CandidatePublicationTests(unittest.TestCase):
    def test_manifest_keeps_existing_evidence_key_order_for_exact_CSV_cells(self):
        prior={'context':{'source_last':'中文','source_first':{'z':3,'a':1}}}
        encoded=json.loads(encode_manifest(prior))
        self.assertEqual(json.dumps(encoded,ensure_ascii=False),json.dumps(prior,ensure_ascii=False))
        self.assertEqual(list(encoded['context']['source_first']),['z','a'])

    def fixture(self):
        row=dict(axis_edge_id='E',mapping_id='M',nominal_mm=250,whole_axis_nominal_mm=250)
        before=[dict(edge_id='E',values=dict(diameter_nominal_mm='',length=5000,vertical='11',reviewed_partition_mapping_id='old-source')),
                dict(edge_id='OTHER',values=dict(diameter_nominal_mm=300,length=4000))]
        after=copy.deepcopy(before);after[0]['values'].update(diameter_nominal_mm=250,diameter_text='DN250',diameter_status='reviewed',
            candidate_ring_partition_plan_nominal_mm=250,candidate_ring_partition_mapping_id='M',
            candidate_ring_partition_whole_axis_nominal_mm=250,candidate_ring_partition_evidence_json=json.dumps(row))
        return row,before,after

    def test_original_delta_kernel_preserves_all_old_values_and_partition_fields(self):
        row,before,after=self.fixture();self.assertEqual(delta(before,after,[row])['new_whole_horizontal_DN_edges'],['E'])
        for i,k,v in [(0,'length',0),(0,'vertical','plan'),(0,'reviewed_partition_mapping_id','overwritten'),(1,'length',5)]:
            bad=copy.deepcopy(after);bad[i]['values'][k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):delta(before,bad,[row])
        known=copy.deepcopy(before);known[0]['values']['diameter_nominal_mm']=300
        with self.assertRaises(ValueError):delta(known,after,[row])

    def test_old_reviewed_observations_survive_the_new_completion_layer(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'provider.json';old=dict(mode='prior',remaining_horizontal_attributes=[
                dict(edge_id='E',known_whole_DN=None,complete_centerline=True,floor=3,next_scope='DN_conflict')],
                records=[],member_domain_observations=[],ordinary_junction_mappings={},current_component_inventory={},
                reviewed_partition_DN_observations=[dict(axis_edge_id='OLD')],new_reviewed_partition_complete_axis_edges=['OLD'],
                history_before_reviewed_partition_DN=dict(mode='original-history'),
                counts=dict(pure_horizontal_complete_DN_and_centerline=238,pure_horizontal_complete_centerline=248),current_horizontal_frontier={})
            p.write_text(json.dumps(old),encoding='utf8');proof=dict(inputs=dict(provider=dict(path=str(p))),records=[dict(axis_edge_id='E',nominal_mm=250,whole_axis_nominal_mm=250)])
            output=provider_from(proof,[dict(edge_id='E',values=dict(diameter_nominal_mm=250))])
            for key in ('reviewed_partition_DN_observations','new_reviewed_partition_complete_axis_edges','history_before_reviewed_partition_DN'):
                self.assertEqual(output[key],old[key])
            self.assertEqual(output['candidate_ring_completion_edges'],['E'])
            self.assertEqual(output['counts']['pure_horizontal_complete_DN_and_centerline'],239)

    def test_actual_parent_component_receipt_is_inherited_instead_of_map_basis(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'public/data').mkdir(parents=True);(root/'effective-provider-refresh').mkdir()
            current=dict(mode='actual',ordinary_junction_mappings={},remaining_horizontal_attributes=[dict(edge_id='E',known_whole_DN=None,complete_centerline=True,floor=3,next_scope='conflict')],
                records=[],member_domain_observations=[],current_component_inventory={'instances':['kept1','kept2']},current_horizontal_frontier={},
                counts=dict(rendered_component_instances=2,pure_horizontal_complete_DN_and_centerline=238,pure_horizontal_complete_centerline=248))
            path=root/'effective-provider-refresh/provider-inventory.json';path.write_text(json.dumps(current),encoding='utf8')
            (root/'public/data/manifest.json').write_text(json.dumps(dict(bundleId='B',effectiveProviderRefresh=dict(mode='actual_effective_member_DN_and_provider_refresh_v1'))),encoding='utf8')
            (root/'public/data/graph.json').write_text(json.dumps(dict(instances=[{},{}])),encoding='utf8')
            (root/'effective-provider-refresh.json').write_text(json.dumps(dict(bundle_id='B',output_hashes={'effective-provider-refresh/provider-inventory.json':sha(path)})),encoding='utf8')
            spec=current_parent_provider(root)
            basis=copy.deepcopy(current);basis['counts']['rendered_component_instances']=1;basis['current_component_inventory']={'instances':['kept1']}
            bp=root/'basis.json';bp.write_text(json.dumps(basis),encoding='utf8')
            proof=dict(inputs=dict(provider=dict(path=str(bp))),records=[dict(axis_edge_id='E',nominal_mm=250,whole_axis_nominal_mm=250)])
            result=provider_from(proof,[dict(edge_id='E',values=dict(diameter_nominal_mm=250))],spec)
            self.assertEqual(result['current_component_inventory'],current['current_component_inventory'])
            self.assertEqual(result['counts']['rendered_component_instances'],2)
            (root/'public/data/graph.json').write_text(json.dumps(dict(instances=[{}])),encoding='utf8')
            with self.assertRaises(ValueError):current_parent_provider(root)


if __name__=='__main__':unittest.main()
