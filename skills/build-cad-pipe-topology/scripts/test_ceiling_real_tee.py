import unittest

from cad_ceiling_native_rules import accept_physical_tee, nearby_circle_blocks_physical_tee


def line(handle, a, b, system="return"):
    return {"handle": handle, "a": a, "b": b, "system": system}


class CeilingRealTeeTest(unittest.TestCase):
    def test_unmatched_circle_offset_from_a_real_tee_does_not_block(self):
        """SH16-09 circles 12E9A and 12E9B sit 1.3 units off a perpendicular tee.

        Radius 80 with no V and no bars is not an omission symbol. The
        vertical main and the horizontal branch already meet by endpoint
        incidence, so the circle must not withhold the tee.
        """
        circle = {"handle": "12E9B", "center": (0, 1.3), "radius": 80, "system": "return"}
        segments = [
            line("B669", (0, 160), (0, -160)),
            line("12E98", (0, 0), (200, 0)),
        ]
        self.assertFalse(nearby_circle_blocks_physical_tee(circle, [], segments, [225]))
        self.assertTrue(accept_physical_tee(3, 3, [], []))

    def test_matched_omission_symbol_still_blocks_the_junction(self):
        circle = {"handle": "112", "center": (0, 0), "radius": 80, "system": "return"}
        glyphs = [
            line("arm-a", (0, 0), (52.1, 114.1)),
            line("arm-b", (0, 0), (114.1, 52.1)),
            line("bar-a", (34.7, 131.5), (131.5, 34.7)),
            line("bar-b", (51.7, 148.5), (148.5, 51.7)),
        ]
        self.assertTrue(nearby_circle_blocks_physical_tee(circle, glyphs, [], [225]))
        self.assertFalse(accept_physical_tee(3, 3, [circle], []))

    def test_circle_centered_on_the_contact_can_remain_a_tee(self):
        circle = {"handle": "centered", "center": (0, 0), "radius": 80, "system": "supply"}
        self.assertTrue(accept_physical_tee(3, 3, [circle], [circle]))

    def test_calibrated_riser_still_blocks(self):
        circle = {"handle": "riser", "center": (0, 0), "radius": 225, "system": "supply"}
        segments = [line("radial", (225, 0), (400, 0), system="supply")]
        self.assertTrue(nearby_circle_blocks_physical_tee(circle, [], segments, [225]))

    def test_four_ray_contact_is_not_a_tee(self):
        self.assertFalse(accept_physical_tee(4, 4, [], []))


if __name__ == "__main__":
    unittest.main()
