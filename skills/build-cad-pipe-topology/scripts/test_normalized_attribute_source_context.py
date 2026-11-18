import copy,tempfile,unittest
from test_normalized_native_junction_evidence import case
from axis_unbranched_vertical_DN import native_items
from normalized_attribute_source_context import prepare

def fixture(folder,**kw):
    doc,g,line,audit=case(folder,**kw);g['metadata']=dict(source_sha256='S')
    route=dict(inputs=dict(source=dict(sha256='S'),graph=dict(sha256='G')),records=[dict(edge_id='B',path_index=0,segment_index=0,
        system='supply',direction_class='vertical',scope_points=[[0,0],[0,100]],native_source_status='no_witness_in_scoped_search',native_witnesses=[])])
    return doc,g,line,audit,route,native_items(doc,g)

class NormalizedAttributeSourceTests(unittest.TestCase):
    def test_private_reader_schema_retains_raw_gap_and_changes_no_source(self):
        with tempfile.TemporaryDirectory()as folder:
            doc,g,line,audit,route,items=fixture(folder);before=copy.deepcopy((g,route,items));raw=list(line.dxf.start)
            source,private_route,private_items,proof=prepare(doc,g,route,items,'S','G',audit,'T','B')
            self.assertEqual((g,route,items),before);self.assertEqual(list(line.dxf.start),raw)
            self.assertEqual(private_route['records'][0]['native_source_status'],'single_source_line_covers')
            self.assertTrue(private_route['records'][0]['private_reader_schema_only']);self.assertTrue(proof['raw_source_coverage_unchanged'])
            self.assertIsNone(proof['physical_gap_length_mm']);self.assertEqual(proof['physical_lengths_assigned'],0)
            self.assertAlmostEqual(source.entitydb[line.dxf.handle].dxf.start.y,0,places=12)
            projected=next(x for x in private_items if x['child_handle']==line.dxf.handle)
            self.assertEqual(projected['raw_native_XYZ'][0],raw);self.assertIn('semantic_normalization_evidence',projected)

    def test_original_limit_Z_competitors_and_ambiguous_scope_are_not_relaxed(self):
        for defect in('long','Z','extra','ambiguous','wrong_source','changed_item'):
            with tempfile.TemporaryDirectory()as folder:
                kw=dict(gap=4)if defect=='long'else dict(z=5)if defect=='Z'else{}
                doc,g,line,audit,route,items=fixture(folder,**kw)
                if defect=='extra':doc.modelspace().add_line((0,-10),(0,0),dxfattribs={'layer':line.dxf.layer})
                elif defect=='ambiguous':route['records'][0]['native_source_status']='multiple_source_lines_cover'
                elif defect=='wrong_source':route['inputs']['source']['sha256']='OTHER'
                elif defect=='changed_item':next(x for x in items if x['child_handle']==line.dxf.handle)['XYZ'][0][1]+=1
                with self.subTest(defect=defect),self.assertRaises(ValueError):prepare(doc,g,route,items,'S','G',audit,'T','B')
if __name__=='__main__':unittest.main()
