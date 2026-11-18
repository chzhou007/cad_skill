import copy
from pathlib import Path
import tempfile
import unittest

from test_match_inherited_circle_crossview_paths import fixture
from batch_apply_crossview_rules import discover_floor,evaluate_all_axis_edges,rebase_axis_inventory


class Tests(unittest.TestCase):
    def test_all_ready_native_branches_and_mains_are_discovered_in_one_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,graphs,inventory,*_=fixture(Path(tmp));before=copy.deepcopy(graphs)
            out=discover_floor(graphs,inventory,3)
            self.assertEqual(len(out['records']),10)
            self.assertEqual(sum(r['kind']=='equipment_branch' for r in out['records']),6)
            self.assertIsNotNone(out['full_floor_structure']);self.assertEqual(graphs,before)

    def test_unready_service_becomes_exception_without_aborting_other_equipment(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,graphs,inventory,*_=fixture(Path(tmp))
            inventory['records'][0]['views']['plan']['services']['supply']['ready_for_mapping_comparison']=False
            inventory['records'][0]['ready_for_mapping_comparison']=False
            out=discover_floor(graphs,inventory,3)
            self.assertTrue(any(r['reason']=='local_service_not_proven' for r in out['unresolved']))
            self.assertEqual(sum(r['kind']=='equipment_branch' for r in out['records']),5)

    def test_changed_native_inventory_trace_is_not_silently_rematched(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,graphs,inventory,*_=fixture(Path(tmp))
            inventory['records'][0]['views']['plan']['services']['supply']['trace']['tee']='wrong'
            with self.assertRaisesRegex(ValueError,'route changed'):discover_floor(graphs,inventory,3)

    def test_axis_batch_contains_every_edge_including_unmatched_and_no_values_are_fabricated(self):
        axis=dict(edges=[dict(edge_id='E1',system='supply',floor_start=1,floor_end=1),
            dict(edge_id='E2',system='return',floor_start=1,floor_end=2)])
        out=evaluate_all_axis_edges(axis,{},dict(edges=[]))
        self.assertEqual(out['total_edges'],2);self.assertEqual(len(out['records']),2)
        self.assertEqual(out['records'][1]['state'],'axis_vertical_or_mixed_scope_requires_segment_rule')
        self.assertTrue(all(r['physical_length_mm'] is None for r in out['records']))

    def test_identity_rebase_rejects_geometry_change(self):
        g=dict(edges=[dict(edge_id='E',system='supply',attribute_paths=[[[0,0],[1,0]]])])
        changed=copy.deepcopy(g);changed['edges'][0]['attribute_paths'][0][-1][0]=2
        with self.assertRaisesRegex(ValueError,'geometry changed'):
            rebase_axis_inventory(dict(records=[]),g,changed,dict(aliases={}))


if __name__=='__main__':unittest.main()
