import hashlib,json,tempfile,unittest
from pathlib import Path
from source_comparison_gate import verify_confirmed_sideview_stage,confirmed_sideview_source_handles

class ConfirmedSideviewStageGateTests(unittest.TestCase):
    def test_graph_claim_alone_does_not_classify_missing_source_lines(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'requires its native stage'):
                confirmed_sideview_source_handles(Path(folder),'G',{'confirmedSideviewCanonicalization':{}})
    def fixture(self,root):
        reports=root/'reports';reports.mkdir();directory=root/'topology-confirmed-sideviews';directory.mkdir()
        body=json.dumps({'script_sha256':'invented'}).encode('utf8')
        (reports/'sideview-canonicalization-audit.json').write_bytes(body)
        (directory/'sideview-canonicalization-audit.json').write_bytes(body)
        return reports,dict(artifact_directory=str(directory),status='source_pinned_confirmed_sideview_canonicalization',graph_sha256='G',hil_ready=False,audit_sha256=hashlib.sha256(body).hexdigest())
    def test_partial_declaration_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'reports').mkdir();(root/'reports/confirmed-sideview-stage.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'missing'):verify_confirmed_sideview_stage(root,'G')
    def test_stale_or_external_evidence_rejected(self):
        for field in ('graph','directory'):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);reports,stage=self.fixture(root)
                if field=='graph':stage['graph_sha256']='OLD'
                else:stage['artifact_directory']=str(root.parent)
                (reports/'confirmed-sideview-stage.json').write_text(json.dumps(stage))
                with self.assertRaisesRegex(ValueError,'unsafe or stale'):verify_confirmed_sideview_stage(root,'G')
    def test_matching_manifest_does_not_substitute_for_native_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);reports,stage=self.fixture(root)
            (reports/'confirmed-sideview-stage.json').write_text(json.dumps(stage))
            with self.assertRaisesRegex(ValueError,'implementation'):verify_confirmed_sideview_stage(root,'G')

if __name__=='__main__':unittest.main()
