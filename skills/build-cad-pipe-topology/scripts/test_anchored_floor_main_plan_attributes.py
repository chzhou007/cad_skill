import copy,unittest
from test_native_inline_joint_path_coverage import fixture
from native_inline_joint_path_coverage import collect
from anchored_floor_main_plan_attributes import inline_projection,preserve_known_main_values,frontier_annotation_domain

class Tests(unittest.TestCase):
    def test_frontier_reads_only_T_contiguous_pipe_and_rejects_seed_across_joint(self):
        graph=dict(nodes=[dict(node_id='T',x=0,y=0),dict(node_id='UT',x=100,y=0)],edges=[dict(edge_id='E',start_node_id='T',end_node_id='UT',attribute_paths=[[[0,0],[40,0]],[[60,0],[100,0]]])])
        observation=dict(edge_id='E',kind='native_scalar',source_evidence=dict(graph_projection=[20,0]));before=copy.deepcopy(graph)
        private,proof=frontier_annotation_domain(graph,'E',{'T'},[observation])
        self.assertEqual(graph,before);self.assertEqual(private['edges'][0]['attribute_paths'],[[[0,0],[40,0]]])
        self.assertEqual(proof['excluded_original_path_indices'],[1]);self.assertFalse(proof['whole_frontier_DN_verified'])
        observation['source_evidence']['graph_projection']=[80,0]
        with self.assertRaisesRegex(ValueError,'unverified frontier span'):frontier_annotation_domain(graph,'E',{'T'},[observation])
        observation['source_evidence']['graph_projection']=[20,0];graph['edges'][0]['attribute_paths'].append([[0,0],[0,20]])
        with self.assertRaisesRegex(ValueError,'unique T-contiguous'):frontier_annotation_domain(graph,'E',{'T'},[observation])
    def test_pipe_only_metric_reuses_original_indices_and_never_adds_joint_span(self):
        for encoded in (False,True):
            with self.subTest(encoded=encoded):
                args=fixture(90,True,encoded);graph=args[1];proof=collect(*args)['records'][0];before=copy.deepcopy(graph)
                record=dict(plan_edges=[proof['edge_id']],system='supply')
                metric=inline_projection(graph,proof,record,dict(plan_window=[0,500,0,500]))
                self.assertEqual(graph,before);self.assertEqual(metric['value_mm'],40);self.assertIsNone(metric['inline_joint_interior_length_mm'])
                self.assertFalse(metric['joint_graphic_spans_added']);self.assertEqual(len(metric['pieces']),2)
                self.assertEqual({p['path_index'] for p in metric['pieces']},{0} if encoded else {0,1})
    def test_stale_path_missing_witness_window_or_unqualified_gap_blocks(self):
        for case in ('path','witness','window','gap'):
            with self.subTest(case=case):
                args=fixture(encoded=True);graph=args[1];proof=collect(*args)['records'][0];record=dict(plan_edges=[proof['edge_id']],system='supply');units=dict(plan_window=[0,500,0,500])
                if case=='path':proof['original_attribute_paths'][0][0][0]-=1
                elif case=='witness':proof['native_path_proofs'][0]['coverage']['edges'][0]['segments'][0]['witnesses']=[]
                elif case=='window':units['plan_window']=[0,10,0,10]
                else:proof['native_path_proofs'][0]['coverage']['edges'][0]['segments'][0]['status']='no_witness_in_scoped_search'
                with self.assertRaises(ValueError):inline_projection(graph,proof,record,units)
    def test_old_main_DN_and_metric_both_have_equal_priority(self):
        snapshot=dict(edges=[dict(cross_view_attributes=dict(floor=1,mapping_kind='main_between_equipment_branches',plan_edges=['P'],diameter=dict(plan_drawn_nominal_mm=200),horizontal_projection=dict(value_mm=1000)))])
        current=[dict(plan_edges=['P'],diameter=dict(nominal_mm=200),horizontal_projection=dict(value_mm=1000))]
        self.assertEqual(len(preserve_known_main_values(snapshot,current,1)),1)
        for case in ('DN','length','missing'):
            changed=copy.deepcopy(current)
            if case=='DN':changed[0]['diameter']['nominal_mm']=None
            elif case=='length':changed[0]['horizontal_projection']['value_mm']=1001
            else:changed=[]
            with self.subTest(case=case),self.assertRaisesRegex(ValueError,'previously known'):preserve_known_main_values(snapshot,changed,1)
    def test_named_main_is_protected_alongside_old_corridor_main(self):
        snapshot=dict(edges=[dict(plan_segment_attributes=[dict(floor=1,whole_local_edge=True,plan_edges=['NAMED'],nominal_mm=300,horizontal_projection=dict(value_mm=1200))])])
        rows=[dict(plan_edges=['NAMED'],diameter=dict(nominal_mm=300),horizontal_projection=dict(value_mm=1200))]
        self.assertTrue(preserve_known_main_values(snapshot,rows,1)[0]['current_values_identical'])
        rows[0]['horizontal_projection']['value_mm']=0
        with self.assertRaises(ValueError):preserve_known_main_values(snapshot,rows,1)
if __name__=='__main__':unittest.main()
