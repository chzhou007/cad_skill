import unittest
import ezdxf
from equipment_label_source_annotations import extract


class EquipmentLabelSourceAnnotations(unittest.TestCase):
    def setUp(self):
        self.doc = ezdxf.new()
        self.label = self.doc.modelspace().add_text('设备-1', dxfattribs={'insert': (10, 20), 'height': 3, 'rotation': 90, 'width': .6})
        self.node = {'source_label_pair_evidence': {'identity_confirmed': False, 'plan_source_sha256': 'source',
                     'alternatives': [{'label': '设备-1', 'plan_text_handle': self.label.dxf.handle}]}}

    def test_native_position_and_unconfirmed_identity(self):
        rows = extract(self.doc, [self.node, self.node], 'source')
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['text'], rows[0]['position'], rows[0]['rotation'], rows[0]['width_factor']), ('设备-1', [10, 20], 90, .6))
        self.assertEqual(rows[0]['identity_binding'], 'unconfirmed')

    def test_fails_closed_for_changed_source_text_and_alignment(self):
        with self.assertRaises(ValueError): extract(self.doc, [self.node], 'other')
        self.label.dxf.text = '设备-2'
        with self.assertRaises(ValueError): extract(self.doc, [self.node], 'source')
        self.label.dxf.text = '设备-1'; self.label.dxf.halign = 1
        with self.assertRaises(ValueError): extract(self.doc, [self.node], 'source')

if __name__ == '__main__': unittest.main()
