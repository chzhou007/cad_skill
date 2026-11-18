import json,os,shutil,tempfile,unittest
from pathlib import Path
import project_producer_policy as code
class PolicyProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.source=self.root/'source';self.target=self.root/'target';self.source.mkdir();self.target.mkdir()
        for base in [self.source,self.target]:(base/'data').mkdir();(base/'data/原数据.txt').write_text('中文原字节',encoding='utf8')
        self.policy=self.root/'policy.json';self.receipt=self.root/'receipt.json'
        self.result=self.root/'producer.json';self.result.write_text('{}');self.seed=self.root/'seeds.json';self.seed.write_text('{}')
        self.data=dict(mode='producer_API_input_enforcement_v1',owned_seeds={'runtime-cache/font.json':'a'*64},
            additional_files={str(self.source/'data/原数据.txt'):code.sha(self.source/'data/原数据.txt')},
            directories={str(self.source/'data'):['原数据.txt']},negative=[str(self.source/'absent.txt'),str(self.root/'external-absent.ini')])
        self.refresh()
    def refresh(self):
        self.policy.write_bytes(code.encode(self.data));self.receipt.write_bytes(code.encode(dict(mode='producer_API_policy_derivation_receipt_v1',
            package=str(self.source),policy_sha256=code.sha(self.policy),producer_result=code.pin(self.result),seed_manifest=code.pin(self.seed))))
    def compute(self):return code.compute(self.policy,self.receipt,self.source,self.target)
    def test_exact_typed_projection_preserves_seeds_and_external_absence(self):
        before=self.policy.read_bytes();policy,proof=self.compute()
        self.assertEqual(policy['additional_files'],{os.path.normcase(str(self.target/'data/原数据.txt')):code.sha(self.target/'data/原数据.txt')})
        self.assertEqual(policy['owned_seeds'],self.data['owned_seeds']);self.assertIn(os.path.normcase(str(self.root/'external-absent.ini')),policy['negative'])
        self.assertEqual(self.policy.read_bytes(),before);self.assertFalse(proof['original_JSON_and_proofs_rewritten'])
    def test_independent_verification_and_modified_output_rejection(self):
        out=self.root/'projection';code.produce(self.policy,self.receipt,self.source,self.target,out);code.verify(out)
        with self.assertRaisesRegex(ValueError,'Fresh'):code.produce(self.policy,self.receipt,self.source,self.target,out)
        (out/'policy.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'policy differs'):code.verify(out)
    def test_changed_source_or_target_bytes_are_held(self):
        (self.target/'data/原数据.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'target bytes'):self.compute()
        shutil.copyfile(self.source/'data/原数据.txt',self.target/'data/原数据.txt');(self.source/'data/原数据.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'source bytes'):self.compute()
    def test_directory_changes_and_new_negative_files_are_held(self):
        extra=self.target/'data/extra';extra.write_text('new')
        with self.assertRaisesRegex(ValueError,'directory members'):self.compute()
        extra.unlink();(self.target/'absent.txt').write_text('appeared')
        with self.assertRaisesRegex(ValueError,'absent probe'):self.compute()
    def test_positive_outside_source_and_nested_target_are_rejected(self):
        self.data['additional_files'][str(self.root/'external-positive')]='b'*64;self.refresh()
        with self.assertRaisesRegex(ValueError,'outside source'):self.compute()
        with self.assertRaisesRegex(ValueError,'disjoint'):code.compute(self.policy,self.receipt,self.source,self.source/'data')
    def test_changed_receipt_and_original_bindings_are_held(self):
        self.result.write_text('different')
        with self.assertRaisesRegex(ValueError,'source bindings changed'):self.compute()
    def test_unknown_fields_and_seed_escape_require_explicit_support(self):
        self.data['future_constraint']={};self.refresh()
        with self.assertRaisesRegex(ValueError,'Unknown policy fields'):self.compute()
        del self.data['future_constraint'];self.data['owned_seeds']={'../escape':'c'*64};self.refresh()
        with self.assertRaisesRegex(ValueError,'relative seed'):self.compute()
    def test_projection_cannot_write_into_either_input_package(self):
        with self.assertRaisesRegex(ValueError,'must not modify'):code.produce(self.policy,self.receipt,self.source,self.target,self.target/'output')
if __name__=='__main__':unittest.main()
