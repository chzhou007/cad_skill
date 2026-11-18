import copy,unittest
from reapply_received_scope_attributes import candidate_prefix,check_values
from reviewed_uniform_subroute_DN import select
from test_reviewed_uniform_subroute_DN import fixture


class ReceivedScopeTests(unittest.TestCase):
    def test_one_unresolved_terminal_direction_does_not_change_full_range_or_original_guard(self):
        args=fixture();scope=args[0];routing=args[5];routing['V2']['segment_domains'][0]['direction_class']='undetermined'
        before=copy.deepcopy(args)
        with self.assertRaisesRegex(ValueError,'unresolved original axis direction'):select(*args)
        selected,evidence,held=candidate_prefix(scope,routing);private=[selected,*args[1:]];result=select(*private)
        self.assertEqual([r['axis_edge_id']for r in result['records']],['H'])
        self.assertEqual(selected['views']['iso']['route']['nodes'],['G','J','K','L'])
        self.assertEqual(evidence['excluded_axis_suffix'],['V2']);self.assertFalse(evidence['new_endpoint_correspondence_assigned'])
        self.assertEqual(held[0]['edge_id'],'V2');self.assertFalse(held[0]['direction_reclassified']);self.assertEqual(args,before)
        self.assertIsNone(result['records'][0]['per_axis_edge_length_allocation'])

    def test_prefix_stops_at_first_unknown_and_cannot_jump_to_later_known_edges(self):
        args=fixture();args[5]['H']['segment_domains'][0]['direction_class']='undetermined';selected,proof,held=candidate_prefix(args[0],args[5])
        self.assertEqual(selected['views']['iso']['route']['edges'],['HIGH','V'])
        self.assertEqual([r['edge_id']for r in held],['H','V2'])
        args[5]['V']['segment_domains'][0]['direction_class']='undetermined'
        with self.assertRaises(ValueError):candidate_prefix(args[0],args[5])

    def test_current_endpoint_geometry_and_previous_known_DN_are_still_blockers(self):
        args=fixture();rows=select(*args)['records'];axis=args[4];values={'H':{'diameter_nominal_mm':None}}
        check_values(rows,values,axis);self.assertIsNone(rows[0]['old_known_nominal_mm'])
        with self.assertRaisesRegex(ValueError,'known axis DN'):check_values(rows,{'H':{'diameter_nominal_mm':250}},axis)
        changed=copy.deepcopy(axis);changed['edges'][2]['end_node_id']='WRONG'
        with self.assertRaisesRegex(ValueError,'endpoints'):check_values(rows,values,changed)
        changed=copy.deepcopy(axis);changed['edges'][2]['attribute_paths'][0][1][0]+=1
        with self.assertRaisesRegex(ValueError,'geometry'):check_values(rows,values,changed)


if __name__=='__main__':unittest.main()
