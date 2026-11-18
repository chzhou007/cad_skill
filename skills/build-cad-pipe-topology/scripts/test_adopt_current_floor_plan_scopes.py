import copy
import unittest

from confirm_crossview_paths import encode
from adopt_current_floor_plan_scopes import adopt, ROOT, FIELD


class CurrentFloorAdoptionTests(unittest.TestCase):
    def fixture(self):
        rows, edges = [], []
        for i in range(3):
            eid, pe = 'I'+str(i), 'P'+str(i)
            metric = dict(value_mm=None if i == 2 else 10, pieces=[dict(plan_edge=pe, points=[[0, 0], [10, 0]])])
            old = dict(mapping_id='OLD'+str(i), floor=2, system='supply', plan_edges=[pe], iso_edges=[eid],
                source_hashes=dict(plan='SOURCE', isometric='AXISSOURCE', plan_graph='OLDPLAN', local_iso_graph='AXIS'),
                diameter=dict(plan_candidate=dict(nominal_mm=300), axis_observation=dict(nominal_mm=65)), horizontal_projection=copy.deepcopy(metric), human_accepted=False)
            edges.append(dict(edge_id=eid, system='supply', attribute_paths=[[[0, 0], [10, 0]]], cross_view_attributes=old, component_inventory=['KEEP']))
            rows.append(dict(mapping_id='NEW'+str(i), kind='equipment_branch', floor=2, system='supply', plan_edges=[pe], iso_edges=[eid],
                diameter=dict(edge_id=pe, system='supply', nominal_mm=300, human_accepted=False), horizontal_projection=metric))
        parent = dict(nodes=[dict(node_id='KEEP')], edges=edges, metadata=dict(hil_ready=False), source_history=dict(preserve=True))
        stages = {str(i): dict(graph_sha256=dict(plan='NEWPLAN', iso='AXIS'), source_sha256=dict(plan='SOURCE', iso='AXISSOURCE'),
            records=[row], physical_values_fused=False, human_accepted=False) for i, row in enumerate(rows)}
        evidence = {str(i): dict(path='SCOPE'+str(i), sha256=str(i)*64) for i in range(3)}
        return parent, stages, evidence

    def test_all_history_geometry_components_and_unknown_values_survive(self):
        parent, stages, evidence = self.fixture(); before = encode(parent)
        graph, stage = adopt(parent, stages, evidence, 2, 'PARENT')
        self.assertEqual(encode(parent), before)
        self.assertEqual(stage['source_checked_plan_scopes'], 3)
        self.assertEqual(stage['unmeasured_detail_scopes'], 1)
        for old, new in zip(parent['edges'], graph['edges']):
            self.assertEqual({k: v for k, v in new.items() if k != FIELD}, old)
            self.assertEqual(new[FIELD]['historical_attributes'], old['cross_view_attributes'])
            self.assertFalse(new[FIELD]['related_HIL_confirmation_inherited'])
            self.assertIsNone(new[FIELD]['whole_axis_physical_length_mm'])

    def test_missing_repeated_or_different_floor_scope_blocks_full_adoption(self):
        for mode in ('missing', 'duplicate', 'floor', 'graph', 'source'):
            parent, stages, evidence = self.fixture()
            if mode == 'missing': stages.pop('2')
            elif mode == 'duplicate': stages['1']['records'] = copy.deepcopy(stages['0']['records'])
            elif mode == 'floor': stages['1']['records'][0]['floor'] = 3
            elif mode == 'graph': stages['1']['graph_sha256']['plan'] = 'OTHER'
            else: stages['1']['source_sha256']['plan'] = 'OTHER'
            with self.subTest(mode=mode), self.assertRaises(ValueError): adopt(parent, stages, evidence, 2, 'PARENT')

    def test_changed_values_and_metric_geometry_need_explicit_reconciliation(self):
        for mode in ('DN', 'length', 'pieces', 'approval'):
            parent, stages, evidence = self.fixture()
            row = stages['0']['records'][0]
            if mode == 'DN': row['diameter']['nominal_mm'] = 200
            elif mode == 'length': row['horizontal_projection']['value_mm'] = 20
            elif mode == 'pieces': row['horizontal_projection']['pieces'][0]['points'][1] = [20, 0]
            else: parent['edges'][0]['cross_view_attributes']['human_accepted'] = True
            with self.subTest(mode=mode), self.assertRaises(ValueError): adopt(parent, stages, evidence, 2, 'PARENT')


if __name__ == '__main__': unittest.main()
