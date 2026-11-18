import copy,unittest
import test_native_valve_display_stub_evidence as fixtures
from native_line_path_evidence import collect as lines,LAYERS
from native_segment_dn_candidates import collect as old_collect
from native_segment_dn_candidates_v2 import collect
from confirm_crossview_paths import encode


def fixture():
    doc,graph,stub=fixtures.fixture();pipe=doc.modelspace().add_line((230,310),(300,310),dxfattribs=dict(layer=LAYERS['return']))
    text=doc.modelspace().add_text('DN450',dxfattribs=dict(insert=(260,330),height=20,layer='AN'))
    graph['edges'].append(dict(edge_id='RISER',system='return',connection_mode='continuous_original_cad_pipe',attribute_paths=[[[230,310],[300,310]]]))
    line_policy=dict(source_sha256='S',graph_sha256='G',selections=[dict(edge_id='RISER',line_handles=[pipe.dxf.handle])])
    witness=lines(doc,graph,line_policy,'S','G');policy=dict(source_sha256='S',graph_sha256='G',line_evidence_sha256='L',text_layers=['AN'],
        selections=[dict(text_handle=text.dxf.handle,expected_text='DN450',edge_id='RISER',segment_index=0)],display_stub_policy=stub)
    return doc,graph,witness,policy,text


class QualifiedSegmentDNTests(unittest.TestCase):
    def test_historical_false_competitor_is_excluded_by_exact_native_stem_proof(self):
        doc,g,w,p,text=fixture();before=copy.deepcopy(g)
        with self.assertRaisesRegex(ValueError,'ambiguous'):old_collect(doc,g,w,p,'S','G','L')
        output=collect(doc,g,w,p,'S','G','L');self.assertEqual(g,before);self.assertEqual(len(output['observations']),1)
        self.assertEqual(output['observations'][0]['nominal_mm_candidate'],450);self.assertEqual(len(output['excluded_competing_source_chains']),1)
        self.assertTrue(output['original_native_document_unchanged']);self.assertFalse(output['physical_values_fused'])
        self.assertEqual(doc.entitydb[p['display_stub_policy']['selections'][0]['free_line_handle']].dxftype(),'LINE')
    def test_other_nested_pipe_competitors_in_same_block_remain_active(self):
        doc,g,w,p,text=fixture();doc.blocks['BODY'].add_line((50,15),(70,15),dxfattribs=dict(layer=LAYERS['return']))
        with self.assertRaisesRegex(ValueError,'ambiguous'):collect(doc,g,w,p,'S','G','L')
    def test_missing_qualification_or_real_contact_never_turns_into_a_whole_DN(self):
        for case in ('missing','invalid','connected'):
            doc,g,w,p,text=fixture()
            if case=='missing':p.pop('display_stub_policy')
            elif case=='invalid':p['display_stub_policy']['selections'][0]['expected_valve_name']='WRONG'
            else:doc.modelspace().add_line((270,300),(270,350),dxfattribs=dict(layer=LAYERS['supply']))
            with self.subTest(case=case),self.assertRaises(ValueError):collect(doc,g,w,p,'S','G','L')
    def test_no_exclusions_is_exactly_the_inherited_reader(self):
        doc,g,w,p,text=fixture();text.dxf.insert=(290,330);p.pop('display_stub_policy')
        self.assertEqual(encode(collect(doc,g,w,p,'S','G','L')),encode(old_collect(doc,g,w,p,'S','G','L')))
    def test_private_reader_does_not_change_global_nested_decomposition(self):
        import native_segment_dn_candidates as old
        original=old.recursive_decompose;doc,g,w,p,text=fixture();collect(doc,g,w,p,'S','G','L');self.assertIs(old.recursive_decompose,original)
    def test_old_source_binding_transform_and_withheld_guards_remain_in_force(self):
        for case in ('source','line_hash','text','transform','withheld'):
            doc,g,w,p,text=fixture()
            if case=='source':p['source_sha256']='OTHER'
            elif case=='line_hash':p['line_evidence_sha256']='OTHER'
            elif case=='text':p['selections'][0]['expected_text']='DN200'
            elif case=='transform':text.dxf.text_generation_flag=2
            else:p['withheld_candidates']=[dict(text_handle=text.dxf.handle,expected_text='DN450',reason='still pending')]
            with self.subTest(case=case),self.assertRaises(ValueError):collect(doc,g,w,p,'S','G','L')


if __name__=='__main__':unittest.main()
