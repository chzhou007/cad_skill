import copy
import math
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from reviewed_main_DN_boundaries import resolve, compute, verify_attribute_report, sha


def fixture(angle=0, mirror=False, longer_north=False):
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    def point(x, y):
        if mirror:
            x = -x
        return [c*x-s*y, s*x+c*y]
    coords = dict(TB=(0, 0), TA=(0, -10), N=(0, 20), S=(0, -20), BB=(10, 0), BA=(10, -10))
    specs = [('N', 'TB', 'N'), ('M', 'TA', 'TB'), ('S', 'TA', 'S'), ('BB', 'TB', 'BB'), ('BA', 'TA', 'BA')]
    if longer_north:
        coords.update(TC=(0, 10), BC=(10, 10))
        specs[0] = ('N', 'TC', 'N')
        specs += [('U', 'TB', 'TC'), ('BC', 'TC', 'BC')]
    nodes = [dict(node_id=n, node_type='tee' if n.startswith('T') else 'virtual_equipment',
        x=point(*xy)[0], y=point(*xy)[1], floor=1) for n, xy in coords.items()]
    edges = [dict(edge_id=e, start_node_id=a, end_node_id=b, system='supply',
        attribute_paths=[[point(*coords[a]), point(*coords[b])]]) for e, a, b in specs]
    proofs = {}
    for nid in coords:
        if not nid.startswith('T'):
            continue
        rays = []
        for edge in edges:
            if nid in (edge['start_node_id'], edge['end_node_id']):
                other = edge['end_node_id'] if edge['start_node_id'] == nid else edge['start_node_id']
                a, b = point(*coords[nid]), point(*coords[other])
                rays.append(dict(edge_id=edge['edge_id'], direction=[b[0]-a[0], b[1]-a[1]]))
        proofs[nid] = dict(source_sha256='S', graph_sha256='G', graph_mutated=False,
            junctions=[dict(node_id=nid, position=point(*coords[nid]), source_rays=rays)])
    seeds = [dict(edge_id=eid, nominal_mm=value, evidence_id='source:' + eid)
             for eid, value in [('N', 200), ('S', 450), ('BA', 100), ('BB', 80)]]
    return dict(nodes=nodes, edges=edges), seeds, {e['edge_id'] for e in edges}, proofs


class Tests(unittest.TestCase):
    def test_original_question_pins_report_then_exact_attribute_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / 'attributes.json'
            payload.write_text('{}', encoding='utf8')
            report = Path(tmp) / 'verification.json'
            report.write_text(json.dumps(dict(attribute_sha256=sha(payload), attribute_run=tmp)), encoding='utf8')
            paths = dict(attributes=payload, attribute_verification=report)
            evidence = dict(current_native_attribute_report_sha256=sha(report))
            verify_attribute_report(paths, evidence)
            payload.write_text('{"changed":true}', encoding='utf8')
            with self.assertRaisesRegex(ValueError, 'report or its payload differs'):
                verify_attribute_report(paths, evidence)

    def test_payload_hash_cannot_substitute_for_reviewed_verification_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / 'attributes.json'
            payload.write_text('{}', encoding='utf8')
            report = Path(tmp) / 'verification.json'
            report.write_text(json.dumps(dict(attribute_sha256=sha(payload), attribute_run=tmp)), encoding='utf8')
            with self.assertRaisesRegex(ValueError, 'report or its payload differs'):
                verify_attribute_report(dict(attributes=payload, attribute_verification=report),
                    dict(current_native_attribute_report_sha256=sha(payload)))

    def test_reviewed_extent_resolves_only_target_preserves_native_DN200_and_branches(self):
        graph, seeds, scope, proofs = fixture()
        original = copy.deepcopy((graph, seeds, proofs))
        before, after = resolve(graph, seeds, scope, proofs, 'S', 'G', {'M': 450}, 'Q')
        old, new = [{r['edge_id']: r for r in value['records']} for value in (before, after)]
        self.assertEqual(old['M']['status'], 'conflict')
        self.assertEqual(new['M']['nominal_mm'], 450)
        self.assertEqual(new['M']['status'], 'explicit_reviewed_plan_DN_extent')
        self.assertEqual(new['N']['nominal_mm'], 200)
        self.assertEqual(new['BA']['nominal_mm'], 100)
        self.assertEqual(new['BB']['nominal_mm'], 80)
        self.assertEqual({k: v for k, v in old.items() if k != 'M'}, {k: v for k, v in new.items() if k != 'M'})
        self.assertEqual((graph, seeds, proofs), original)
        self.assertIsNone(new['M']['reviewed_DN_extent']['physical_reducer_position'])

    def test_rotation_and_mirror_do_not_change_reviewed_source_extent(self):
        for angle, mirror in [(0, False), (90, False), (180, True), (270, True)]:
            graph, seeds, scope, proofs = fixture(angle, mirror)
            with self.subTest(angle=angle, mirror=mirror):
                _, after = resolve(graph, seeds, scope, proofs, 'S', 'G', {'M': 450}, 'Q')
                self.assertEqual(next(r for r in after['records'] if r['edge_id'] == 'M')['nominal_mm'], 450)

    def test_new_review_cannot_overwrite_a_native_direct_label(self):
        graph, seeds, scope, proofs = fixture()
        with self.assertRaisesRegex(ValueError, 'bound an inherited conflict'):
            resolve(graph, seeds, scope, proofs, 'S', 'G', {'N': 450}, 'Q')

    def test_unobserved_value_and_boolean_cannot_become_pipe_DN(self):
        for value in (999, True):
            graph, seeds, scope, proofs = fixture()
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve(graph, seeds, scope, proofs, 'S', 'G', {'M': value}, 'Q')

    def test_scope_ends_require_both_independently_checked_Ts(self):
        graph, seeds, scope, proofs = fixture()
        del proofs['TB']
        with self.assertRaisesRegex(ValueError, 'bound an inherited conflict'):
            resolve(graph, seeds, scope, proofs, 'S', 'G', {'M': 450}, 'Q')

    def test_review_does_not_silently_extend_to_unreviewed_next_pipe(self):
        graph, seeds, scope, proofs = fixture(longer_north=True)
        with self.assertRaisesRegex(ValueError, 'unreviewed pipe scope'):
            resolve(graph, seeds, scope, proofs, 'S', 'G', {'M': 450}, 'Q')

    def test_partial_expert_answer_is_not_expanded_to_a_complete_scope(self):
        with patch('reviewed_main_DN_boundaries.bind_question', return_value=dict(answer=dict(decision='供回水不同或段内变径，见说明'))), \
                patch('reviewed_main_DN_boundaries.read_source') as native:
            with self.assertRaisesRegex(ValueError, 'partial replies remain unresolved'):
                compute({}, {})
        native.assert_not_called()


if __name__ == '__main__':
    unittest.main()
