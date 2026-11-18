import unittest
from pipe_annotation_attributes import direct_diameters, parse_dn_annotation, parse_named_dn_annotation


class NativeDnLabelsTest(unittest.TestCase):
    def test_sh16_parenthesized_value_retained_without_interpretation(self):
        result = parse_dn_annotation('DN450(2.900)')
        self.assertEqual(result, {'nominal_mm': 450., 'parenthesized_source_value': '2.900'})
        self.assertEqual(parse_dn_annotation('DN 80 (-1.250)')['parenthesized_source_value'], '-1.250')

    def test_multi_label_and_nonpositive_are_not_single_dn(self):
        for value in ('DN300(3.600)/DN200(3.000)', 'DN0', 'DN200(错)', 'DN200~DN150'):
            self.assertIsNone(parse_dn_annotation(value))

    def test_named_dn_is_unbound_and_strict(self):
        for value,system,route in [('CHWS1 DN450','supply','1'),('chwr 2 DN 450','return','2')]:
            parsed=parse_named_dn_annotation(value);self.assertEqual((parsed['system'],parsed['route_number'],parsed['nominal_mm']), (system,route,450.));self.assertEqual(parsed['original_text'],value);self.assertEqual(parsed['binding_status'],'unbound_source_text_candidate');self.assertIsNone(parse_dn_annotation(value))
        for value in ('CHWS0 DN450','CHWR1 DN0','CHWS1 DN450/DN200','prefix CHWS1 DN450','CHWS1 DN450 (2.9)','DN450'):
            self.assertIsNone(parse_named_dn_annotation(value))

    def test_source_suffix_does_not_bypass_geometry(self):
        t = dict(id='T', text='DN450(2.900)', layer='A', rotation=0, position=[5, 1], height=1)
        edges = [dict(edge_id='E', attribute_paths=[[(0, 0), (10, 0)]]),
                 dict(edge_id='OTHER', attribute_paths=[[(0, 2), (10, 2)]])]
        yes, no = direct_diameters([t], edges, set(), ['A'])
        self.assertEqual(yes, [])
        self.assertEqual(no[0]['status'], 'pending')
        yes, no = direct_diameters([t], edges[:1], set(), ['A'])
        self.assertEqual((yes[0]['nominal_mm'], yes[0]['parenthesized_source_value']), (450., '2.900'))


if __name__ == '__main__':
    unittest.main()
