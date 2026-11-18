import copy, unittest
from axis_attribute_source_routing import collect
from qualified_crossview_provider_inventory import inventory


def fixture():
    nodes = [dict(node_id=n, node_type='tee', system='supply', floor=3, x=i, y=0)
             for i, n in enumerate(('A', 'B', 'C'))]
    axis = dict(nodes=nodes, edges=[dict(edge_id='E', start_node_id='A', end_node_id='B',
        system='supply', floor_start=3, floor_end=3, attribute_paths=[[[0, 0], [1, 0]]])])
    plan = dict(nodes=[dict(n, node_id='P'+n['node_id']) for n in nodes],
        edges=[dict(axis['edges'][0], edge_id='PE', start_node_id='PA', end_node_id='PB')])
    batch = dict(floors={str(f):dict(junction_mapping={}, records=[]) for f in (1, 2, 3)})
    batch['floors']['3']['junction_mapping']={'PA':'A'}
    route = collect(axis, dict(isometric_horizontal_directions_degrees=[0, 45, 135], source_rule_evidence='expert'))
    frontier = dict(records=[dict(edge_id='E', next_scope='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path')])
    ext = dict(floor=2, current_junction_mapping={}, new_records=[])
    root=dict(human_accepted=False, source_bindings={'native_proof':'checked-by-owner'}, records=[dict(
        axis_edge_id='E', axis_attribute_paths=axis['edges'][0]['attribute_paths'], system='supply',
        floor=3, mapping_id='M', plan_edges=['PE'], plan_Ts=['PA','PB'], axis_Ts=['A','B'])])
    return [axis, dict(anchor_bounded_mains=root), batch, {'1':dict(nodes=[],edges=[]),
        '2':dict(nodes=[],edges=[]),'3':plan}, route, frontier, ext]


class Tests(unittest.TestCase):
    def test_inherit_later_native_anchors_and_do_not_rediscover_known_paths(self):
        args=fixture(); before=copy.deepcopy(args); r=inventory(*args)
        self.assertEqual(args,before)
        self.assertEqual(r['ordinary_junction_mappings']['3'],{'PA':'A','PB':'B'})
        self.assertEqual(r['counts']['corrected_false_unmapped_edges'],1)
        self.assertEqual(r['remaining_horizontal_attributes'][0]['next_scope'],'known_local_correspondence_incomplete_attributes')
        self.assertEqual(r['new_correspondences_assigned'],0)
        self.assertEqual(r['DN_or_length_values_assigned'],0)

    def test_native_order_is_used_instead_of_axis_edge_display_order(self):
        args=fixture(); args[0]['edges'][0].update(start_node_id='B',end_node_id='A')
        r=inventory(*args)
        self.assertEqual(r['ordinary_junction_mappings']['3']['PB'],'B')

    def test_member_namespace_is_preserved_and_never_becomes_local_anchor(self):
        args=fixture(); row=args[1].pop('anchor_bounded_mains')['records'][0]
        row.update(member_edge_id='MEMBER:scope:PE',anchors=[{'plan_T':'PA','axis_T':'C'}])
        args[1]['compound_member_mains']=dict(records=[row],source_bindings={'native':'proof'},human_accepted=False)
        r=inventory(*args)
        self.assertEqual(r['ordinary_junction_mappings']['3'],{'PA':'A'})
        self.assertEqual(r['counts']['member_domain_observations'],1)
        self.assertEqual(r['remaining_horizontal_attributes'][0]['next_scope'],'known_member_correspondence_incomplete_metric')

    def test_old_group_observations_cover_all_children_without_new_writers(self):
        args=fixture(); args[2]['floors']['3']['records']=[dict(mapping_id='CHAIN',plan_edges=['PE'],iso_edges=['E'])]
        r=inventory(*args)
        self.assertEqual(r['counts']['existing_correspondence_edges'],1)
        self.assertEqual(len(r['records'][0]['correspondence_observations']),2)

    def test_changed_geometry_conflicting_anchor_or_missing_bindings_fail(self):
        for case in ('geometry','anchor','bindings','floor','system','provider','member'):
            with self.subTest(case=case):
                args=fixture(); root=args[1]['anchor_bounded_mains']; row=root['records'][0]
                if case=='geometry':row['axis_attribute_paths']=[[[0,0],[2,0]]]
                elif case=='anchor':args[2]['floors']['3']['junction_mapping']={'PC':'B'}
                elif case=='bindings':root['source_bindings']={}
                elif case=='floor':args[3]['3']['nodes'][1]['floor']=2
                elif case=='system':row['system']='return'
                elif case=='provider':args[1]['unknown_provider']=copy.deepcopy(root)
                else:row['plan_Ts'][1]='MEMBER:scope:PB'
                with self.assertRaises(ValueError):inventory(*args)

    def test_vertical_routing_cannot_leak_into_plan_frontier(self):
        args=fixture(); args[0]['edges'][0]['attribute_paths']=[[[0,0],[0,1]]]
        args[4]=collect(args[0],dict(isometric_horizontal_directions_degrees=[0,45,135],source_rule_evidence='expert'))
        args[1]['anchor_bounded_mains']['records'][0]['axis_attribute_paths']=[[[0,0],[0,1]]]
        with self.assertRaises(ValueError):inventory(*args)
        args[5]['records']=[]
        r=inventory(*args)
        self.assertEqual(r['vertical_segments_routed_to_plan'],0)
        args[4]['records'][0]['DN_source_route']='corresponding_floor_plan_horizontal'
        with self.assertRaises(ValueError):inventory(*args)


if __name__=='__main__':unittest.main()
