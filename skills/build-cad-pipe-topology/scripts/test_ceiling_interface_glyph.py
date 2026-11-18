import math
import unittest
from cad_ceiling_native_rules import match_out_of_plane_symbol


class NearbyOppositeGlyphTest(unittest.TestCase):
    def scene(self, angle, mirror):
        # Native SH16 08 measurements, simplified below drawing tolerance.
        segments = [((-0., 0.), (52.09458, 114.14687)),
                    ((0., 0.), (114.14687, 52.09458)),
                    ((34.72067, 131.52078), (131.52078, 34.72067)),
                    ((51.73687, 148.53698), (148.53698, 51.73687)),
                    ((39.02, -69.69), (132.59, -169.61)),
                    ((56.58, -53.24), (150.15, -153.16))]
        theta = math.radians(angle)
        def tf(p):
            x, y = p; x = -x if mirror else x
            return (x*math.cos(theta)-y*math.sin(theta)+1000,
                    x*math.sin(theta)+y*math.cos(theta)+2000)
        return ({'center': tf((0, 0)), 'radius': 80},
                [{'handle': str(i), 'a': tf(a), 'b': tf(b)} for i, (a, b) in enumerate(segments)])

    def test_opposite_symbol_bars_do_not_hide_correct_pair(self):
        for angle in (0, 37, 90, 180, 270):
            for mirror in (False, True):
                with self.subTest(angle=angle, mirror=mirror):
                    circle, lines = self.scene(angle, mirror)
                    arms, bars = match_out_of_plane_symbol(circle, lines)
                    self.assertEqual({x['handle'] for x in arms + bars}, {'0', '1', '2', '3'})

    def test_extra_qualified_bar_keeps_ambiguous(self):
        circle, lines = self.scene(0, False)
        extra = dict(lines[2], handle='extra')
        self.assertIsNone(match_out_of_plane_symbol(circle, lines + [extra]))

    def test_unrelated_circle_and_missing_arm_are_not_interfaces(self):
        circle, lines = self.scene(0, False)
        self.assertIsNone(match_out_of_plane_symbol(dict(circle, radius=100), lines))
        self.assertIsNone(match_out_of_plane_symbol(circle, lines[1:]))


if __name__ == '__main__': unittest.main()
