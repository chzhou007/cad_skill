import hashlib,json,tempfile,unittest
from pathlib import Path
from source_comparison_gate import verify_confirmed_near_tee_stage

def write(path,value):
    path.write_text(json.dumps(value),encoding='utf8')

class ConfirmedNearTeeGateTests(unittest.TestCase):
    def test_claim_and_partial_receipt_require_real_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaisesRegex(ValueError,'requires its source stage'):
                verify_confirmed_near_tee_stage(root,'G',{'sourceNearTeeConfirmations':{'claimed':True}})
            (root/'reports').mkdir();write(root/'reports/confirmed-near-tee-stage.json',{})
            with self.assertRaisesRegex(ValueError,'missing'):verify_confirmed_near_tee_stage(root,'G')
    def fixture(self,root):
        reports=root/'reports';reports.mkdir();directory=root/'topology-confirmed-near-tees';directory.mkdir()
        graph=dict(metadata=dict(source_sha256='S'),sourceNearTeeConfirmations={'claimed':True},nodes=[],edges=[])
        gp=directory/'graph_with_confirmed_near_tees.json';write(gp,graph)
        graph_hash=hashlib.sha256(gp.read_bytes()).hexdigest()
        norm=root/'normalization.json';write(norm,dict(near_junction=[]))
        audit=dict(script_sha256='invented',screen_sha256='invented',source_sha256='S',output_graph_sha256=graph_hash,normalization=str(norm))
        ap=reports/'near-tee-confirmation-audit.json';write(ap,audit)
        (directory/ap.name).write_bytes(ap.read_bytes())
        stage=dict(status='source_pinned_normalized_near_tee_confirmation',source_sha256='S',graph_sha256=graph_hash,
            artifact_directory=str(directory),audit_sha256=hashlib.sha256(ap.read_bytes()).hexdigest(),hil_ready=False)
        return graph_hash,stage
    def test_unsafe_path_and_stale_hash_fail(self):
        for field in ('path','hash'):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);gh,stage=self.fixture(root)
                if field=='path':stage['artifact_directory']=str(root.parent)
                else:stage['graph_sha256']='OLD'
                write(root/'reports/confirmed-near-tee-stage.json',stage)
                with self.assertRaisesRegex(ValueError,'unsafe or stale'):verify_confirmed_near_tee_stage(root,gh)
    def test_matching_receipt_and_claim_do_not_replace_native_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);gh,stage=self.fixture(root)
            write(root/'reports/confirmed-near-tee-stage.json',stage)
            with self.assertRaisesRegex(ValueError,'implementation'):verify_confirmed_near_tee_stage(root,gh)
    def test_different_current_graph_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);gh,stage=self.fixture(root)
            write(root/'reports/confirmed-near-tee-stage.json',stage)
            with self.assertRaisesRegex(ValueError,'output mismatch'):verify_confirmed_near_tee_stage(root,gh,{'changed':True})

if __name__=='__main__':unittest.main()
