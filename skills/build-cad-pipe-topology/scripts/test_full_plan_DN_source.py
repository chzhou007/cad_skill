import copy,unittest
from test_source_direct_dn_evidence import fixture
from full_plan_DN_source import collect


def source_fixture():
    doc,g,p,line,text=fixture();g['nodes']=[dict(node_id='A',node_type='virtual_equipment',x=0,y=0),dict(node_id='B',node_type='virtual_equipment',x=100,y=0)]
    g['edges'][0].update(start_node_id='A',end_node_id='B')
    return doc,g,line,text


class Tests(unittest.TestCase):
    def test_native_plan_label_is_read_without_any_crossview_mapping_or_a_T(self):
        doc,g,line,text=source_fixture();before=copy.deepcopy(g);r=collect(doc,g,'SRC','GRAPH')
        self.assertEqual(g,before);self.assertEqual(len(r['records']),1);self.assertEqual(r['records'][0]['nominal_mm'],200)
        self.assertFalse(r['crossview_subset_used_for_scope']);self.assertEqual(r['physical_lengths_assigned'],0)
        self.assertEqual(r['annotation_evidence']['direct_observations'][0]['parenthesized_source_value'],'3.000')
    def test_unknown_or_unreadable_annotation_is_not_converted_to_a_value(self):
        doc,g,line,text=source_fixture();text.dxf.text='DN300(3.600)/DN200(3.000)';r=collect(doc,g,'SRC','GRAPH')
        self.assertIsNone(r['records'][0]['nominal_mm']);self.assertEqual(r['records'][0]['status'],'annotation_blocked')
        doc,g,line,text=source_fixture();text.dxf.text='DN200\ufffd'
        with self.assertRaisesRegex(ValueError,'unreadable'):collect(doc,g,'SRC','GRAPH')
    def test_wrong_source_or_unwitnessed_path_stops_only_its_scope(self):
        doc,g,line,text=source_fixture()
        with self.assertRaises(ValueError):collect(doc,g,'other','GRAPH')
        line.dxf.end=(50,0);r=collect(doc,g,'SRC','GRAPH')
        self.assertIsNone(r['records'][0]['nominal_mm']);self.assertEqual(r['counts']['graph_edges'],1)


if __name__=='__main__':unittest.main()
