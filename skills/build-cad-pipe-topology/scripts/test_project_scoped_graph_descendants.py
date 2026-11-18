import copy,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from project_scoped_graph_descendants import asset,corner_owner,kind,verify_capped_roles,verify_corner
from confirm_crossview_paths import encode,sha


class Tests(unittest.TestCase):
    def test_preserved_owner_assets_and_loader_do_not_depend_on_work_R_scripts(self):
        before=list(sys.path);module,digest=corner_owner();self.assertEqual(sys.path,before)
        self.assertEqual(sha(module.__file__),digest);self.assertTrue(callable(module.compute));self.assertTrue(callable(module.verify_output))
        cap,_=asset('capped_roles');self.assertEqual(cap.name,'sh16_source_capped_branch_roles_v1.py')

    def test_capped_role_root_takes_precedence_over_its_preserved_corner_parent(self):
        self.assertEqual(kind(dict(sourceDeclaredCappedBranchInterfaces={},sourceSH16RelatedCornerKnownIssue={})),'capped_roles')
        self.assertEqual(kind(dict(sourceSH16RelatedCornerKnownIssue={})),'related_corner')
        with self.assertRaises(ValueError):kind({})

    def test_changed_or_escaped_asset_manifest_blocks_before_import(self):
        original=__import__('project_scoped_graph_descendants').load
        base=Path(__import__('project_scoped_graph_descendants').ASSETS)
        manifest=original(base/'manifest.json')
        for field,value in [('filename','../../outside.py'),('sha256','changed')]:
            changed=copy.deepcopy(manifest);changed['files']['related_corner'][field]=value
            with self.subTest(field=field),patch('project_scoped_graph_descendants.load',return_value=changed):
                with self.assertRaises((ValueError,FileNotFoundError)):asset('related_corner')

    def test_non_SH16_corner_cannot_borrow_the_project_adapter(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'graph_with_edges.json').write_bytes(encode(dict(sourceSH16RelatedCornerKnownIssue={},metadata=dict(source_sha256='LF20'))))
            (root/'SH16-related-corner-known-issue-audit.json').write_bytes(encode({}))
            with self.assertRaisesRegex(ValueError,'SH16-10 only'):verify_corner(root)

    def test_source_cap_audit_owner_drift_blocks_before_parent_replay(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'graph_with_edges.json').write_bytes(encode(dict(sourceDeclaredCappedBranchInterfaces={},metadata=dict(source_sha256='S'))))
            (root/'source-capped-interface-roles-audit.json').write_bytes(encode(dict(mode='unsupported')))
            with self.assertRaisesRegex(ValueError,'owner or project'):verify_capped_roles(root,None,None)


if __name__=='__main__':unittest.main()
