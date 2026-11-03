import unittest

from ceiling_equipment_labels import bind_ceiling_equipment_labels


def label(text, x, y):
    return {"text": text, "x": x, "y": y}


class CeilingEquipmentLabelTest(unittest.TestCase):
    def test_shared_halo_label_is_not_unique_to_the_block_with_one_hit(self):
        # SH16-09 inserts 63 and 65, texts 69 and 6A. Text 6A is below 65 and
        # also inside 63's 600-unit box. The old sole-candidate counter gave
        # 6A to block 65.
        blocks = [
            {"source_handle": "63", "bounds": ((2313672.1390086897, 74946.9949084227), (2314672.1390086897, 76438.94011474634))},
            {"source_handle": "65", "bounds": ((2314872.1390086897, 74946.9949084227), (2315872.1390086897, 76438.94011474634))},
        ]
        labels = [
            label("CRAH-4#-2-1", 2313298.024393293, 74638.75766610047),
            label("CRAH-4#-2-2", 2315190.155879353, 74638.75766610035),
        ]
        rows = {row["source_handle"]: row for row in bind_ceiling_equipment_labels(blocks, labels)}
        self.assertEqual(rows["65"]["association_status"], "label_unresolved")
        self.assertEqual(rows["63"]["association_status"], "label_unresolved")
        self.assertEqual(rows["65"]["connection_status"], "ports_unresolved")
        self.assertNotIn("port_id", rows["65"])

    def test_label_inside_bounds_stays_with_that_block(self):
        blocks = [
            {"source_handle": "A", "bounds": ((0, 0), (1000, 800))},
            {"source_handle": "B", "bounds": ((1200, 0), (2200, 800))},
        ]
        labels = [label("CRAH-A", 100, 100), label("CRAH-B", 2500, -100)]
        rows = {row["source_handle"]: row for row in bind_ceiling_equipment_labels(blocks, labels)}
        self.assertEqual(rows["A"]["association_status"], "unique_bounded_source_label")
        self.assertEqual(rows["A"]["label_candidates"], ["CRAH-A"])
        self.assertEqual(rows["B"]["association_status"], "unique_bounded_source_label")
        self.assertEqual(rows["B"]["label_candidates"], ["CRAH-B"])

    def test_two_labels_inside_one_block_stay_unresolved(self):
        blocks = [{"source_handle": "A", "bounds": ((0, 0), (1000, 800))}]
        labels = [label("CRAH-1", 10, 10), label("CRAH-2", 20, 20)]
        row = bind_ceiling_equipment_labels(blocks, labels)[0]
        self.assertEqual(row["association_status"], "label_unresolved")
        self.assertEqual(row["connection_status"], "ports_unresolved")


if __name__ == "__main__":
    unittest.main()
