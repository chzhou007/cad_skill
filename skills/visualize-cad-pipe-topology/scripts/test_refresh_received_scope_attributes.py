import copy,json,tempfile,unittest
from pathlib import Path
from refresh_received_scope_attributes import delta,provider_from,group_export


class ReceivedPublicationTests(unittest.TestCase):
    def fixture(self):
        records=[dict(axis_edge_id=e,nominal_mm=200,whole_horizontal_edge=whole,source_scope_id='S',plan_remaining_edges=['P'])for e,whole in[('D',True),('M',False)]]
        proof=dict(records=records,new_metric_records=[dict(axis_edges=['D','M','H'])],held_direction_edges=[dict(edge_id='H',direction_reclassified=False)])
        before=[dict(edge_id=e,values=dict(length=55,vertical='11',uniform_subroute_DN_domains_json='old',shared_plan_metric_scopes_json='old-source'))for e in('D','M','H','OTHER')]
        after=copy.deepcopy(before)
        for row in after:
            eid=row['edge_id'];v=row['values']
            if eid in('D','M'):
                record=records[0 if eid=='D'else 1];v.update(received_scope_uniform_DN_scope_id='S',received_scope_uniform_DN_domains_json=json.dumps(record),received_scope_uniform_DN_plan_source_sha256='a'*64)
            if eid=='D':v.update(diameter_nominal_mm=200,diameter_text='DN200',diameter_status='received')
            if eid in('D','M','H'):
                v.update(received_scope_metric_scope_ids='S',received_scope_metric_scopes_json=json.dumps([dict(per_axis_edge_length_allocation=None,aggregation_policy='count_once_per_scope_id_not_once_per_edge')]),received_scope_metric_source_sha256='a'*64)
            if eid=='H':v['received_scope_direction_hold_json']=json.dumps(proof['held_direction_edges'][0])
        return before,after,proof

    def test_only_new_whole_horizontal_DN_changes_old_primary_fields(self):
        before,after,proof=self.fixture();result=delta(before,after,proof);self.assertEqual(result['new_whole_horizontal_DN_edges'],['D'])
        for index,key,value in[(0,'length',0),(1,'diameter_nominal_mm',200),(2,'diameter_nominal_mm',200),(3,'length',1),(0,'uniform_subroute_DN_domains_json','lost'),(1,'vertical','plan'),(2,'received_scope_direction_hold_json','{}')]:
            bad=copy.deepcopy(after);bad[index]['values'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):delta(before,bad,proof)
        bad=copy.deepcopy(before);bad[0]['values']['diameter_nominal_mm']=250
        with self.assertRaises(ValueError):delta(bad,after,proof)

    def test_group_totals_are_not_allocated_and_export_contains_unique_scopes(self):
        before,after,proof=self.fixture();bad=copy.deepcopy(after);r=json.loads(bad[0]['values']['received_scope_metric_scopes_json']);r[0]['per_axis_edge_length_allocation']=0;bad[0]['values']['received_scope_metric_scopes_json']=json.dumps(r)
        with self.assertRaises(ValueError):delta(before,bad,proof)
        context=dict(reviewed_expression_group_metrics=dict(records=[dict(scope_id='OLD')]),received_scope_group_metrics=dict(records=[dict(scope_id='NEW')]))
        exported=group_export(context);self.assertEqual(len(exported['records']),2);self.assertIsNone(exported['per_axis_edge_length_allocation'])
        context['received_scope_group_metrics']['records'][0]['scope_id']='OLD'
        with self.assertRaises(ValueError):group_export(context)

    def test_current_frontier_records_DN_gain_without_fabricating_lengths_or_node_pairs(self):
        before,after,proof=self.fixture()
        prior=dict(counts=dict(pure_horizontal_complete_DN_and_centerline=1),remaining_horizontal_attributes=[dict(edge_id='D',known_whole_DN=None,complete_centerline=False,next_scope='unmapped',floor=2,attributes={},correspondence_observations=[])],current_horizontal_frontier={},records=[],member_domain_observations=[],ordinary_junction_mappings={'2':{'P':'A'}},current_component_inventory={'count':1578})
        with tempfile.TemporaryDirectory()as folder:
            p=Path(folder)/'proof';p.write_text('native',encoding='utf8');result=provider_from(prior,proof,after,p)
        row=result['remaining_horizontal_attributes'][0];self.assertEqual(row['known_whole_DN'],200);self.assertFalse(row['complete_centerline'])
        self.assertEqual(row['next_scope'],'reviewed_range_per_edge_length_allocation_unresolved')
        self.assertFalse(row['correspondence_observations'][0]['ordinary_endpoint_mapping_assigned'])
        for k in('records','member_domain_observations','ordinary_junction_mappings','current_component_inventory'):self.assertEqual(result[k],prior[k])


if __name__=='__main__':unittest.main()
