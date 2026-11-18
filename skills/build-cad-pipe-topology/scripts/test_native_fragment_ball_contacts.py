import copy
import unittest

from native_fragment_ball_contacts import collect
from test_native_ball_contact_reapplication import fixture


def scene(rotation=0, mirror=1, extrusion=(0, 0, 1)):
    doc, graph, insert, pipe, row = fixture(rotation, mirror, extrusion)
    for e in graph['edges']:
        e['connection_mode'] = 'standalone_multiport_omission_stitched_by_order'
        e['source_handles'] = ['OMISSION-MARKER']
    route = dict(records=[])
    for edge, line in zip(graph['edges'], list(doc.modelspace().query('LINE'))):
        route['records'].append(dict(edge_id=edge['edge_id'], path_index=0, segment_index=0,
            system=edge['system'], scope_points=copy.deepcopy(edge['attribute_paths'][0]),
            native_source_status='single_source_line_covers', source_line_coverage_checked=True,
            native_witnesses=[dict(scope='modelspace', source_handle=line.dxf.handle,
                layer=line.dxf.layer, start=list(line.dxf.start)[:2], end=list(line.dxf.end)[:2])]))
    row.update(edge_id='MAIN', source_top_handle='UNRELATED')
    return doc, graph, insert, pipe, row, route


class Tests(unittest.TestCase):
    def test_original_contacts_reused_for_omission_fragment_rotations_and_negative_OCS(self):
        for rotation in (0, 45, 90, 180):
            for mirror in (-1, 1):
                for extrusion in ((0, 0, 1), (0, 0, -1)):
                    d, g, ins, pipe, old, routing = scene(rotation, mirror, extrusion)
                    snapshot = copy.deepcopy(g)
                    out = collect(d, g, [old], routing)
                    self.assertEqual(out['counts']['added_components'], 1)
                    self.assertEqual(out['added_components'][0]['edge_id'], 'MAIN')
                    self.assertEqual(out['components'][0], old)
                    self.assertEqual(out['added_components'][0]['resistance'], '')
                    self.assertEqual(g, snapshot)
                    self.assertFalse(out['whole_edge_continuity_assigned'])
                    self.assertEqual(collect(d, g, out['components'], routing)['added_components'], [])

    def test_source_or_graph_competition_and_foreign_Z_remain_unresolved(self):
        for kind in ('source', 'graph', 'Z', 'unwitnessed'):
            d, g, ins, pipe, old, routing = scene()
            if kind == 'source':
                d.modelspace().add_line(pipe.dxf.start, pipe.dxf.end, dxfattribs={'layer': pipe.dxf.layer})
            elif kind == 'graph':
                g['edges'].append(dict(g['edges'][0], edge_id='OTHER'))
                routing['records'].append(dict(routing['records'][0], edge_id='OTHER'))
            elif kind == 'Z':
                a, b = list(pipe.dxf.start), list(pipe.dxf.end)
                a[2] = b[2] = 1
                pipe.dxf.start, pipe.dxf.end = a, b
            else:
                routing['records'][0]['native_source_status'] = 'unresolved'
            with self.subTest(kind=kind):
                self.assertEqual(collect(d, g, [old], routing)['added_components'], [])

    def test_partial_or_stale_routing_and_conflicting_prior_owner_fail_closed(self):
        for kind in ('partial', 'points', 'witness'):
            d, g, ins, pipe, old, routing = scene()
            if kind == 'partial': routing['records'].pop()
            elif kind == 'points': routing['records'][0]['scope_points'][0][0] += 1
            else: routing['records'][0]['native_witnesses'][0]['start'][0] += 1
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                collect(d, g, [old], routing)
        d, g, ins, pipe, old, routing = scene()
        old.update(source_top_handle=ins.dxf.handle, edge_id='BRANCH')
        out = collect(d, g, [old], routing)
        self.assertEqual(out['components'], [old])
        self.assertEqual(out['counts']['statuses']['existing_owner_conflict_retained'], 1)


if __name__ == '__main__': unittest.main()
