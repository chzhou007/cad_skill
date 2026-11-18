import copy, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import test_source_reviewed_circle_branch_evidence as reviewed
import test_normalize_two_arm_circle_continuity as two_arm
from confirm_crossview_paths import encode, sha, load
from current_circle_main_lineage import collect, membership
from normalize_two_arm_circle_continuity import collect as contacts, normalize
from current_circle_plan_DN import current_tee


class Tests(unittest.TestCase):
    def pin(self, graph, role):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'parent.json'
        path.write_bytes(encode(graph))
        return dict(path=str(path), sha256=sha(path), role=role)

    def split_fixture(self, angle=0, mirror=1):
        fixture = reviewed.HistoricalReviewedCircleTests()
        self.addCleanup(fixture.doCleanups)
        doc, parent, _ = fixture.legacy_fixture(angle, mirror)
        parent['metadata'] = dict(source_sha256='S')
        for edge in parent['edges']:
            edge['path'] = copy.deepcopy(edge['attribute_paths'][0])
        pin = self.pin(parent, 'reviewed_circle_split_origin')
        current = copy.deepcopy(parent)
        edge = next(e for e in current['edges'] if e['edge_id'] == 'M1')
        edge['edge_id'] = 'CURRENT-MAIN'
        edge['path'] = [[v/2 for v in p] for p in edge['path']]
        edge['attribute_paths'] = [copy.deepcopy(edge['path'])]
        edge['path_length'] = 10
        edge['split_source_edge'] = dict(edge_id='M1', source_graph_sha256=pin['sha256'], interval_native_units=[0, 10])
        # slice_path keeps floating point arithmetic of the original producer.
        from repair_confirmed_circle_junctions import slice_path
        edge['path'] = slice_path(next(e for e in parent['edges'] if e['edge_id']=='M1')['path'], 0, 10)
        edge['attribute_paths'] = [copy.deepcopy(edge['path'])]
        current['userConfirmedCircleJunctionRepair'] = dict(source_sha256='S', input_graph_sha256=pin['sha256'],
            records=[dict(main_source_edge='M1', main_child_edges=['CURRENT-MAIN', 'TAIL'])])
        return doc, current, pin

    def test_current_native_T_survives_source_bound_split_rotation_and_mirror(self):
        for angle, mirror in [(0, 1), (90, 1), (180, -1), (270, -1)]:
            doc, graph, pin = self.split_fixture(angle, mirror)
            before = copy.deepcopy(graph)
            proof = collect(doc, graph, 'T', 'S', 'G', [pin])
            self.assertEqual(graph, before)
            self.assertEqual(proof['current_main_lineage'][0]['original_edge_id'], 'M1')
            self.assertEqual(len(proof['junctions'][0]['source_rays']), 3)
            self.assertEqual(proof['physical_values_assigned'], 0)
            self.assertFalse(proof['historical_reader_or_globals_changed'])

    def test_split_provenance_geometry_and_native_ambiguities_remain_barriers(self):
        for mode in ('missing_parent', 'changed_parent', 'wrong_root', 'path', 'mixed', 'duplicate_main', 'radius'):
            doc, graph, pin = self.split_fixture()
            edge = next(e for e in graph['edges'] if e['edge_id'] == 'CURRENT-MAIN')
            parents = [pin]
            if mode == 'missing_parent': parents = []
            elif mode == 'changed_parent': Path(pin['path']).write_bytes(b'{}')
            elif mode == 'wrong_root': graph['userConfirmedCircleJunctionRepair']['records'][0]['main_source_edge']='OTHER'
            elif mode == 'path': edge['path'][1][0] += 1
            elif mode == 'mixed': edge['system']='return'
            elif mode == 'duplicate_main':
                entity = doc.entitydb[edge['source_handles'][0]]
                doc.modelspace().add_line(entity.dxf.start, entity.dxf.end, dxfattribs={'layer': entity.dxf.layer})
            elif mode == 'radius': graph['edges'][0]['attribute_paths'][0][0]=[0,0]
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                collect(doc, graph, 'T', 'S', 'G', parents)

    def test_native_two_arm_merge_retains_reviewed_ancestor_and_unknown_length(self):
        doc, parent, handles, _ = two_arm.fixture(True)
        parent['metadata']['source_sha256']='S'
        pin = self.pin(parent, 'two_arm_origin')
        parent = load(pin['path'])
        graph, _ = normalize(parent, contacts(doc, parent, handles))
        before = copy.deepcopy(graph)
        receipts=[]
        membership(doc, graph, graph['edges'][0], dict(main_child_edges=['E0']), 'S', [pin], receipts)
        self.assertEqual(graph, before)
        self.assertEqual(receipts[0]['kind'], 'native_two_arm_merge')
        self.assertIsNone(graph['edges'][0]['physical_length_mm'])
        graph['edges'][0]['source_circle_continuity']['prior_edge_snapshots'][0]['system']='supply'
        with self.assertRaises(ValueError):
            membership(doc, graph, graph['edges'][0], dict(main_child_edges=['E0']), 'S', [pin], [])

    def test_geometry_failure_does_not_trigger_lineage_fallback(self):
        with patch('current_circle_plan_DN.original_tee', side_effect=ValueError('native T ray is not uniquely witnessed')):
            with patch('current_circle_plan_DN.circle_collect') as fallback:
                with self.assertRaisesRegex(ValueError, 'not uniquely witnessed'):
                    current_tee(None, {}, 'T', 'S', 'G', [])
                fallback.assert_not_called()


if __name__ == '__main__':
    unittest.main()
