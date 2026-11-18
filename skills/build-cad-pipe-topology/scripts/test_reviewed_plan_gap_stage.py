import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from confirm_crossview_paths import load, sha, encode
from reviewed_plan_gap_stage import load_policy_map, run_stage, SETTINGS, DESTINATION, STAGE


class Tests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        task = root / 'task'
        parent = task / 'parent/graph_with_edges.json'
        parent.parent.mkdir(parents=True)
        parent.write_text('{}', 'utf8')
        (parent.parent / 'assigned_edge_device_instances.csv').write_text('component', 'utf8')
        source = root / 'source.dxf'
        source.write_text('source', 'utf8')
        settings = {k: root / (k + '.json') for k in SETTINGS}
        for p in settings.values():
            p.write_text('{}', 'utf8')
        return root, task, parent, source, settings

    def produce(self, task, parent, source, settings, mutation=None):
        paths = dict(source=source, graph=parent, devices=parent.parent / 'assigned_edge_device_instances.csv', **settings)
        graph = dict(metadata=dict(hil_ready=False), derivedEvidenceInvalidation=dict(
            historical_annotations_preserved=True, recompute=['mapping', 'human_acceptance']),
            sourceReviewedDrawingGapContinuity=dict(input_graph_sha256=sha(parent), source_sha256=sha(source),
                physical_Ts_added=0, physical_lengths_assigned=0, supply_return_independent=True, human_accepted=False, retired_node_snapshots=[{}]*4,
                records=[dict(equipment_id='D', system=s) for s in ('supply', 'return')]))
        if mutation:
            mutation(graph)
        output = task / DESTINATION
        output.mkdir(parents=True)
        target = output / 'graph_with_edges.json'
        target.write_bytes(encode(graph))
        audit = dict(mode='explicit_reviewed_same_service_plan_gap_continuity_v1',
            output_graph_sha256=sha(target), inputs={k: dict(path=str(v), sha256=sha(v)) for k, v in paths.items()})
        (output / 'reviewed-drawing-gap-audit.json').write_bytes(encode(audit))
        return audit

    def test_map_resolves_evidence_only_and_rejects_local_input_overrides(self):
        root, task, parent, source, settings = self.fixture()
        path = root / 'map.json'
        values = {k: p.name for k, p in settings.items()}
        path.write_bytes(encode({'T': values}))
        self.assertEqual(load_policy_map(path, {'T'})['T'], settings)
        with self.assertRaisesRegex(ValueError, 'unrecognized'):
            load_policy_map(path, {'OTHER'})
        values['graph'] = str(parent)
        path.write_bytes(encode({'T': values}))
        with self.assertRaisesRegex(ValueError, 'only original review'):
            load_policy_map(path)
        self.assertEqual(load_policy_map(None), {})

    def test_external_graph_cannot_bypass_family_parent(self):
        root, task, parent, source, settings = self.fixture()
        with patch('reviewed_plan_gap_stage.subprocess.run') as child:
            with self.assertRaisesRegex(ValueError, 'current task graph'):
                run_stage(source, parent, settings, root / 'other')
        child.assert_not_called()

    def test_native_verify_precedes_stage_publication(self):
        root, task, parent, source, settings = self.fixture()
        audit = {}
        def child(command, check):
            self.assertTrue(check)
            self.assertIn(str(parent), command)
            audit.update(self.produce(task, parent, source, settings))
        with patch('reviewed_plan_gap_stage.subprocess.run', side_effect=child), \
                patch('reconstruct_reviewed_plan_gaps.verify_output', side_effect=lambda _: audit) as verify:
            target, _ = run_stage(source, parent, settings, task)
        verify.assert_called_once_with(task / DESTINATION)
        stage = load(task / STAGE)
        self.assertEqual(stage['graph_sha256'], sha(target))
        self.assertEqual(stage['logical_continuations'], 2)
        self.assertEqual(stage['physical_lengths_assigned'], 0)
        self.assertIn('human_acceptance', stage['recompute_required'])
        self.assertFalse(stage['hil_ready'])

    def test_failed_replay_does_not_publish_receipt(self):
        root, task, parent, source, settings = self.fixture()
        with patch('reviewed_plan_gap_stage.subprocess.run'), \
                patch('reconstruct_reviewed_plan_gaps.verify_output', side_effect=ValueError('native differs')):
            with self.assertRaisesRegex(ValueError, 'native differs'):
                run_stage(source, parent, settings, task)
        self.assertFalse((task / STAGE).exists())

    def test_mid_execution_change_and_unproven_physical_acceptance_rejected(self):
        for mode in ('mutate_parent', 'claim_port', 'claim_hil'):
            root, task, parent, source, settings = self.fixture()
            audit = {}
            def child(command, check):
                def mutate(graph):
                    if mode == 'claim_port':
                        graph['sourceReviewedDrawingGapContinuity']['physical_Ts_added'] = 1
                    elif mode == 'claim_hil':
                        graph['metadata']['hil_ready'] = True
                audit.update(self.produce(task, parent, source, settings, mutate))
                if mode == 'mutate_parent':
                    parent.write_text('changed', 'utf8')
            with self.subTest(mode=mode), patch('reviewed_plan_gap_stage.subprocess.run', side_effect=child), \
                    patch('reconstruct_reviewed_plan_gaps.verify_output', side_effect=lambda _: audit):
                with self.assertRaises(ValueError):
                    run_stage(source, parent, settings, task)
            self.assertFalse((task / STAGE).exists())


if __name__ == '__main__':
    unittest.main()
