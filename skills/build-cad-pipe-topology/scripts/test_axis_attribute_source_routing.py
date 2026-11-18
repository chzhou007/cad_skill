import copy,unittest
from axis_attribute_source_routing import collect
def fixture(points,floors=(3,3)):
    return dict(edges=[dict(edge_id='E',system='supply',floor_start=floors[0],floor_end=floors[1],attribute_paths=[points])]),dict(isometric_horizontal_directions_degrees=[0,45,135],source_rule_evidence='user_all_vertical_segments_use_axis_11_including_same_floor')
class Tests(unittest.TestCase):
    def test_same_floor_vertical_uses_axis_equally_with_interfloor_vertical(self):
        for floors in((3,3),(1,2)):
            args=fixture([[0,0],[0,1000]],floors);before=copy.deepcopy(args);r=collect(*args);self.assertEqual(r['edge_counts'],{'vertical_only':1});self.assertEqual(r['records'][0]['DN_source_route'],'axis_11_native_vertical');self.assertEqual(r['records'][0]['length_source_route'],'axis_11_native_vertical');self.assertEqual(args,before)
    def test_mixed_edge_is_split_for_attributes_and_never_collapsed_by_floor(self):
        r=collect(*fixture([[0,0],[100,0],[100,250],[200,350]]));self.assertEqual(r['edge_counts'],{'mixed_horizontal_vertical':1});self.assertEqual([x['DN_source_route']for x in r['records']],['corresponding_floor_plan_horizontal','axis_11_native_vertical','corresponding_floor_plan_horizontal']);self.assertTrue(all(x['physical_length_mm']is None and x['DN_assigned']is None for x in r['records']))
    def test_reversed_supply_return_direction_preserves_routing_and_ids(self):
        for system in('supply','return'):
            a=fixture([[0,0],[100,100],[100,200]]);a[0]['edges'][0]['system']=system;b=copy.deepcopy(a);b[0]['edges'][0]['attribute_paths'][0].reverse();self.assertEqual(collect(*a)['segment_counts'],collect(*b)['segment_counts']);self.assertTrue(all(x['edge_id']=='E'and x['system']==system for x in collect(*a)['records']))
    def test_unclassified_and_zero_spans_are_kept_without_forced_correspondence(self):
        r=collect(*fixture([[0,0],[2,1],[2,1]]));self.assertEqual(r['edge_counts'],{'unresolved_direction_or_path':1});self.assertEqual(r['segment_counts'],{'undetermined':1,'degenerate':1});self.assertTrue(all(x['DN_source_route']=='original_source_direction_review'for x in r['records']))
    def test_bad_policy_duplicate_ids_and_nonfinite_coordinates_fail(self):
        args=fixture([[0,0],[10,0]]);args[1]['isometric_horizontal_directions_degrees'].append(90)
        with self.assertRaises(ValueError):collect(*args)
        args=fixture([[0,0],[10,0]]);args[0]['edges']*=2
        with self.assertRaises(ValueError):collect(*args)
        with self.assertRaises(ValueError):collect(*fixture([[0,0],[float('nan'),1]]))
if __name__=='__main__':unittest.main()
