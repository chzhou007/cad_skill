import copy,unittest
from complementary_plan_attribute_application import adopt_provider,qualify_row

class Adoption(unittest.TestCase):
    def fixture(self):
        remaining=[dict(edge_id=e,floor=3,complete_centerline=False,known_whole_DN=None,attributes={})for e in('A','B')]
        original=dict(remaining_horizontal_attributes=remaining,records=[dict(edge_id='OLD')],member_domain_observations=[dict(keep=True)],ordinary_junction_mappings={'3':{}},current_component_inventory={'count':1574},counts={},
            current_horizontal_frontier=dict(pure_horizontal_complete=1,pure_horizontal_complete_centerline=1,records=copy.deepcopy(remaining)))
        rows=[dict(axis_edge_id=e,source_scope_id=e,complete_horizontal_centerline_mm=1000,nominal_mm=150 if e=='A'else None,DN_status='direct_plan_DN'if e=='A'else'conflict')for e in('A','B')]
        effective=[dict(edge_id=r['axis_edge_id'],values=dict(complementary_mapping_id=r['source_scope_id'],complementary_plan_centerline_mm=1000,complementary_plan_DN_mm=150 if r['axis_edge_id']=='A'else'',diameter_nominal_mm=150 if r['axis_edge_id']=='A'else''))for r in rows]
        return original,dict(records=rows),effective
    def test_adopt_only_actual_values_keep_DN_conflict_and_topology_exact(self):
        old,proof,effective=self.fixture();before=copy.deepcopy(old);new=adopt_provider(old,proof,effective)
        self.assertEqual(old,before);self.assertEqual(new['records'],old['records']);self.assertEqual(new['current_component_inventory'],old['current_component_inventory'])
        self.assertEqual(new['current_horizontal_frontier']['pure_horizontal_complete'],2);self.assertEqual(new['current_horizontal_frontier']['pure_horizontal_complete_centerline'],3)
        self.assertEqual(len(new['remaining_horizontal_attributes']),1);self.assertIsNone(new['remaining_horizontal_attributes'][0]['known_whole_DN'])
    def test_missing_reader_adoption_or_old_known_value_is_not_promoted(self):
        for mutate in(lambda o,p,e:e[0]['values'].update(complementary_plan_centerline_mm=0),lambda o,p,e:o['remaining_horizontal_attributes'][0].update(known_whole_DN=200)):
            args=self.fixture();mutate(*args)
            with self.assertRaises(ValueError):adopt_provider(*args)
    def test_unrecovered_native_component_difference_stops_attribute_owner(self):
        row=dict(kind='native_complementary_anchored_chain_topology',attribute_adoption_allowed=False,source_detail_difference=True,physical_values_assigned=0)
        with self.assertRaisesRegex(ValueError,'not attribute-qualified'):qualify_row(row,None,None,None,None,None,None,None)

if __name__=='__main__':unittest.main()
