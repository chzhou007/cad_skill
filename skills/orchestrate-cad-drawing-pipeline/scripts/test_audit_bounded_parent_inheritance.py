import hashlib,tempfile,unittest
from pathlib import Path
from audit_bounded_parent_inheritance import audit
from checked_native_parent_application import tree,encode,sha,NAMES
from checked_bounded_attribute_parent import OWNER

class HistoricalAssetAuditTests(unittest.TestCase):
    def fixture(self,base):
        root=base/'old';cur=base/'current'
        for name in NAMES:(root/name).mkdir(parents=True);(cur/name).mkdir(parents=True)
        for name in ['algorithm.py','test_historical.py']:
            for target in [root,cur]:p=target/'build-cad-pipe-topology/scripts'/name;p.parent.mkdir(exist_ok=True);p.write_bytes(b'original\r\n')
        native=base/'native';native.mkdir();proof=native/'bounded-main-extents.json';proof.write_text('{}');policy=base/'policy.json';policy.write_text('{}')
        spec=dict(owner=OWNER,skills_root=str(root),skill_tree_sha256=hashlib.sha256(encode(tree(root))).hexdigest(),environment_policy=str(policy),environment_policy_sha256=sha(policy),native_run=str(native),proof_sha256=sha(proof))
        return root,cur,spec
    def test_original_guard_checks_historical_tests_and_algorithms(self):
        with tempfile.TemporaryDirectory()as t:
            root,cur,spec=self.fixture(Path(t));r=audit(spec,cur);self.assertEqual(r['production_assets'],1);self.assertEqual(r['test_assets'],1);self.assertTrue(r['original_strict_checker_used']);self.assertFalse(r['native_replay_performed'])
            for name in ['algorithm.py','test_historical.py']:
                p=cur/'build-cad-pipe-topology/scripts'/name;p.write_text('changed')
                with self.assertRaisesRegex(ValueError,'assets differ'):audit(spec,cur)
                p.write_bytes((root/p.relative_to(cur)).read_bytes())
    def test_additional_test_keeps_original_bytes_and_missing_old_test_blocks(self):
        with tempfile.TemporaryDirectory()as t:
            _,cur,spec=self.fixture(Path(t));(cur/'build-cad-pipe-topology/scripts/test_new.py').write_text('new independent case');self.assertEqual(audit(spec,cur)['test_assets'],1)
            (cur/'build-cad-pipe-topology/scripts/test_historical.py').unlink()
            with self.assertRaisesRegex(ValueError,'test_historical'):audit(spec,cur)

if __name__=='__main__':unittest.main()
