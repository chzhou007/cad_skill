import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from source_comparison_gate import check,check_paired_attribute_graph


class PairedAttributeGateTests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder);parent=root/'base';parent.mkdir();pg=parent/'graph_with_edges.json';pg.write_text('{}')
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();old=dict(graph_sha256=sha(pg),status='pending',errors=[],pending=['old datum issue'],hil_ready=False)
        cache=parent/'source-comparison-gate.json';cache.write_text(json.dumps(old),encoding='utf8')
        child=root/'child';child.mkdir();graph=child/'graph_with_edges.json';graph.write_text(json.dumps(dict(pairedServiceCrossViewAttributeFusion={'new':True},sourceCheckedCrossViewAttributeFusion={'old':True})))
        audit=dict(output_graph_sha256=sha(graph),parent_graph=dict(path=str(pg),sha256=sha(pg)),all_prior_attribute_values_preserved=True,
            old_nodes_edges_source_roots_and_components_preserved=True,records=[{'mapping_id':'NEW'}],added_axis_edges=['E'],
            plan_DN_scope_fusion=[dict(plan_drawn_nominal_mm=200,whole_main_DN_and_centerline_route=True)])
        return child,graph,pg,cache,old,audit,sha
    def test_native_extension_retains_every_prior_issue_and_hil_remains_invalidated(self):
        with tempfile.TemporaryDirectory() as folder:
            root,graph,pg,cache,old,audit,sha=self.fixture(folder)
            with patch('compose_paired_plan_attribute_scope.verify_output',return_value=audit):result=check_paired_attribute_graph(root,old,sha(graph),graph)
            self.assertIn('old datum issue',result['pending']);self.assertFalse(result['hil_ready']);self.assertEqual(result['paired_plan_attribute_stage']['plan_drawn_DN_edges'],1)
            self.assertTrue(result['paired_plan_attribute_stage']['original_issues_retained'])
    def test_paired_stage_runs_before_inherited_attribute_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            root,graph,pg,cache,old,audit,sha=self.fixture(folder)
            with patch('compose_paired_plan_attribute_scope.verify_output',side_effect=ValueError('bad native extension')),patch('source_comparison_gate.check_source_checked_attribute_graph') as wrong:
                result=check(old,sha(graph),root,graph)
            self.assertEqual(result['status'],'failed');self.assertIn('bad native extension',result['errors'][0]);wrong.assert_not_called()
    def test_missing_cache_changed_base_or_unmatched_context_fails_closed(self):
        for mode in ('missing','base','context','preservation','cached_hash'):
            with tempfile.TemporaryDirectory() as folder:
                root,graph,pg,cache,old,audit,sha=self.fixture(folder)
                if mode=='missing':cache.unlink()
                elif mode=='base':pg.write_text('{"changed":true}')
                elif mode=='context':old=dict(old,pending=[])
                elif mode=='preservation':audit['all_prior_attribute_values_preserved']=False
                else:cache.write_text(json.dumps(dict(old,graph_sha256='OTHER')),encoding='utf8')
                with patch('compose_paired_plan_attribute_scope.verify_output',return_value=audit):
                    with self.assertRaises((ValueError,OSError)):check_paired_attribute_graph(root,old,sha(graph),graph)
    def test_existing_errors_are_never_cleared(self):
        with tempfile.TemporaryDirectory() as folder:
            root,graph,pg,cache,old,audit,sha=self.fixture(folder);old['errors']=['original source error'];cache.write_text(json.dumps(old),encoding='utf8')
            with patch('compose_paired_plan_attribute_scope.verify_output',return_value=audit):r=check_paired_attribute_graph(root,old,sha(graph),graph)
            self.assertEqual(r['status'],'failed');self.assertEqual(r['errors'],old['errors'])


if __name__=='__main__':unittest.main()
