import hashlib,json,tempfile,unittest
from pathlib import Path
from source_comparison_gate import verify_batch_circle_stage


class BatchCircleStageGateTest(unittest.TestCase):
    def fixture(self,root):
        reports=root/'reports';reports.mkdir();directory=root/'topology-batch-confirmed-circles';directory.mkdir()
        body=json.dumps({'script_sha256':'invented'}).encode('utf8')
        (reports/'batch-confirmed-circle-audit.json').write_bytes(body)
        (directory/'batch-confirmed-circle-audit.json').write_bytes(body)
        stage=dict(artifact_directory=str(directory),status='source_pinned_batch_circle_reconstruction',graph_sha256='G',hil_ready=False,audit_sha256=hashlib.sha256(body).hexdigest())
        return reports,stage
    def test_present_stage_needs_complete_paired_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'reports').mkdir();(root/'reports/batch-confirmed-circle-stage.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'missing'):verify_batch_circle_stage(root,'G')
    def test_stale_graph_and_external_directory_fail_before_replay(self):
        for change in ('graph','directory'):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);reports,stage=self.fixture(root)
                if change=='graph':stage['graph_sha256']='OLD'
                else:stage['artifact_directory']=str(root.parent)
                (reports/'batch-confirmed-circle-stage.json').write_text(json.dumps(stage))
                with self.assertRaisesRegex(ValueError,'unsafe or stale'):verify_batch_circle_stage(root,'G')
    def test_matching_manifest_hashes_do_not_replace_native_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);reports,stage=self.fixture(root)
            (reports/'batch-confirmed-circle-stage.json').write_text(json.dumps(stage))
            with self.assertRaisesRegex(ValueError,'implementation'):verify_batch_circle_stage(root,'G')


if __name__=='__main__':unittest.main()
