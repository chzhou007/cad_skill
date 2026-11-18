import copy,unittest
from axis_vertical_DN_batch import projection,recursive_qualification,consolidate
def scope(edge='E',pi=0,si=0,kind='vertical',status='single_source_line_covers'):
    return dict(edge_id=edge,path_index=pi,segment_index=si,system='supply',floor_start=3,floor_end=3,scope_points=[[0,pi*100],[0,pi*100+10]],direction_class=kind,native_source_status=status,native_witnesses=[dict(scope='modelspace',source_handle='L'+str(pi))]if status=='single_source_line_covers'else[])
class Tests(unittest.TestCase):
    def test_multipath_edges_keep_original_path_segment_identity_in_private_single_path_scope(self):
        g=dict(metadata=dict(source_sha256='s'),nodes=[],edges=[dict(edge_id='E',system='supply',source_insert_handle='ROOT',attribute_paths=[[[0,0],[0,10]],[[0,100],[0,110]]])]);r=dict(inputs=dict(source=dict(sha256='s')),records=[scope(),scope(pi=1)]);before=copy.deepcopy(g);private,index,witness,h=projection(g,r)
        self.assertEqual(g,before);self.assertEqual(len(private['edges']),2);self.assertTrue(all(len(e['attribute_paths'])==1 for e in private['edges']));self.assertEqual({r['path_index']for r in index.values()},{0,1});self.assertTrue(all(n['node_type']=='read_only_attribute_cut_not_physical_node'for n in private['nodes']));self.assertEqual(len(witness['edges']),2);self.assertEqual(len(h),64)
    def test_one_unqualified_target_does_not_discard_other_independent_native_results(self):
        def reader(handles):
            if 'bad'in handles:raise ValueError('independent native source proof missing')
            return list(handles)
        result=recursive_qualification(['A','B','bad','C'],reader);self.assertEqual({h for p in result if p['status']=='passed'for h in p['handles']},{'A','B','C'});self.assertEqual([h for p in result if p['status']=='pending'for h in p['handles']],['bad'])
    def test_local_vertical_values_never_promote_horizontal_whole_edge_or_length(self):
        route=dict(records=[scope(),scope(edge='H',kind='horizontal')]);obs=[dict(edge_id='E',path_index=0,segment_index=0,nominal_mm=80)];before=copy.deepcopy(route);rows,pending=consolidate(route,obs,{})
        self.assertEqual(route,before);self.assertEqual(len(rows),1);self.assertFalse(pending);self.assertEqual(rows[0]['nominal_mm'],80);self.assertFalse(rows[0]['whole_edge_DN_assigned']);self.assertIsNone(rows[0]['physical_length_mm']);self.assertEqual(rows[0]['source'],'axis_11_native_annotation_even_same_floor')
    def test_conflicting_dn_annotations_and_missing_source_keep_explicit_evidence(self):
        route=dict(records=[scope()]);obs=[dict(edge_id='E',path_index=0,segment_index=0,nominal_mm=v)for v in(80,65)];rows,pending=consolidate(route,obs,{});self.assertFalse(rows);self.assertEqual(len(pending[0]['observations']),2);self.assertIn('transition',pending[0]['reason'])
        route=dict(records=[scope(status='no_witness_in_scoped_search')]);rows,pending=consolidate(route,obs[:1],{});self.assertFalse(rows);self.assertIn('not_yet_witnessed',pending[0]['reason'])
    def test_unparsed_or_ambiguous_annotations_and_zero_values_do_not_become_known_dn(self):
        route=dict(records=[scope()]);obs=[dict(edge_id='E',path_index=0,segment_index=0,nominal_mm=80)];rows,pending=consolidate(route,obs,{('E',0,0):'unparsed_native_DN'});self.assertFalse(rows);self.assertEqual(pending[0]['reason'],'unparsed_native_DN')
        obs[0]['nominal_mm']=0;rows,pending=consolidate(route,obs,{});self.assertFalse(rows);self.assertEqual(pending[0]['reason'],'invalid_native_DN_value')
if __name__=='__main__':unittest.main()
