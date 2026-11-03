import unittest

import dual_view_attributes as attributes


def segment(segment_id, system, direct=None, links=()):
    return {
        "id": segment_id,
        "system": system,
        "direct_diameter": direct,
        "links": [dict(item) for item in links],
    }


class DualViewAttributeTest(unittest.TestCase):
    def test_one_direct_diameter_inherits_through_a_proven_same_system_tee(self):
        result = attributes.inherit_diameter([
            segment("main", "supply", 150, [{"id": "branch", "proven": True}]),
            segment("branch", "supply", links=[{"id": "main", "proven": True}]),
        ])
        self.assertEqual(result["main"]["status"], "direct")
        self.assertEqual(result["branch"]["status"], "inherited")
        self.assertEqual(result["branch"]["value"], 150)
        self.assertEqual(result["branch"]["chain"][0], "main")

    def test_unproven_link_and_other_system_do_not_inherit(self):
        result = attributes.inherit_diameter([
            segment("supply-main", "supply", 100, [
                {"id": "open-end", "proven": False},
                {"id": "return-main", "proven": True},
            ]),
            segment("open-end", "supply"),
            segment("return-main", "return"),
        ])
        self.assertEqual(result["open-end"]["status"], "unknown")
        self.assertIsNone(result["open-end"]["value"])
        self.assertEqual(result["return-main"]["status"], "unknown")

    def test_conflicting_direct_diameters_keep_evidence_and_fill_nothing(self):
        result = attributes.inherit_diameter([
            segment("left", "supply", 100, [{"id": "middle", "proven": True}]),
            segment("middle", "supply", links=[{"id": "left", "proven": True}, {"id": "right", "proven": True}]),
            segment("right", "supply", 150, [{"id": "middle", "proven": True}]),
        ])
        self.assertEqual(result["left"]["value"], 100)
        self.assertEqual(result["right"]["value"], 150)
        self.assertEqual(result["middle"]["status"], "conflict")
        self.assertIsNone(result["middle"]["value"])
        self.assertTrue(all(item["value"] != 0 for item in result.values()))

    def test_zero_is_rejected_for_unknown_diameter_and_length(self):
        with self.assertRaises(attributes.AttributeError):
            attributes.inherit_diameter([segment("bad", "supply", 0)])
        with self.assertRaises(attributes.AttributeError):
            attributes.physical_length("horizontal", "plan", 0, "source_dimension")

    def test_length_source_follows_orientation(self):
        horizontal = attributes.physical_length("horizontal", "plan", 12.5, "matched_plan_dimension")
        rejected = attributes.physical_length("horizontal", "isometric", 12.5, "isometric_annotation")
        vertical = attributes.physical_length("vertical", "isometric", 3.2, "elevation_delta")
        self.assertEqual(horizontal["completeness"], "complete")
        self.assertEqual(horizontal["value"], 12.5)
        self.assertEqual(rejected["completeness"], "incomplete")
        self.assertIsNone(rejected["value"])
        self.assertEqual(vertical["expected_source"], "isometric")
        self.assertEqual(vertical["value"], 3.2)

    def test_difference_cannot_overwrite_either_view(self):
        difference = attributes.record_difference(
            "branch_mismatch",
            {"edge": "plan-e1"},
            {"edge": "iso-e9"},
        )
        self.assertFalse(difference["may_overwrite_other_view"])
        self.assertEqual(difference["disposition"], "unresolved")
        with self.assertRaises(attributes.AttributeError):
            attributes.record_difference("branch_mismatch", {"edge": "plan-e1"}, {})


if __name__ == "__main__":
    unittest.main()
