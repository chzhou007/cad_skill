import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from source_comparison_gate import check, hidden_branch_screen_blockers


class HiddenBranchComparisonGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'reports').mkdir()
        self.graph=self.root/'graph.json';self.graph.write_text(json.dumps({'metadata':{'source_sha256':'SRC'},'nodes':[],'edges':[]}),encoding='utf8');self.graph_hash=hashlib.sha256(self.graph.read_bytes()).hexdigest()
        self.native=self.root/'pair.png';self.native.write_bytes(b'comparison');self.native_hash=hashlib.sha256(self.native.read_bytes()).hexdigest()
        self.candidate={'terminal':'U','branch_handle':'B','main_handle':'M','circle_handle':'C','status':'candidate_not_connectivity_proof'}
        self.screen=self.root/'reports'/'hidden-branch-circle-screen.json';self.screen.write_text(json.dumps({'source_sha256':'SRC','graph_sha256':self.graph_hash,'status':'candidates_not_connectivity_proof','candidates':[self.candidate],'ambiguous':[]}),encoding='utf8')
        self.receipt=self.root/'reports'/'hidden-branch-circle-screen-stage.json';self.receipt.write_text(json.dumps({'graph_sha256':self.graph_hash,'evidence_sha256':hashlib.sha256(self.screen.read_bytes()).hexdigest()}),encoding='utf8')
        self.report={'graph_sha256':self.graph_hash,'rounds_completed':1,'families':[{'id':'x','status':'resolved','source_handles':['B'],'disposition':'compared'}],'native_comparisons':[{'path':'pair.png','sha256':self.native_hash}]}
    def tearDown(self):self.tmp.cleanup()

    def test_unclassified_candidate_blocks_even_when_receipt_claims_done(self):
        r=check(self.report,self.graph_hash,self.root,self.graph)
        self.assertEqual(r['status'],'pending');self.assertEqual(len(r['hidden_branch_screen_blockers']),1)

    def test_disposition_requires_bound_evidence(self):
        x={k:self.candidate[k] for k in ('terminal','branch_handle','main_handle','circle_handle')};x.update(status='resolved',disposition='source comparison excludes it',evidence_path='pair.png',evidence_sha256=self.native_hash)
        self.report['hidden_branch_dispositions']=[x]
        self.assertEqual(hidden_branch_screen_blockers(self.root,self.graph_hash,'SRC',self.report),[])
        x['evidence_sha256']='wrong'
        with self.assertRaises(ValueError):hidden_branch_screen_blockers(self.root,self.graph_hash,'SRC',self.report)

    def test_stale_screen_and_missing_graph_fail_closed(self):
        with self.assertRaises(ValueError):hidden_branch_screen_blockers(self.root,'stale','SRC',self.report)
        self.graph.unlink();self.assertEqual(check(self.report,self.graph_hash,self.root)['status'],'failed')


if __name__=='__main__':unittest.main()
