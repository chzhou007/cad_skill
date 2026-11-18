import copy,unittest
from source_checked_plan_path_coverage import audit
from native_path_coverage_audit import audit as historical_audit
from native_plan_projection_lengths import lengths
from test_source_reviewed_circle_branch_evidence import HistoricalReviewedCircleTests


class ScopedPlanCoverageTests(unittest.TestCase):
    def fixture(self,crossover=True):
        helper=HistoricalReviewedCircleTests();self.addCleanup(helper.doCleanups)
        return helper.crossover_fixture() if crossover else helper.legacy_fixture()

    def test_single_path_retains_exact_historical_audit(self):
        doc,g,_=self.fixture(False);policy=dict(source_sha256='S',graph_sha256='G',edges=['B'])
        self.assertEqual(audit(doc,g,policy,'S','G'),historical_audit(doc,g,policy,'S','G'))

    def test_crossover_projection_counts_only_native_pipe_with_path_identity(self):
        doc,g,_=self.fixture();before=copy.deepcopy(g)
        coverage=audit(doc,g,dict(source_sha256='S',graph_sha256='G',edges=['B']),'S','G')
        metric=lengths(g,coverage,dict(plan_edges=['B'],system='supply'),dict(plan_window=[-20,20,-20,20]))
        self.assertEqual(metric['value_mm'],6);self.assertEqual([p['path_index'] for p in metric['pieces']],[0,1])
        self.assertIsNone(metric['installed_whole_edge_length_mm']);self.assertIsNone(metric['unshown_connection_length_mm'])
        self.assertEqual(g,before)

    def test_unproved_multi_path_plain_crossing_and_invalid_source_are_rejected(self):
        for kind in ('unreviewed','missing_gap','wrong_crossing','duplicate','hash'):
            doc,g,_=self.fixture();policy=dict(source_sha256='S',graph_sha256='G',edges=['B'])
            if kind=='unreviewed':g['nodes'][0].pop('source_reviewed_circle')
            elif kind=='missing_gap':g['edges'][0]['source_normalized_crossovers']=[]
            elif kind=='wrong_crossing':g['edges'][0]['source_normalized_crossovers'][0]['crossings'][0]['crossed_source_system']='supply'
            elif kind=='duplicate':
                e=doc.entitydb[g['edges'][0]['source_handles'][0]];doc.modelspace().add_line(e.dxf.start,e.dxf.end,dxfattribs={'layer':e.dxf.layer})
            else:policy['graph_sha256']='BAD'
            with self.assertRaises(ValueError):audit(doc,g,policy,'S','G')

    def test_multi_path_metric_requires_replayed_scope_and_valid_indices(self):
        for kind in ('scope','proof','index','duplicate'):
            doc,g,_=self.fixture();coverage=audit(doc,g,dict(source_sha256='S',graph_sha256='G',edges=['B']),'S','G');row=coverage['edges'][0]
            if kind=='scope':row.pop('coverage_mode')
            elif kind=='proof':row['source_path_evidence']['crossovers']=[]
            elif kind=='index':row['segments'][0]['path_index']=True
            else:row['segments'].append(copy.deepcopy(row['segments'][0]))
            with self.assertRaises(ValueError):lengths(g,coverage,dict(plan_edges=['B'],system='supply'),dict(plan_window=[-20,20,-20,20]))


if __name__=='__main__':unittest.main()
