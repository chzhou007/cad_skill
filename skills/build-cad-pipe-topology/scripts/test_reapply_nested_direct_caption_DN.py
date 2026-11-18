import copy,unittest
from reapply_nested_direct_caption_DN import compose
from test_native_nested_direct_caption_DN import scene
from test_axis_unbranched_vertical_DN import fixture

def parent(handles,targets):
    return dict(pair_qualification=dict(unmatched_target_text_handles=handles),pending=targets,counts=dict(current_known=0))

def waiting(si,reason='no_qualified_axis_annotation_on_this_vertical_segment'):
    return dict(edge_id='E',path_index=0,segment_index=si,original_reason=reason)

class CompositionTests(unittest.TestCase):
    def test_direct_adoption_only_replaces_its_actual_unresolved_source_scope(self):
        doc,g,r,hs,sh,gh=scene();p=parent(hs,[waiting(0,'repeated native DN layout does not identify one source branch')]);before=copy.deepcopy((g,r,p));v=compose(doc,g,r,p,sh,gh)
        self.assertEqual(v['counts']['new_known'],1);self.assertEqual(v['counts']['remaining_unknown'],0);self.assertEqual((g,r,p),before);self.assertEqual(v['physical_lengths_assigned'],0)
        p['pending'][0]['original_reason']='source_ambiguity'
        with self.assertRaisesRegex(ValueError,'overwrite'):compose(doc,g,r,p,sh,gh)

    def test_actual_direct_owner_seeds_original_bends_after_complete_projection(self):
        doc,g,_,r,ann,sh,gh=fixture();r['inputs']=dict(source=dict(sha256=sh),graph=dict(sha256=gh))
        for s in r['records']:s['native_witnesses'][0]['layer']='空调冷冻水供水'
        hs=[ann['records'][0]['observations'][0]['source_text']['handle']];p=parent(hs,[waiting(2,'repeated native DN layout does not identify one source branch'),waiting(0)]);before=copy.deepcopy((g,r,p));v=compose(doc,g,r,p,sh,gh)
        self.assertEqual(v['counts']['new_direct'],1);self.assertEqual(v['counts']['new_continuity'],1);self.assertEqual(v['counts']['current_known'],2);self.assertEqual((g,r,p),before)
        for row in v['records']:self.assertIsNone(row['physical_length_mm']);self.assertFalse(row['whole_edge_DN_assigned'])

    def test_real_T_and_unowned_new_DN_retain_pending_target(self):
        for kind in('T','DN'):
            doc,g,_,r,ann,sh,gh=fixture();r['inputs']=dict(source=dict(sha256=sh),graph=dict(sha256=gh))
            for s in r['records']:s['native_witnesses'][0]['layer']='空调冷冻水供水'
            if kind=='T':doc.modelspace().add_line((100,150),(120,150),dxfattribs={'layer':'空调冷冻水供水'})
            else:doc.modelspace().add_text('DN65',dxfattribs={'insert':(103,180),'height':10,'rotation':90})
            hs=[ann['records'][0]['observations'][0]['source_text']['handle']];v=compose(doc,g,r,parent(hs,[waiting(2,'repeated native DN layout does not identify one source branch'),waiting(0)]),sh,gh)
            self.assertEqual(v['counts']['new_direct'],1);self.assertEqual(v['counts']['new_continuity'],0);self.assertEqual(v['counts']['remaining_unknown'],1)

if __name__=='__main__':unittest.main()
