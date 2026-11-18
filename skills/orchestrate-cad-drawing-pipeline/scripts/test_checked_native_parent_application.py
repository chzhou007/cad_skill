import json,shutil,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import checked_native_parent_application as parent

class Tests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder);old=root/'old';current=root/'current'
        for name in parent.NAMES:
            (old/name/'scripts').mkdir(parents=True);(current/name/'scripts').mkdir(parents=True)
        code='build-cad-pipe-topology/scripts/reader.py';(old/code).write_text('# original algorithm');shutil.copy2(old/code,current/code)
        native=root/'native';native.mkdir();proof=native/'member-projections.json';proof.write_text('{"中文":1}\n',encoding='utf8')
        policy=root/'policy.json';policy.write_text(json.dumps(dict(scope='isolated_pure_native_worker_only',stable_transport_context='fixture')))
        import hashlib
        spec=dict(owner='rebuild_compound_member_projections',skills_root=str(old),skill_tree_sha256=hashlib.sha256(parent.encode(parent.tree(old))).hexdigest(),
            native_run=str(native),proof_sha256=parent.sha(proof),environment_policy=str(policy),environment_policy_sha256=parent.sha(policy),cwd=str(root),cache_root=str(root/'cache'),workers=1)
        return root,old,current,code,proof,spec
    def test_new_rule_extends_parent_but_edited_inherited_algorithm_cannot_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root,old,current,code,proof,spec=self.fixture(folder);parent.check(spec,current)
            (current/'build-cad-pipe-topology/scripts/new_rule.py').write_text('# independent new rule');parent.check(spec,current)
            (current/code).write_text('# modified ancestor')
            with self.assertRaisesRegex(ValueError,'inherited native algorithm changed'):parent.check(spec,current)
    def test_original_frozen_version_native_proof_and_policy_are_all_pinned(self):
        for target in ('code','proof','policy'):
            with tempfile.TemporaryDirectory() as folder:
                root,old,current,code,proof,spec=self.fixture(folder)
                p=old/code if target=='code' else proof if target=='proof' else Path(spec['environment_policy']);p.write_text('changed')
                with self.assertRaises(ValueError):parent.check(spec,current)
    def test_reused_parent_is_currently_checked_not_reported_as_new_native_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root,old,current,code,proof,spec=self.fixture(folder)
            def child(command,**kwargs):
                out=Path(command[command.index('--output')+1]);out.mkdir();(out/'proof.json').write_bytes(proof.read_bytes())
                audit=dict(mode='content_checked_complete_native_artifact_reuse_v1',owner=spec['owner'],proof_sha256=spec['proof_sha256'],human_accepted=False,native_replay_performed=False,dependency_checked_reuse=True)
                (out/'execution.json').write_text(json.dumps(audit));return types.SimpleNamespace(returncode=0,stdout='',stderr='')
            with patch.object(parent.subprocess,'run',child):result,qualification=parent.apply(spec,current)
            self.assertEqual(result,{'中文':1});self.assertTrue(qualification['current_dependency_checked']);self.assertNotIn('native_replay_performed',qualification);self.assertFalse(qualification['human_accepted'])
            with patch.object(parent.subprocess,'run',return_value=types.SimpleNamespace(returncode=1,stdout='native failure',stderr='')):
                with self.assertRaisesRegex(ValueError,'dependency checks failed'):parent.apply(spec,current)

if __name__=='__main__':unittest.main()
