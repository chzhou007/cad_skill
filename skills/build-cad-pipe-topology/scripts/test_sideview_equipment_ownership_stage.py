import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sideview_equipment_ownership_stage import load_policy_map, run_stage


class SideviewStageTests(unittest.TestCase):
    def test_map_resolves_relative_paths_and_rejects_unknown_tasks(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'map.json'
            p.write_text(json.dumps({'SH16-09': 'policy.json'}), encoding='utf8')
            self.assertEqual(load_policy_map(p, {'SH16-09'})['SH16-09'], p.parent / 'policy.json')
            with self.assertRaisesRegex(ValueError, 'unrecognized'):
                load_policy_map(p, {'SH16-08'})

    def test_invalid_map_never_launches(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'map.json'
            for value in ([], {'T': {}}, {'T': ''}, {'T': '   '}):
                p.write_text(json.dumps(value), encoding='utf8')
                with self.assertRaises(ValueError):load_policy_map(p)
        self.assertEqual(load_policy_map(None), {})

    def test_entry_writes_receipt_only_after_independent_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve();source = root/'source.dxf';source.write_bytes(b'source')
            parent = root/'parent/graph_with_edges.json';parent.parent.mkdir();parent.write_bytes(b'{}')
            dest = root/'task/topology-source-sideview-equipment-ownership'
            def produce(command, check):
                self.assertTrue(check)
                self.assertIn(str(parent.parent/'assigned_edge_device_instances.csv'), command)
                dest.mkdir(parents=True);(dest/'sideview-equipment-ownership-audit.json').write_bytes(b'audit')
            with patch('sideview_equipment_ownership_stage.subprocess.run', side_effect=produce),patch(
                'reconstruct_sideview_equipment_ownership.verify_output', return_value={'output_graph_sha256':'H','records':[]}) as replay:
                path,audit = run_stage(source,parent,root/'policy.json',root/'task')
            replay.assert_called_once_with(dest)
            self.assertEqual(path,dest/'graph_with_edges.json')
            receipt=json.loads((root/'task/reports/source-sideview-equipment-ownership-stage.json').read_text())
            self.assertEqual(receipt['graph_sha256'],'H');self.assertFalse(receipt['hil_ready'])
            self.assertFalse(receipt['physical_ports_verified']);self.assertFalse(receipt['detail_view_metric_verified'])

    def test_failed_replay_cannot_publish_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch('sideview_equipment_ownership_stage.subprocess.run'),patch(
                'reconstruct_sideview_equipment_ownership.verify_output',side_effect=ValueError('native changed')):
                with self.assertRaisesRegex(ValueError,'native changed'):
                    run_stage(root/'s',root/'g',root/'p',root/'task')
            self.assertFalse((root/'task/reports/source-sideview-equipment-ownership-stage.json').exists())


if __name__=='__main__':unittest.main()
