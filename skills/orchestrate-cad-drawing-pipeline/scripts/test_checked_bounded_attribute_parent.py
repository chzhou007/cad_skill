import hashlib,json,tempfile,unittest
from pathlib import Path
from checked_bounded_attribute_parent import check,OWNER
from checked_native_parent_application import tree,encode,sha,NAMES

class Tests(unittest.TestCase):
    def test_exact_frozen_parent_inherited_algorithm_guard_and_proof_binding(self):
        with tempfile.TemporaryDirectory()as temp:
            base=Path(temp);root=base/'original';current=base/'current'
            for name in NAMES:
                (root/name).mkdir(parents=True);(current/name).mkdir(parents=True)
            relative='build-cad-pipe-topology/scripts/old.py'
            for folder in(root,current):p=folder/relative;p.parent.mkdir();p.write_text('original algorithm')
            native=base/'native';native.mkdir();proof=native/'bounded-main-extents.json';proof.write_text('{}')
            policy=base/'policy.json';policy.write_text('{}')
            spec=dict(owner=OWNER,skills_root=str(root),skill_tree_sha256=hashlib.sha256(encode(tree(root))).hexdigest(),environment_policy=str(policy),environment_policy_sha256=sha(policy),native_run=str(native),proof_sha256=sha(proof))
            self.assertEqual(check(spec,current)[1],proof)
            (current/relative).write_text('edited algorithm')
            with self.assertRaisesRegex(ValueError,'requalify'):check(spec,current)
            (current/relative).write_text('original algorithm');proof.write_text('{"edited":true}')
            with self.assertRaisesRegex(ValueError,'proof changed'):check(spec,current)
if __name__=='__main__':unittest.main()
