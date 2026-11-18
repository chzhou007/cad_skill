import copy,unittest
from compose_paired_plan_attribute_scope import append_scope,ROOT,BASIS


class PairedScopeCompositionTests(unittest.TestCase):
    def data(self):
        common=dict(nodes=[dict(node_id='A',node_type='tee',floor=2)],edges=[dict(edge_id=e,system='supply',attribute_paths=[[[0,0],[10,0]]],equipment_inventory=[dict(device_names=['V'])]) for e in ('H','OLD','NEW')],sourceNativeBlockBranchReconstruction=dict(records=['historical']))
        common['edges'][0]['cross_view_attributes']={'old_confirmed':True};base=copy.deepcopy(common);scope=copy.deepcopy(common)
        base['edges'][1]['cross_view_attributes']={'historical_value':123.45};base['sourceCheckedCrossViewAttributeFusion']={'records':['old']}
        scope['edges'][2]['cross_view_attributes']=dict(mapping_basis=BASIS,diameter={'plan_drawn_nominal_mm':200},whole_edge_physical_length_mm=None)
        scope['sourceCheckedCrossViewAttributeFusion']=dict(proof_type=BASIS,records=['new'],human_accepted=False)
        return base,common,scope
    def test_old_records_and_source_graph_are_retained_byte_for_byte(self):
        args=self.data();before=copy.deepcopy(args);out,audit=append_scope(*args,'S')
        self.assertEqual(args,before);self.assertEqual(out['edges'][:2],args[0]['edges'][:2]);self.assertEqual(out['sourceCheckedCrossViewAttributeFusion'],args[0]['sourceCheckedCrossViewAttributeFusion'])
        self.assertEqual(out['nodes'],args[0]['nodes']);self.assertEqual(out[ROOT]['added_axis_edges'],['NEW']);self.assertEqual(audit['prior_attribute_edges'],2)
        self.assertIsNone(out['edges'][2]['cross_view_attributes']['whole_edge_physical_length_mm']);self.assertFalse(out['metadata']['hil_ready'])
    def test_identity_geometry_component_and_source_root_changes_are_rejected(self):
        for mode in ('node','edge','geometry','component','source_root','common_attributes'):
            args=self.data();scope=args[2]
            if mode=='node':scope['nodes'][0]['floor']=3
            elif mode=='edge':scope['edges'].pop()
            elif mode=='geometry':scope['edges'][2]['attribute_paths']=[[[0,0],[11,0]]]
            elif mode=='component':scope['edges'][2]['equipment_inventory']=[]
            elif mode=='source_root':scope['sourceNativeBlockBranchReconstruction']={}
            else:scope['edges'][0]['cross_view_attributes']={}
            with self.assertRaises(ValueError):append_scope(*args,'S')
    def test_previously_published_writer_even_empty_is_never_overwritten(self):
        for value in ({},{'old':True}):
            args=self.data();args[0]['edges'][2]['cross_view_attributes']=value
            with self.assertRaisesRegex(ValueError,'overlaps'):append_scope(*args,'S')
    def test_unsupported_proof_and_duplicate_extension_fail_closed(self):
        args=self.data();args[2]['sourceCheckedCrossViewAttributeFusion']['proof_type']='legacy'
        with self.assertRaises(ValueError):append_scope(*args,'S')
        args=self.data();args[0][ROOT]={}
        with self.assertRaises(ValueError):append_scope(*args,'S')


if __name__=='__main__':unittest.main()
