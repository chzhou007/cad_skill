import unittest
from unbound_ceiling_symbols import identify


class UnboundCeilingSymbolsTest(unittest.TestCase):
    def setUp(self):
        self.circle = {'handle': 'C', 'center': [0, 0], 'radius': 80, 'system': 'return'}
        def line(h, a, b): return {'handle': h, 'a': a, 'b': b, 'layer': '空调立管、水平支管', 'system': None}
        self.glyphs = [line('a', [0, 0], [52.09458, 114.14687]),
                       line('b', [0, 0], [114.14687, 52.09458]),
                       line('c', [34.72067, 131.52078], [131.52078, 34.72067]),
                       line('d', [51.73687, 148.53698], [148.53698, 51.73687])]

    def test_near_endpoint_remains_diagnostic(self):
        line = {'handle': 'P', 'a': [0.427, 0], 'b': [10, 0], 'system': 'return', 'layer': 'return'}
        other = dict(line, handle='S', system='supply')
        result = identify([self.circle], self.glyphs + [line, other], set())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['connectivity'], 'unverified')
        self.assertEqual([p['source_handle'] for p in result[0]['near_same_system_source_endpoints']], ['P'])
        self.assertEqual(result[0]['source_system_conflict'], 'not_observed_at_circle_center')
        exact_opposite = dict(other, a=[0, 0])
        conflict = identify([self.circle], self.glyphs + [line, exact_opposite], set())[0]
        self.assertEqual(conflict['source_system_conflict'], 'exact_opposite_system_endpoint')
        self.assertEqual(conflict['near_opposite_system_source_endpoints'][0]['source_handle'], 'S')
        self.assertEqual(identify([self.circle], self.glyphs + [line], {'C'}), [])

    def test_complete_glyph_without_pipe_is_not_discarded(self):
        result = identify([self.circle], self.glyphs, set())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['near_same_system_source_endpoints'], [])
        self.assertEqual(identify([self.circle], self.glyphs[:-1], set()), [])

    def test_bad_sources_rejected(self):
        with self.assertRaises(ValueError): identify([self.circle, self.circle], self.glyphs, set())
        with self.assertRaises(ValueError): identify([self.circle], self.glyphs, {'missing'})
        with self.assertRaises(ValueError): identify([self.circle], self.glyphs, set(), diagnostic_radius=.01)


if __name__ == '__main__': unittest.main()
