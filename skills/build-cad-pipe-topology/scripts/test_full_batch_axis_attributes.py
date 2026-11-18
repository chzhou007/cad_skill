import copy,unittest
from full_batch_axis_attribute_composition import append,restore,ROOT,FIELD
from native_exploded_caption_identity import apply_aliases
from match_source_checked_crossview_paths import selected_snapshot


def fixture(count=1):
    nodes=[dict(node_id='T'+str(i),node_type='tee',floor=1,x=10*i,y=0)for i in range(count+1)]
    edges=[dict(edge_id='E'+str(i),start_node_id='T'+str(i),end_node_id='T'+str(i+1),system='supply',
        start_floor=1,end_floor=1,attribute_paths=[[[10*i,0],[10*(i+1),0]]],source_handles=['L'+str(i)])for i in range(count)]
    raw=dict(nodes=nodes,edges=edges,metadata=dict(source_sha256='source'),derivedEvidenceInvalidation=dict(reason='prior'))
    parent=copy.deepcopy(raw);parent['edges'][0]['cross_view_attributes']=dict(prior='preserved')
    axis=copy.deepcopy(raw);axis.update(sourceExplodedCaptionIdentity=dict(aliases={}),derivedEvidenceInvalidation=dict(reason='identity'))
    plan=copy.deepcopy(raw);ids=[e['edge_id']for e in edges]
    row=dict(mapping_id='M',kind='same_floor_T_to_T_main'if count==1 else'native_main_chain_between_independent_junctions',floor=1,system='supply',
        plan_edges=ids,iso_edges=ids,plan_start='T0',plan_end='T'+str(count),iso_start='T0',iso_end='T'+str(count),
        plan_snapshot=selected_snapshot(plan,ids),iso_snapshot=selected_snapshot(axis,ids))
    metric=dict(value_mm=10*count,status='native_plan_horizontal_projection_partial_length',
        pieces=[dict(plan_edge=eid,path_index=0,segment_index=0,length_mm=10)for eid in ids])
    batch=dict(identity_graph_sha256='identity',floors={'1':dict(records=[row])},metrics={'1':[dict(mapping_id='M',projection=metric)]})
    DN=dict(floors={'1':dict(graph_sha256='plan',records=[dict(edge_id=eid,system='supply',nominal_mm=100,human_accepted=False,scope_paths=edges[i]['attribute_paths'])for i,eid in enumerate(ids)])})
    hashes=dict(identity_graph='identity',plan_graphs={'1':'plan'},plan_sources={'1':'plan-source'},axis_source='source',mapping_receipt='mapping',DN_receipt='DN')
    return parent,raw,axis,{},batch,{'1':plan},DN,{},[0,45,135],hashes


class Tests(unittest.TestCase):
    def test_one_to_one_main_is_source_scoped_and_entire_old_parent_is_restorable(self):
        args=fixture();before=copy.deepcopy(args[0]);g=append(*args);r=g['edges'][0][FIELD]
        self.assertEqual(r['whole_axis_nominal_mm'],100);self.assertEqual(r['complete_horizontal_centerline_route_mm'],10)
        self.assertIsNone(r['whole_installed_length_mm']);self.assertFalse(r['human_accepted'])
        self.assertEqual(restore(g,before),before);self.assertEqual(args[0],before)
    def test_many_to_many_group_does_not_allocate_route_total_or_whole_DN_to_children(self):
        args=fixture(2);g=append(*args)
        for e in g['edges']:
            r=e[FIELD];self.assertTrue(r['group_scope_not_allocated_to_child_edges'])
            self.assertIsNone(r['whole_axis_nominal_mm']);self.assertIsNone(r['complete_horizontal_centerline_route_mm'])
            self.assertEqual(r['horizontal_projection']['value_mm'],20)
        self.assertEqual(len(g[ROOT]['records']),1)
    def test_equipment_or_mixed_scope_cannot_become_a_whole_horizontal_main(self):
        args=list(fixture());args[4]['floors']['1']['records'][0]['kind']='equipment_branch'
        r=append(*args)['edges'][0][FIELD]
        self.assertEqual(r['plan_drawn_nominal_mm'],100);self.assertIsNone(r['whole_axis_nominal_mm']);self.assertIsNone(r['complete_horizontal_centerline_route_mm'])
    def test_current_unknown_keeps_original_values_but_does_not_select_them_as_current(self):
        args=list(fixture());args[6]['floors']['1']['records'][0]['nominal_mm']=None;g=append(*args)
        self.assertIsNone(g['edges'][0][FIELD]['plan_drawn_nominal_mm']);self.assertEqual(g['edges'][0]['cross_view_attributes'],dict(prior='preserved'))
    def test_changed_snapshot_system_duplicate_writer_or_metric_repetition_is_rejected(self):
        for case in ['snapshot','system','writer','metric']:
            args=list(fixture())
            if case=='snapshot':args[4]['floors']['1']['records'][0]['iso_snapshot']['edges'][0]['system']='return'
            if case=='system':args[6]['floors']['1']['records'][0]['system']='return'
            if case=='writer':args[4]['floors']['1']['records'].append(copy.deepcopy(args[4]['floors']['1']['records'][0]))
            if case=='metric':args[4]['metrics']['1'][0]['projection']['pieces']*=2
            with self.subTest(case=case),self.assertRaises(ValueError):append(*args)
    def test_root_or_edge_tampering_and_old_geometry_changes_fail_restoration(self):
        args=list(fixture());g=append(*args);g['edges'][0][FIELD]['plan_drawn_nominal_mm']=200
        with self.assertRaises(ValueError):restore(g,args[0])
        args[0]['edges'][0]['attribute_paths'][0][-1]=[20,0]
        with self.assertRaises(ValueError):append(*args)


if __name__=='__main__':unittest.main()
