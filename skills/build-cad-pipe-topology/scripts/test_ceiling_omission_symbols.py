import unittest

from cad_ceiling_native_rules import match_out_of_plane_symbol


def line(handle, a, b):
    return {"handle": handle, "a": a, "b": b}


def symbol_at(origin=(0, 0), rear=False):
    """Relative geometry of SH16-08 return circle 112 and its forward bars.

    The rear bars are the neighboring supply symbol's bars, 200 drawing
    units away, which the old radius test counted as part of this circle.
    """
    ox, oy = origin
    def shift(pt):
        return (pt[0] + ox, pt[1] + oy)
    rows = [
        line("arm-a", shift((0, 0)), shift((52.1, 114.1))),
        line("arm-b", shift((0, 0)), shift((114.1, 52.1))),
        line("bar-a", shift((34.7, 131.5)), shift((131.5, 34.7))),
        line("bar-b", shift((51.7, 148.5)), shift((148.5, 51.7))),
    ]
    if rear:
        rows.extend([
            line("rear-a", shift((39.0, -69.7)), shift((132.6, -169.6))),
            line("rear-b", shift((56.6, -53.2)), shift((150.2, -153.2))),
        ])
    return {"center": origin, "radius": 80, "system": "return"}, rows


class CeilingOmissionSymbolTest(unittest.TestCase):
    def test_complete_symbol_matches_without_a_neighbor(self):
        circle, glyphs = symbol_at()
        arms, bars = match_out_of_plane_symbol(circle, glyphs)
        self.assertEqual([item["handle"] for item in arms], ["arm-a", "arm-b"])
        self.assertEqual([item["handle"] for item in bars], ["bar-a", "bar-b"])

    def test_neighbor_bars_behind_the_v_do_not_reject_or_bind(self):
        circle, glyphs = symbol_at(rear=True)
        arms, bars = match_out_of_plane_symbol(circle, glyphs)
        handles = {item["handle"] for item in arms + bars}
        self.assertEqual(handles, {"arm-a", "arm-b", "bar-a", "bar-b"})
        self.assertNotIn("rear-a", handles)
        self.assertNotIn("rear-b", handles)

    def test_extra_forward_bar_stays_unmatched(self):
        circle, glyphs = symbol_at()
        glyphs.append(line("extra", (40, 160), (150, 70)))
        self.assertIsNone(match_out_of_plane_symbol(circle, glyphs))

    def test_bars_only_behind_the_arms_stay_unmatched(self):
        circle, glyphs = symbol_at(rear=True)
        glyphs = [item for item in glyphs if not item["handle"].startswith("bar-")]
        self.assertIsNone(match_out_of_plane_symbol(circle, glyphs))

    def test_mirrored_symbol_uses_its_own_arm_direction(self):
        circle, glyphs = symbol_at()
        flipped = []
        for item in glyphs:
            flipped.append(line(item["handle"], (item["a"][0], -item["a"][1]), (item["b"][0], -item["b"][1])))
        flipped.extend([
            line("other-a", (39.0, 69.7), (132.6, 169.6)),
            line("other-b", (56.6, 53.2), (150.2, 153.2)),
        ])
        arms, bars = match_out_of_plane_symbol(circle, flipped)
        self.assertEqual({item["handle"] for item in bars}, {"bar-a", "bar-b"})


if __name__ == "__main__":
    unittest.main()
