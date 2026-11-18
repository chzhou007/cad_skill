"""Delivery regressions: original path spelling, no overwrite, hash/escape guards."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from restore_sealed_review_runtime import checked_relative, plan, restore, WORKER, LAUNCHER


class RestoreSealedReviewRuntimeTests(unittest.TestCase):
    def inventory(self):
        names = [r'C:\BoundPython\python312.dll', r'C:\BoundNode\node.exe',
                 r'C:\BoundPython\Lib\xml\etree\ElementTree.py',
                 r'E:\Frozen\skills\viewer\scripts\sample_DN.py',
                 r'E:\Frozen\viewer\public\app.js',
                 r'C:\BoundVenv\Lib\site-packages\PIL\Image.py']
        digest = 'a'*64
        files = {n.lower(): digest for n in names}
        binding = {'skills_root': r'E:\Frozen\skills', 'directory': r'E:\Frozen\viewer',
                   'executable_path': r'C:\BoundVenv\Scripts\python.exe',
                   'runtime_and_skill_files': {n: digest for n in names}}
        return files, binding

    def test_case_sensitive_python_module_names_restore_original_binding(self):
        files, binding = self.inventory()
        rows = plan(files, binding)
        names = {r['relative'] for r in rows}
        self.assertIn('runtime/python/Lib/xml/etree/ElementTree.py', names)
        self.assertIn('skills/viewer/scripts/sample_DN.py', names)
        self.assertIn('runtime/site-packages/PIL/Image.py', names)
        self.assertEqual(len(rows), len(files))

    def test_path_traversal_rejected_even_inside_matched_namespace(self):
        with self.assertRaises(ValueError):
            checked_relative(r'E:\Frozen\skills\..\escape', r'E:\Frozen\skills')
        with self.assertRaises(ValueError):
            checked_relative(r'E:\Frozen\skills\file:stream', r'E:\Frozen\skills')
        with self.assertRaises(ValueError):
            checked_relative('relative/path', r'E:\Frozen\skills')

    def test_digest_disagreement_cannot_supply_original_case_alias(self):
        files, binding = self.inventory()
        binding['runtime_and_skill_files'][r'C:\BoundPython\Lib\xml\etree\ElementTree.py'] = 'b'*64
        with self.assertRaisesRegex(ValueError, 'different digest'):
            plan(files, binding)

    def test_no_overwrite_existing_annotation_or_old_package(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output = root/'existing'
            (output/'viewer/annotations').mkdir(parents=True)
            old = output/'viewer/annotations/review.json'
            old.write_bytes(b'{"historical":true}')
            with self.assertRaises(FileExistsError):
                restore(root/'missing-corpus', output, 'a'*64, 'b'*64)
            self.assertEqual(old.read_bytes(), b'{"historical":true}')

    def test_same_size_changed_manifest_rejected_before_creating_package(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); corpus = root/'corpus'; corpus.mkdir()
            p = corpus/'manifest.json'; p.write_bytes(b'{"a":1}')
            old = hashlib.sha256(p.read_bytes()).hexdigest()
            p.write_bytes(b'{"a":2}')
            (corpus/'runtime-binding.json').write_text('{}', encoding='utf8')
            output = root/'new'
            with self.assertRaisesRegex(ValueError, 'changed'):
                restore(corpus, output, old, 'b'*64)
            self.assertFalse(output.exists())

    def test_actual_embedded_workers_are_valid_python(self):
        compile(WORKER, 'replay_delivered_attributes.py', 'exec')
        compile(LAUNCHER, 'launch_portable_review.py', 'exec')
        self.assertIn("command.append('--open')", LAUNCHER)
        self.assertNotIn('webbrowser.open', LAUNCHER)


if __name__ == '__main__':
    unittest.main()
