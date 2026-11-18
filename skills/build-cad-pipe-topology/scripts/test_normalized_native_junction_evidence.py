import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pipe_geometry as pg
from test_native_junction_ray_evidence import fixture
from crossview_equipment_branch_inventory import native_tee
from normalized_native_junction_evidence import prepare, collect
from topology_normalization import snap_near_junction_endpoints


def case(folder, gap=2.354840376327047, opposite=False, z=0):
    d, g, policy = fixture()
    m = d.modelspace()
    main = d.entitydb[policy['junctions'][0]['edge_witnesses']['L']]
    branch = d.entitydb[policy['junctions'][0]['edge_witnesses']['B']]
    m.delete_entity(branch)
    branch = m.add_line((0, gap, z), (0, 100, z), dxfattribs={'layer': main.dxf.layer})
    marker = m.add_lwpolyline([(-1, 120), (0, 119), (1, 120)], dxfattribs={'layer': 'DIM_SYMB'})
    g['edges'][2].update(attribute_paths=[[[0, 0], [0, 100]]], source_insert_handle=marker.dxf.handle)
    g['nodes'].extend(dict(node_id=n, node_type='unresolved_endpoint', x=x, y=y)
                      for n, x, y in [('L', -10, 0), ('R', 10, 0), ('B', 0, 100)])
    if opposite:
        m.add_line((0, -20), (0, 110), dxfattribs={'layer': '空调冷冻水回水'})
    config = dict(system_layers={'空调冷冻水供水': 'supply', '空调冷冻水回水': 'return'},
                  elbow_overshoot=dict(maximum_length=10, maximum_ratio=.1, minimum_angle_degrees=20),
                  near_junction=dict(maximum_gap=3, discovery_maximum_gap=10,
                                     maximum_ratio=.05, minimum_angle_degrees=20),
                  previous_source_sha256='S')
    # Original shared rule supplies the record; the new reader must independently
    # recover these rows from the DXF, through the historical collector and trim.
    rows = [dict(a=tuple(e.dxf.start)[:2], b=tuple(e.dxf.end)[:2],
                 system=config['system_layers'][e.dxf.layer], source_handles=[e.dxf.handle],
                 handle=e.dxf.handle) for e in m.query('LINE')]
    old = pg.TOL
    try:
        pg.set_tolerance(.2)
        _, records = snap_near_junction_endpoints(rows, config['near_junction'])
    finally:
        pg.set_tolerance(old)
    audit = dict(config=config, elbow_overshoots=[], junction_snaps=records)
    p = Path(folder)/'audit.json'; p.write_text(json.dumps(audit), encoding='utf8')
    spec = dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    return d, g, branch, spec


class NormalizedJunctionTests(unittest.TestCase):
    def test_old_rule_replayed_before_T_evidence_not_metric_coverage(self):
        from partial_native_line_coverage import intervals
        with tempfile.TemporaryDirectory() as folder:
            d, g, branch, spec = case(folder)
            old = copy.deepcopy(g); before_tol = pg.TOL
            with self.assertRaisesRegex(ValueError, 'selected ray insert mismatch'):
                native_tee(d, g, 'T', 'S', 'G')
            context = prepare(d, g, 'S', 'G', spec)
            result = collect(d, g, 'T', 'S', 'G', normalization=context)
            node = result['junctions'][0]
            ray = next(r for r in node['source_rays'] if r['edge_id'] == 'B')
            self.assertTrue(node['normalization_replayed'])
            self.assertEqual(ray['source_line_handle'], branch.dxf.handle)
            self.assertIsNone(ray['physical_gap_length'])
            self.assertFalse(ray['source_gap_is_measured'])
            self.assertAlmostEqual(ray['normalization']['normalization_distance'], 2.354840376327047)
            parts = intervals([0, 0], [0, 100], [(branch.dxf.handle, [0, branch.dxf.start.y], [0, 100])])
            self.assertEqual(parts[0]['status'], 'unwitnessed')
            self.assertEqual(g, old); self.assertEqual(pg.TOL, before_tol)
            self.assertFalse(result['hil_ready'])

    def test_original_limit_and_opposing_service_remain_independent(self):
        with tempfile.TemporaryDirectory() as folder:
            d, g, _, spec = case(folder, gap=4)
            context = prepare(d, g, 'S', 'G', spec)
            self.assertEqual(context.audit['junction_snaps'][0]['status'], 'pending')
            with self.assertRaisesRegex(ValueError, 'selected ray insert mismatch'):
                collect(d, g, 'T', 'S', 'G', normalization=context)
        with tempfile.TemporaryDirectory() as folder:
            d, g, _, spec = case(folder, opposite=True)
            result = collect(d, g, 'T', 'S', 'G', normalization=prepare(d, g, 'S', 'G', spec))
            self.assertEqual(len(result['junctions'][0]['opposite_system_contacts']), 1)

    def test_audit_source_hash_forgery_and_context_changes_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            d, g, branch, spec = case(folder)
            with self.assertRaisesRegex(ValueError, 'source hash'):
                prepare(d, g, 'different-source', 'G', spec)
            context = prepare(d, g, 'S', 'G', spec)
            branch.dxf.start = (0, 3, 0)
            with self.assertRaisesRegex(ValueError, 'context changed'):
                collect(d, g, 'T', 'S', 'G', normalization=context)
            with self.assertRaisesRegex(ValueError, 'does not replay'):
                prepare(d, g, 'S', 'G', spec)
            p = Path(spec['path']); audit = json.loads(p.read_bytes())
            audit['junction_snaps'][0]['added_length'] = 0
            p.write_text(json.dumps(audit), encoding='utf8')
            with self.assertRaisesRegex(ValueError, 'audit hash'):
                prepare(d, g, 'S', 'G', spec)

    def test_different_Z_never_qualified_by_XY_normalization(self):
        with tempfile.TemporaryDirectory() as folder:
            d, g, _, spec = case(folder, z=5)
            context = prepare(d, g, 'S', 'G', spec)
            with self.assertRaisesRegex(ValueError, 'selected ray insert mismatch'):
                collect(d, g, 'T', 'S', 'G', normalization=context)

    def test_extra_same_system_source_remains_a_blocker(self):
        with tempfile.TemporaryDirectory() as folder:
            d, g, _, spec = case(folder)
            context = prepare(d, g, 'S', 'G', spec)
            d.modelspace().add_line((0, -10), (0, 0), dxfattribs={'layer': '空调冷冻水供水'})
            with self.assertRaises(ValueError):
                collect(d, g, 'T', 'S', 'G', normalization=context)

    def test_changed_record_with_a_fresh_hash_still_needs_source_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            d, g, _, spec = case(folder)
            p = Path(spec['path']); audit = json.loads(p.read_bytes())
            audit['junction_snaps'][0]['added_length'] = 0
            p.write_text(json.dumps(audit), encoding='utf8')
            spec['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, 'does not replay'):
                prepare(d, g, 'S', 'G', spec)

    def test_current_graph_and_normalized_competing_contacts_rechecked(self):
        with tempfile.TemporaryDirectory() as folder:
            d, g, _, spec = case(folder)
            context = prepare(d, g, 'S', 'G', spec)
            g['edges'][0]['system'] = 'return'
            with self.assertRaisesRegex(ValueError, 'context changed'):
                collect(d, g, 'T', 'S', 'G', normalization=context)
        with tempfile.TemporaryDirectory() as folder:
            d, g, _, spec = case(folder)
            d.modelspace().add_line((0, -10), (0, 0), dxfattribs={'layer': '空调冷冻水供水'})
            context = prepare(d, g, 'S', 'G', spec)
            with self.assertRaisesRegex(ValueError, 'unaccounted'):
                collect(d, g, 'T', 'S', 'G', normalization=context)

    def test_nested_competitor_changes_cannot_reuse_the_replayed_context(self):
        with tempfile.TemporaryDirectory() as folder:
            d, g, _, spec = case(folder)
            context = prepare(d, g, 'S', 'G', spec)
            block = d.blocks.new('NEW_COMPETITOR')
            block.add_line((0, 0), (10, 10), dxfattribs={'layer': '空调冷冻水供水'})
            d.modelspace().add_blockref(block.name, (0, 0))
            with self.assertRaisesRegex(ValueError, 'context changed'):
                collect(d, g, 'T', 'S', 'G', normalization=context)


if __name__ == '__main__':
    unittest.main()
