import copy,unittest
from cycle_carrier_guards import reconcile

class Tests(unittest.TestCase):
    def fixture(self):
        records=[dict(axis_edge_id='A',mapping_id='M',plan_edge_id='P',floor=2,system='supply',complete_horizontal_centerline_mm=10),dict(axis_edge_id='B',mapping_id='N',plan_edge_id='Q',floor=2,system='supply',complete_horizontal_centerline_mm=20)]
        proposals=dict(floors={'2':dict(new_junction_mapping={'p':'a'},discovery=dict(bounded_routes=[dict(plan=dict(nodes=['p','remote'],edges=['OTHER']))]))})
        risks=dict(corridors=[dict(source_LINE='L',edges=[dict(edge_id='P')],declarations=[dict(handle='D',members=[dict(nominal_mm=300),dict(nominal_mm=200)])])])
        plan=dict(edges=[dict(edge_id='P',start_node_id='old',end_node_id='p')]);return dict(records=records),proposals,risks,plan
    def test_existing_carrier_barrier_holds_metric_and_incident_riser_even_outside_long_arc(self):
        args=self.fixture();before=copy.deepcopy(args);r=reconcile(*args)
        self.assertEqual(r['held_cycle_lengths'],1);self.assertEqual(r['held_riser_roles'],1);self.assertEqual(r['unblocked_metric_mapping_ids'],['N'])
        self.assertEqual(r['records'][0]['drawing_carrier_projection_mm'],10);self.assertIsNone(r['records'][0]['complete_physical_horizontal_length_mm']);self.assertFalse(r['records'][0]['source_annotation_ownership_inferred']);self.assertEqual(args,before)
    def test_no_candidate_barrier_does_not_retract_other_values(self):
        a=self.fixture();a[2]['corridors']=[];r=reconcile(*a);self.assertEqual(r['held_cycle_lengths'],0);self.assertEqual(r['held_riser_roles'],0)
    def test_duplicate_target_is_not_silently_counted(self):
        a=self.fixture();a[0]['records'].append(copy.deepcopy(a[0]['records'][0]))
        with self.assertRaises(ValueError):reconcile(*a)
if __name__=='__main__':unittest.main()
