import copy
import unittest
from test_match_named_riser_floor_paths import fixture as mapping_fixture
from match_named_riser_floor_paths import correspond, MODE as MAPPING_MODE
from named_riser_plan_attributes import topology_contract, named_annotation_domain, implementation_hashes
from native_named_riser_evidence import collect as collect_names
from pipe_annotation_attributes import source_texts
from checked_plan_DN_scope_attributes import attribute_checked_scope
from native_path_coverage_audit import audit as audit_native_paths


def fixture():
    args = list(mapping_fixture()); docs, graphs, inventory, names, riser, removed, policy, hashes = args
    for view in inventory['records'][0]['views'].values():
        for service in view['services'].values():
            service['ready_for_mapping_comparison'] = True
    for view in graphs:
        coverage = audit_native_paths(docs[view], graphs[view], dict(source_sha256=view, graph_sha256=view+'-graph',
            edges=[e['edge_id'] for e in graphs[view]['edges']]), view, view+'-graph')
        for edge, proof in zip(graphs[view]['edges'], coverage['edges']):
            edge['source_handles'] = sorted({w['source_handle'] for segment in proof['segments'] for w in segment['witnesses']})
    rows = copy.deepcopy(correspond(*args))
    mapping = dict(mode=MAPPING_MODE, local_graphs_mutated=False, physical_values_fused=False,
                   human_accepted=False, source_sha256={v: h['source_sha256'] for v, h in hashes.items()},
                   graph_sha256={v: h['graph_sha256'] for v, h in hashes.items()}, records=rows)
    doc, graph = docs['plan'], graphs['plan']; m = doc.modelspace(); specs = []
    for row, y in zip(rows, [0, 50]):
        node = next(n for n in graph['nodes'] if n['node_id'] == row['plan_riser_interface'])
        circle = next(c for c in m.query('CIRCLE') if c.dxf.center.y == y)
        node.update(system=row['system'], subtype='out_of_plane_riser', source_handle=circle.dxf.handle)
        t = m.add_text(row['identifier'] + ' DN450', dxfattribs=dict(insert=(-5, y+5), height=1, layer='ANNOTATION'))
        under = m.add_line((-6, y+4.8), (-1, y+4.8), dxfattribs=dict(layer='ANNOTATION'))
        leader = m.add_line((-1, y+4.8), (0, y), dxfattribs=dict(layer='ANNOTATION'))
        specs.append(dict(text_handle=t.dxf.handle, expected_text=t.plain_text(), underline_handle=under.dxf.handle,
                          leader_handle=leader.dxf.handle, target=dict(kind='plan_riser_circle', node_id=node['node_id'], circle_handle=circle.dxf.handle)))
    fresh = collect_names(doc, graph, dict(source_sha256='plan', graph_sha256='plan-graph',
        text_layers=['ANNOTATION'], leader_layers=['ANNOTATION'], selections=specs), 'plan', 'plan-graph')
    for row, name in zip(rows, fresh['records']):
        row['native_names']['plan'] = name
    return doc, graph, mapping


class NamedRiserPlanAttributesTests(unittest.TestCase):
    def test_native_through_main_and_equipment_branch_roles_are_read_only(self):
        doc, graph, mapping = fixture(); before = copy.deepcopy(graph)
        result = topology_contract(doc, graph, mapping, 'plan', 'plan-graph')
        self.assertEqual(set(result['main_edges']), {'supplyRIF', 'returnRIF'})
        self.assertEqual(set(result['branch_frontier_edges']), {'supplyEQ', 'returnEQ'})
        self.assertEqual(result['branches'], []); self.assertEqual(graph, before)

    def test_a_name_cannot_override_changed_main_service_path_or_floor(self):
        for case in ('branch_role', 'path', 'floor', 'service', 'review', 'unready'):
            doc, graph, mapping = fixture(); row = mapping['records'][0]
            if case == 'branch_role': row['paths']['plan']['independent_equipment_service']['trace']['edges'] = ['supplyMAIN']
            elif case == 'path': next(e for e in graph['edges'] if e['edge_id']=='supplyRIF')['attribute_paths'][0][0][0] += 1
            elif case == 'floor': row['floor'] = 3
            elif case == 'service': row['system'] = 'return'
            elif case == 'review': next(n for n in graph['nodes'] if n['node_id']=='supplyR')['review_required'] = True
            else: row['paths']['plan']['independent_equipment_service']['ready_for_mapping_comparison'] = False
            with self.subTest(case=case), self.assertRaises(ValueError):
                topology_contract(doc, graph, mapping, 'plan', 'plan-graph')

    def test_only_replayed_named_circle_annotations_leave_horizontal_DN_domain(self):
        doc, graph, mapping = fixture(); result = named_annotation_domain(doc, graph, mapping, 'plan', 'plan-graph')
        self.assertEqual(len(result['consumed_text_handles']), 2)
        self.assertEqual(len(result['consumed_stroke_handles']), 4)
        self.assertFalse(result['vertical_DN_selected'])
        handle = mapping['records'][0]['native_names']['plan']['leader']['handle']
        doc.entitydb[handle].dxf.end = (3, 0)
        with self.assertRaises(ValueError): named_annotation_domain(doc, graph, mapping, 'plan', 'plan-graph')

    def test_horizontal_DN_uses_its_own_scalar_marks_not_named_riser_DN450(self):
        doc, graph, mapping = fixture(); before = copy.deepcopy(graph)
        domain = named_annotation_domain(doc, graph, mapping, 'plan', 'plan-graph')
        contract = topology_contract(doc, graph, mapping, 'plan', 'plan-graph'); seeds = []
        for system, y in [('supply', 0), ('return', 50)]:
            text = doc.modelspace().add_text('DN300(3.200)', dxfattribs=dict(insert=(5, y+.8), height=1, layer='ANNOTATION'))
            line = next(e for e in doc.modelspace().query('LINE') if e.dxf.layer == ('空调冷冻水供水' if system=='supply' else '空调冷冻水回水') and e.dxf.start.x == 0 and e.dxf.start.y == y)
            seeds.append(dict(text_handle=text.dxf.handle, expected_text=text.plain_text(), edge_id=system+'RIF', source_line_handle=line.dxf.handle))
        texts = [t for t in source_texts(doc, 'plan', 'plan') if t['handle'] not in domain['consumed_text_handles']]
        result = attribute_checked_scope(doc, graph, dict(group_id='approaches', main_edges=contract['main_edges'], branches=[], seeds=seeds),
            texts, 'plan', 'plan-graph', set(), junctions=contract['junctions'], verified_taps=contract['verified_taps'],
            branch_frontier_edges=contract['branch_frontier_edges'], verified_nonpipe_annotation_strokes=domain['consumed_stroke_handles'])
        self.assertEqual([r['nominal_mm'] for r in result['records']], [300, 300])
        self.assertEqual({r['status'] for r in result['records']}, {'direct_plan_DN'})
        self.assertEqual(graph, before)

    def test_dependency_closure_includes_historical_DN_metric_and_named_mapping_rules(self):
        hashes = implementation_hashes()
        for name in ('match_named_riser_floor_paths.py', 'native_named_riser_evidence.py', 'checked_plan_DN_scope_attributes.py',
                     'diameter_tee_inheritance.py', 'native_plan_projection_lengths.py', 'source_checked_plan_path_coverage.py'):
            self.assertIn(name, hashes)


if __name__ == '__main__':
    unittest.main()
