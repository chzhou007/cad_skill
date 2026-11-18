import copy,unittest
import test_compose_paired_plan_attribute_scope as fixtures
from compose_refined_paired_plan_attributes import append_scope,ROOT,BASIS


class RefinedPairedCompositionTests(unittest.TestCase):
    def data(self):
        args=fixtures.PairedScopeCompositionTests().data();scope=args[2]
        scope['edges'][2]['cross_view_attributes']['mapping_basis']=BASIS
        scope['edges'][2]['cross_view_attributes']['mapping_kind']='main_between_matched_junctions'
        scope['sourceCheckedCrossViewAttributeFusion']['proof_type']=BASIS
        return args
    def test_nonpaired_history_components_and_actual_junction_kind_are_retained(self):
        args=self.data();before=copy.deepcopy(args);out,audit=append_scope(*args,'S')
        self.assertEqual(args,before);self.assertEqual(out['edges'][:2],args[0]['edges'][:2]);self.assertEqual(out['nodes'],args[0]['nodes'])
        self.assertEqual(out['sourceCheckedCrossViewAttributeFusion'],args[0]['sourceCheckedCrossViewAttributeFusion'])
        self.assertEqual(out[ROOT]['added_axis_edges'],['NEW']);self.assertEqual(out['edges'][2]['cross_view_attributes']['mapping_kind'],'main_between_matched_junctions')
        self.assertTrue(audit['coarse_paired_child_not_added']);self.assertFalse(audit['related_prior_HIL_confirmation_inherited']);self.assertFalse(out['metadata']['hil_ready'])
    def test_coarse_and_refined_children_are_replacements_never_two_writers(self):
        for key in ('pairedServiceCrossViewAttributeFusion',ROOT):
            for index in (0,2):
                args=self.data();args[index][key]={}
                with self.subTest(key=key,index=index),self.assertRaisesRegex(ValueError,'replaces'):append_scope(*args,'S')
    def test_same_counts_do_not_excuse_wrong_identity_geometry_or_component(self):
        for case in ('node','id','path','component','root','common_attribute'):
            args=self.data();scope=args[2]
            if case=='node':scope['nodes'][0]['floor']=3
            elif case=='id':scope['edges'][2]['edge_id']='WRONG'
            elif case=='path':scope['edges'][2]['attribute_paths'][0][-1][0]+=1
            elif case=='component':scope['edges'][2]['equipment_inventory']=[]
            elif case=='root':scope['sourceNativeBlockBranchReconstruction']={}
            else:scope['edges'][0]['cross_view_attributes']={}
            with self.subTest(case=case),self.assertRaises(ValueError):append_scope(*args,'S')
    def test_inherited_or_unknown_writer_cannot_be_silently_replaced(self):
        for case in ('occupied','proof','empty'):
            args=self.data()
            if case=='occupied':args[0]['edges'][2]['cross_view_attributes']={}
            elif case=='proof':args[2]['sourceCheckedCrossViewAttributeFusion']['proof_type']='old'
            else:args[2]['edges'][2].pop('cross_view_attributes')
            with self.subTest(case=case),self.assertRaises(ValueError):append_scope(*args,'S')


if __name__=='__main__':unittest.main()
