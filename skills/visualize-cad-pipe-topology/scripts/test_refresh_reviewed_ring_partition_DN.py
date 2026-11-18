import copy,json,tempfile,unittest
from pathlib import Path
from refresh_reviewed_ring_partition_DN import delta,effective,provider_from


class Tests(unittest.TestCase):
    def test_actual_app_facade_wins_over_retained_legacy_files(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);(root/'public/data').mkdir(parents=True)
            (root/'package.json').write_text('{"type":"module"}',encoding='utf-8')
            (root/'public/app.js').write_text("import {crossViewAttributeCsvValues}from './edge-attributes-current.js';",encoding='utf-8')
            for name,value in [('edge-attributes-current.js',300),('edge-attributes-plan-crossover.js',200)]:
                (root/'public'/name).write_text('export function crossViewAttributeCsvValues(){return {DN:'+str(value)+'}}',encoding='utf-8')
            (root/'public/data/graph.json').write_text('{"edges":[{"edge_id":"E"}]}',encoding='utf-8')
            (root/'public/data/manifest.json').write_text('{"attributeValueContext":{}}',encoding='utf-8')
            self.assertEqual(effective(root)[0]['values']['DN'],300)
            (root/'public/app.js').write_text("import {x}from './edge-attributes-current.js';import{y}from './edge-attributes-plan-crossover.js';",encoding='utf-8')
            with self.assertRaises(ValueError):effective(root)

    def fixture(self):
        row=dict(axis_edge_id='E',mapping_id='M',nominal_mm=200,whole_axis_nominal_mm=200)
        before=[dict(edge_id='E',values=dict(diameter_nominal_mm='',diameter_status='current_plan_DN_conflict',length=5300,vertical='original')),
                dict(edge_id='OTHER',values=dict(diameter_nominal_mm=300))]
        after=copy.deepcopy(before);after[0]['values'].update(diameter_nominal_mm=200,diameter_text='DN200',diameter_status='reviewed',
            reviewed_partition_plan_nominal_mm=200,reviewed_partition_mapping_id='M',reviewed_partition_whole_axis_nominal_mm=200,
            reviewed_partition_evidence_json=json.dumps(row))
        return row,before,after

    def test_only_resolved_unknown_DN_status_changes_all_lengths_and_other_scopes_stay_exact(self):
        row,before,after=self.fixture();self.assertEqual(delta(before,after,[row])['new_whole_horizontal_DN_edges'],['E'])
        for index,key,value in [(0,'length',6000),(0,'vertical','changed'),(1,'diameter_nominal_mm',200)]:
            bad=copy.deepcopy(after);bad[index]['values'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):delta(before,bad,[row])
        known=copy.deepcopy(before);known[0]['values']['diameter_nominal_mm']=250
        with self.assertRaises(ValueError):delta(known,after,[row])

    def test_known_DN_with_unknown_length_cannot_be_called_complete(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);row=dict(edge_id='E',known_whole_DN=None,complete_centerline=True,floor=2,next_scope='DN_conflict')
            old=dict(mode='parent',remaining_horizontal_attributes=[row],records=[],member_domain_observations=[],ordinary_junction_mappings={},current_component_inventory={},
                counts=dict(pure_horizontal_complete_DN_and_centerline=230,pure_horizontal_complete_centerline=248),current_horizontal_frontier={})
            path=root/'provider.json';path.write_text(json.dumps(old),encoding='utf-8')
            proof=dict(inputs=dict(provider=dict(path=str(path))),records=[dict(axis_edge_id='E',nominal_mm=200,whole_axis_nominal_mm=200)])
            actual=[dict(edge_id='E',values=dict(diameter_nominal_mm=200))]
            result=provider_from(proof,actual);self.assertEqual(result['counts']['pure_horizontal_complete_DN_and_centerline'],231)
            self.assertEqual(result['current_horizontal_frontier']['pure_horizontal_complete_centerline'],248)
            old['remaining_horizontal_attributes'][0]['complete_centerline']=False;path.write_text(json.dumps(old),encoding='utf-8')
            with self.assertRaises(ValueError):provider_from(proof,actual)


if __name__=='__main__':unittest.main()
