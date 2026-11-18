import copy,unittest
from unittest.mock import patch
from test_full_plan_DN_inheritance import fixture
from current_junction_plan_DN import collect,annotation_equal,reviewed_seeds,preserve_known

class CurrentT(unittest.TestCase):
    def test_collector_reuses_preexisting_confirmed_corner_main_roles(self):
        from test_source_main_DN_continuity import Tests as OriginalCornerTests
        fixture=OriginalCornerTests();self.addCleanup(fixture.doCleanups)
        graph,nid,proof,record=fixture.native_corner();graph['metadata']={'source_sha256':'S'}
        ann=dict(seeds=[dict(edge_id=e,nominal_mm=v,evidence_id='source:'+e)for e,v in [('M',200),('BR',80)]],blocked_edges={})
        old=dict(source_sha256='S',graph_sha256='G',annotation_evidence=copy.deepcopy(ann),direct_seed_evidence=ann['seeds'],roles={},
                 records=[dict(edge_id=e['edge_id'],nominal_mm={'M':200,'BR':80}.get(e['edge_id']))for e in graph['edges']])
        path=dict(edges=[dict(segments=[dict(status='single_source_line_covers')])])
        def reader(document,current,node,*hashes):
            if node!=nid:raise ValueError('fixture endpoint is not a proved three-arm T')
            return proof
        with patch('current_junction_plan_DN.inventory',return_value=ann),patch('current_junction_plan_DN.coverage',return_value=path),patch('current_junction_plan_DN.barriers',return_value=({},[])):
            result=collect(None,graph,old,'S','G',reader,{})
        values={r['edge_id']:r['nominal_mm']for r in result['records']}
        self.assertEqual([values[e]for e in record['main_child_edges']],[200,200]);self.assertEqual(values['BR'],80)
        self.assertEqual(result['counts']['original_main_continuity_roles'],1)

    def run_scope(self,seeds,reader_error=False,bad_path=None):
        graph,proof=fixture();graph['metadata']={'source_sha256':'s'}
        ann=dict(seeds=[dict(edge_id=e,nominal_mm=v,evidence_id='source:'+e)for e,v in seeds],blocked_edges={})
        old=dict(source_sha256='s',graph_sha256='g',annotation_evidence=copy.deepcopy(ann),direct_seed_evidence=ann['seeds'],roles={},
                 records=[dict(edge_id=e,nominal_mm=dict(seeds).get(e))for e in('A','B','C')])
        def path(doc,g,eids,sh,gh):return dict(edges=[dict(segments=[dict(status='missing'if eids[0]==bad_path else'single_source_line_covers')])])
        def reader(*args):
            if reader_error:raise ValueError('unproved native current T')
            return proof['T']
        with patch('current_junction_plan_DN.inventory',return_value=ann),patch('current_junction_plan_DN.coverage',side_effect=path),patch('current_junction_plan_DN.barriers',return_value=({},[])):
            return collect(None,graph,old,'s','g',reader,{})
    def test_current_native_T_dispatch_reuses_original_through_and_branch_rules(self):
        result=self.run_scope([('A',300)]);self.assertEqual([x['nominal_mm']for x in result['records']],[300,300,300])
        self.assertEqual(result['counts']['new_known_DN'],2);self.assertFalse(result['axis_values_used_to_choose_DN'])
    def test_native_T_failure_or_missing_through_path_leaves_unknown(self):
        for kw in(dict(reader_error=True),dict(bad_path='B')):
            result=self.run_scope([('A',300)],**kw);c=next(x for x in result['records']if x['edge_id']=='C');self.assertIsNone(c['nominal_mm'])
    def test_new_branch_annotation_and_through_conflict_stay_boundaries(self):
        result=self.run_scope([('A',300),('C',80)]);self.assertEqual([x['nominal_mm']for x in result['records']],[300,300,80])
        result=self.run_scope([('A',300),('B',200)]);c=next(x for x in result['records']if x['edge_id']=='C');self.assertIsNone(c['nominal_mm']);self.assertEqual(c['status'],'conflict')
    def test_changed_annotations_reviewed_extent_or_old_known_value_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'annotation evidence changed'):annotation_equal({'seeds':[150]},{'seeds':[100]})
        with self.assertRaisesRegex(ValueError,'known local plan DN changed'):preserve_known({'records':[dict(edge_id='A',nominal_mm=100)]},[dict(edge_id='A',nominal_mm=150)])
        seed=dict(edge_id='A',nominal_mm=100,evidence_id='reviewed:A',scope_only=True,source_kind='explicit_reviewed_drawn_plan_scope_not_new_annotation',scope_paths=[[[0,0],[1,0]]])
        graph={'edges':[dict(edge_id='A',attribute_paths=[[[0,0],[2,0]]])]}
        with self.assertRaisesRegex(ValueError,'scope changed'):reviewed_seeds({'direct_seed_evidence':[seed]},{'seeds':[]},graph,{'A'})

if __name__=='__main__':unittest.main()
