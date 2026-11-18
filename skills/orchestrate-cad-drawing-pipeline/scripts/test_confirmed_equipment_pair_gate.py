import hashlib,json,tempfile,unittest
from pathlib import Path
from source_comparison_gate import verify_confirmed_equipment_pair_stage

class ConfirmedEquipmentPairGateTests(unittest.TestCase):
    def test_graph_flag_and_partial_stage_cannot_replace_native_proof(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaisesRegex(ValueError,'requires its source stage'):
                verify_confirmed_equipment_pair_stage(root,'G',{'confirmedEquipmentPairReconstruction':{'claimed':True}})
            (root/'reports').mkdir();(root/'reports/confirmed-equipment-pair-stage.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'missing'):verify_confirmed_equipment_pair_stage(root,'G')
    def fixture(self,root):
        reports=root/'reports';reports.mkdir();directory=root/'topology-confirmed-equipment-pairs';directory.mkdir()
        body=json.dumps({'implementation_sha256':['invented']}).encode()
        (reports/'equipment-pair-reconstruction-audit.json').write_bytes(body);(directory/'equipment-pair-reconstruction-audit.json').write_bytes(body)
        return reports,dict(status='source_pinned_confirmed_equipment_pair_reconstruction',graph_sha256='G',hil_ready=False,artifact_directory=str(directory),audit_sha256=hashlib.sha256(body).hexdigest())
    def test_stale_graph_or_external_directory_rejects_before_replay(self):
        for field in ('graph','directory'):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);reports,stage=self.fixture(root)
                if field=='graph':stage['graph_sha256']='OLD'
                else:stage['artifact_directory']=str(root.parent)
                (reports/'confirmed-equipment-pair-stage.json').write_text(json.dumps(stage))
                with self.assertRaisesRegex(ValueError,'unsafe or stale'):verify_confirmed_equipment_pair_stage(root,'G')
    def test_matching_receipt_hash_does_not_bypass_native_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);reports,stage=self.fixture(root);(reports/'confirmed-equipment-pair-stage.json').write_text(json.dumps(stage))
            with self.assertRaisesRegex(ValueError,'implementation'):verify_confirmed_equipment_pair_stage(root,'G')

if __name__=='__main__':unittest.main()
