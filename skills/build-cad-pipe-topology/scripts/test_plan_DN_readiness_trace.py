import copy,unittest
from plan_DN_readiness_trace import collect

class ReadinessTests(unittest.TestCase):
    def fixture(self):
        graph=dict(nodes=[dict(node_id=n,node_type='tee'if n=='T'else'equipment',floor=1)for n in ('T','A','B','C')],edges=[dict(edge_id=e,start_node_id='T',end_node_id=n,system='supply',attribute_paths=[[[0,0],[x,1]]])for e,n,x in [('U','A',1),('P','B',2),('Q','C',3)]])
        result=dict(source_sha256='a'*64,graph_sha256='b'*64,records=[dict(edge_id=e['edge_id'],system='supply',status='unresolved'if e['edge_id']=='U'else'annotation_blocked',nominal_mm=None,lineage=[],scope_paths=copy.deepcopy(e['attribute_paths']))for e in graph['edges']],roles={'T':dict(through=['P','Q'],branch='U',source_T_proof=dict(source_sha256='a'*64,graph_sha256='b'*64))},annotation_barriers={'P':[dict(reason='compound_or_named_DN_needs_its_native_scope',text_handle='LABEL')]})
        return graph,result
    def test_unknown_groups_report_source_barriers_without_assigning_values(self):
        g,r=self.fixture();before=copy.deepcopy((g,r));out=collect(g,r,1,'a'*64,'b'*64)
        self.assertEqual(out['counts']['unresolved_edges'],1);self.assertEqual(out['groups'][0]['primary_reason'],'source_annotation_scope_barrier');self.assertIsNone(out['groups'][0]['nominal_mm_assigned']);self.assertEqual((g,r),before)
    def test_checked_T_incidence_groups_unknown_siblings_but_not_across_equipment(self):
        g,r=self.fixture()
        for row in r['records']:row['status']='unresolved'
        self.assertEqual(collect(g,r,1,'a'*64,'b'*64)['counts']['trace_groups'],1)
        r['roles']={};g['nodes'][0]['node_type']='equipment'
        self.assertEqual(collect(g,r,1,'a'*64,'b'*64)['counts']['trace_groups'],3)
    def test_source_T_gap_is_separate_from_semantic_DN_question(self):
        g,r=self.fixture();r['roles']={};r['source_T_exceptions']={'T':'missing native ray'}
        out=collect(g,r,1,'a'*64,'b'*64);self.assertEqual(out['groups'][0]['primary_reason'],'source_T_evidence_missing');self.assertEqual(out['groups'][0]['missing_T_evidence'][0]['node_id'],'T')
    def test_distinct_main_DN_does_not_choose_a_branch_or_repeat_old_review(self):
        g,r=self.fixture()
        for row,value in zip(r['records'][1:],[450,200]):row.update(status='reviewed_plan_DN_scope'if value==450 else'direct_plan_DN',nominal_mm=value,lineage=[{'known':value}])
        out=collect(g,r,1,'a'*64,'b'*64);self.assertEqual(out['groups'][0]['primary_reason'],'DN_transition_branch_scope_unassigned');self.assertIsNone(out['groups'][0]['nominal_mm_assigned'])
    def test_stale_source_cross_service_and_wrong_floor_fail_closed(self):
        for kind in ('source','service','floor','value'):
            g,r=self.fixture()
            if kind=='source':r['roles']['T']['source_T_proof']['source_sha256']='c'*64
            if kind=='service':g['edges'][1]['system']='return';r['records'][1]['system']='return'
            if kind=='floor':g['nodes'][1]['floor']=2
            if kind=='value':r['records'][0]['nominal_mm']=100
            with self.subTest(kind=kind),self.assertRaises(ValueError):collect(g,r,1,'a'*64,'b'*64)
    def test_typed_non_node_boundaries_remain_non_nodes(self):
        g,r=self.fixture();e=g['edges'][0];e['end_node_id']=None;e['end_boundary_id']='BOUNDARY';e['endpoint_semantics']={'end':dict(kind='source_boundary',id='BOUNDARY')}
        self.assertEqual(collect(g,r,1,'a'*64,'b'*64)['counts']['unresolved_edges'],1)
        del e['endpoint_semantics']
        with self.assertRaisesRegex(ValueError,'untyped'):collect(g,r,1,'a'*64,'b'*64)
if __name__=='__main__':unittest.main()
