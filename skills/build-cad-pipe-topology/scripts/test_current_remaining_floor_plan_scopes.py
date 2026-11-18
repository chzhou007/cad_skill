import copy
import unittest

import ezdxf
from confirm_crossview_paths import encode
from current_remaining_floor_plan_scopes import MODE, partial_segment_evidence, check_result
from native_path_coverage_audit import audit
from native_segment_dn_candidates import collect as segment_DN


def state():
    rows = []
    for kind in ('equipment_branch', 'named_riser_floor_approach'):
        for system in ('supply', 'return'):
            key = kind+system
            rows.append(dict(mapping_id='CURRENT'+key, historical_mapping_id=key, kind=kind, system=system,
                plan_edges=['P'+key], iso_edges=['I'+key], diameter=dict(edge_id='P'+key, system=system, nominal_mm=300, lineage=[{}]),
                horizontal_projection=dict(value_mm=10, pieces=[{}], installed_whole_edge_length_mm=None, unshown_connection_length_mm=None),
                whole_axis_DN_selected=False, whole_axis_physical_length_mm=None, physical_ports_verified=False,
                equal_plan_axis_segment_extents_proved=False, human_confirmation_transferred=False, human_accepted=False))
    return dict(mode=MODE, status='current_context_and_named_plan_scopes_source_checked_not_fused', records=rows,
        local_graphs_mutated=False, physical_values_fused=False, whole_axis_DN_assigned=0, installed_lengths_assigned=0, human_accepted=False,
        axis_local_DN_candidates=dict(status='segment_candidates_not_accepted', graph_mutated=False, observations=[{}, {}]))


class CurrentRemainingScopeTests(unittest.TestCase):
    def fixture(self):
        doc = ezdxf.new(); model = doc.modelspace()
        line = model.add_line((0, 0), (10, 0), dxfattribs=dict(layer='空调冷冻水供水'))
        text = model.add_text('DN65', dxfattribs=dict(insert=(5, 1), height=1, layer='ANNOTATION'))
        graph = dict(nodes=[], edges=[dict(edge_id='E', system='supply', attribute_paths=[[[0, 0], [10, 0], [10, -5]]])])
        coverage = audit(doc, graph, dict(source_sha256='S', graph_sha256='G', edges=['E']), 'S', 'G')
        selection = dict(edge_id='E', segment_index=0, text_handle=text.dxf.handle, expected_text='DN65')
        return doc, graph, coverage, selection

    def test_native_modelspace_segment_candidate_does_not_accept_unshown_rest(self):
        import hashlib
        doc, graph, coverage, selected = self.fixture(); before = encode(graph)
        evidence = partial_segment_evidence(graph, coverage, [selected]); digest = hashlib.sha256(encode(evidence)).hexdigest()
        result = segment_DN(doc, graph, evidence, dict(source_sha256='S', graph_sha256='G', line_evidence_sha256=digest,
            text_layers=['ANNOTATION'], selections=[selected]), 'S', 'G', digest)
        self.assertEqual(result['observations'][0]['nominal_mm_candidate'], 65)
        self.assertFalse(evidence['complete_edge_source_coverage_claimed'])
        self.assertIsNone(evidence['edges'][0]['segments'][1]['source_handle'])
        self.assertEqual(result['status'], 'segment_candidates_not_accepted')
        self.assertEqual(encode(graph), before)

    def test_missing_selected_LINE_wrong_index_or_path_blocks_candidate(self):
        _, graph, coverage, selected = self.fixture()
        for mode in ('missing', 'index', 'path'):
            cov = copy.deepcopy(coverage); choice = copy.deepcopy(selected)
            if mode == 'missing': choice['segment_index'] = 1
            elif mode == 'index': choice['segment_index'] = 99
            else: cov['edges'][0]['segments'][0]['end'] = [99, 0]
            with self.subTest(mode=mode), self.assertRaises(ValueError): partial_segment_evidence(graph, cov, [choice])

    def test_source_four_values_keep_axis_extents_and_HIL_unknown(self):
        result = check_result(state())
        self.assertEqual(result['known_DN_scopes'], 4)
        self.assertEqual(result['native_axis_local_DN_candidates'], 2)
        self.assertFalse(result['hil_ready'])

    def test_duplicate_scope_wrong_service_or_promoted_axis_value_blocks(self):
        for mode in ('writer', 'system', 'whole', 'extent', 'approval', 'zero'):
            data = state()
            if mode == 'writer': data['records'][1]['iso_edges'] = data['records'][0]['iso_edges']
            elif mode == 'system': data['records'][0]['diameter']['system'] = 'return'
            elif mode == 'whole': data['records'][0]['whole_axis_DN_selected'] = True
            elif mode == 'extent': data['records'][0]['equal_plan_axis_segment_extents_proved'] = True
            elif mode == 'approval': data['records'][0]['human_confirmation_transferred'] = True
            else: data['records'][0]['horizontal_projection']['value_mm'] = 0
            with self.subTest(mode=mode), self.assertRaises(ValueError): check_result(data)


if __name__ == '__main__': unittest.main()
