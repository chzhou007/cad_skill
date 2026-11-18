import copy,unittest
import test_native_paired_junction_correspondence as fixtures
from native_paired_junction_correspondence import collect
from refine_paired_service_path_correspondence import refine,MODE
from match_source_checked_crossview_paths import selected_snapshot


class JunctionPathRefinementTests(unittest.TestCase):
    def data(self):
        docs,graphs,mapping,hashes=fixtures.fixture();records=[]
        for pair in mapping['evidence']['paired_services']:
            for system,state in pair['services'].items():
                for did in pair['equipment_ids']:
                    row=dict(mapping_id=f'R{len(records)+1}',kind='equipment_branch',equipment_id=did,system=system,floor=2,human_accepted=False)
                    for view in graphs:row.update({view+'_edges':state['branches'][view][did],view+'_snapshot':selected_snapshot(graphs[view],state['branches'][view][did])})
                    records.append(row)
                row=dict(mapping_id=f'R{len(records)+1}',kind='main_between_equipment_branches',endpoint_equipment_ids=pair['equipment_ids'],system=system,floor=2,human_accepted=False)
                for view in graphs:row.update({view+'_edges':state['routes'][view]['edges'],view+'_snapshot':selected_snapshot(graphs[view],state['routes'][view]['edges'])})
                records.append(row)
        mapping.update(records=records,expert_confirmation_claimed=False,hil_ready=False)
        proof=collect(docs,graphs,mapping,hashes);required=[dict(parent_pair_id='P01',system=s) for s in ('supply','return')]
        return mapping,proof,graphs,required
    def test_existing_Ts_split_correspondence_and_add_only_source_verified_links(self):
        args=self.data();before=copy.deepcopy(args);out=refine(*args)
        self.assertEqual(args,before);self.assertEqual(out['mode'],MODE);self.assertEqual(len(out['records']),16);self.assertEqual(len(out['superseded_path_records']),2)
        rows=[r for r in out['records'] if r.get('derived_from_mapping_id')];self.assertEqual(len(rows),4)
        self.assertTrue(all(len(r['plan_edges'])==len(r['iso_edges'])==1 for r in rows))
        self.assertTrue(all(r['kind']=='main_between_matched_junctions' and 'endpoint_equipment_ids' not in r for r in rows))
        self.assertEqual(len([r for r in out['records'] if r['mapping_id'].startswith('LINK-')]),2)
        self.assertFalse(out['local_graphs_mutated']);self.assertFalse(out['physical_values_fused']);self.assertFalse(out['human_accepted'])
    def test_other_source_checked_records_and_retired_scope_are_preserved_exactly(self):
        args=self.data();old=args[0];out=refine(*args);by={r['mapping_id']:r for r in out['records']};retired={r['mapping_id'] for r in out['superseded_path_records']}
        for row in old['records']:
            if row['mapping_id'] not in retired:self.assertEqual(by[row['mapping_id']],row)
            else:self.assertIn(row,out['superseded_path_records'])
    def test_incomplete_duplicate_or_false_interior_match_never_allocates_by_position(self):
        for mode in ('incomplete','duplicate_group','duplicate_match','wrong_node','wrong_route'):
            args=self.data();mapping,proof,graphs,required=args
            if mode=='incomplete':proof['records'][0]['complete']=False
            elif mode=='duplicate_group':required.append(copy.deepcopy(required[0]))
            elif mode=='duplicate_match':proof['records'][0]['matches'].append(copy.deepcopy(proof['records'][0]['matches'][0]))
            elif mode=='wrong_node':proof['records'][0]['matches'][0]['views']['iso']['parent_node']='supply0'
            else:next(r for r in mapping['records'] if r['kind']=='main_between_equipment_branches')['plan_edges']=[]
            with self.assertRaises(ValueError):refine(*args)
    def test_duplicate_edge_claim_is_a_blocker_even_with_matching_total_counts(self):
        args=self.data();args[0]['records'].append(copy.deepcopy(args[0]['records'][0]));args[0]['records'][-1]['mapping_id']='OTHER'
        with self.assertRaisesRegex(ValueError,'overlaps'):refine(*args)


if __name__=='__main__':unittest.main()
