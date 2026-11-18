import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import package_current_review as package


class PublishedReviewPackage(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows extended-length path spelling')
    def test_windows_resolved_prefix_does_not_change_containment(self):
        with patch.object(Path, 'resolve', return_value=Path('\\\\?\\C:\\review\\viewer')):
            self.assertEqual(package.portable.resolved_path('unused'), Path('C:/review/viewer'))
        with patch.object(Path, 'resolve', return_value=Path('\\\\?\\UNC\\server\\share\\viewer')):
            self.assertEqual(package.portable.resolved_path('unused'), Path('//server/share/viewer'))

    def fixture(self, root):
        viewer, runtime = root / 'current-viewer', root / 'standard-python'
        (viewer / 'public/data').mkdir(parents=True)
        runtime.mkdir()
        for relative in ['serve.py', 'hil_server.py', 'launch_review.py', 'public/index.html',
                         'public/data/graph.json', 'public/data/manifest.json', 'public/data/cad.svg']:
            (viewer / relative).write_text('中文原图与拓扑 ' + relative, encoding='utf8')
        (viewer / 'annotations').mkdir()
        (viewer / 'annotations/history.json').write_text('{"旧批注":"保留"}', encoding='utf8')
        (viewer / 'startup-logs').mkdir()
        (viewer / 'startup-logs/previous.log').write_text('old machine state')
        (runtime / 'python.exe').write_bytes(b'fixture-interpreter')
        (runtime / 'python._pth').write_text('.\nDLLs\nLib\nLib/site-packages\n')
        binding = dict(schema='published_current_review_binding_v1', preferred_port=10534,
                       viewer=dict(path=str(viewer), files=package.inventory(viewer, ('annotations', 'startup-logs', '__pycache__'))),
                       runtime=dict(path=str(runtime), files=package.inventory(runtime, ('__pycache__',))),
                       annotations=package.inventory(viewer / 'annotations'), extras=[],
                       readme='解压完整文件夹，先诊断再启动。未知长度保持为空。\n')
        path = root / 'binding.json'
        package.dump(path, binding)
        return path, binding

    def test_current_bytes_original_launcher_and_annotation_history_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, binding = self.fixture(root)
            out = root / '中文 便携审查'
            result = package.package(path, package.digest(path), out)
            self.assertEqual(result['annotations_preserved'], 1)
            for relative, record in binding['viewer']['files'].items():
                self.assertEqual(package.digest(out / 'viewer' / relative), record['sha256'])
            self.assertEqual((out / 'viewer/annotations/history.json').read_bytes(),
                             (root / 'current-viewer/annotations/history.json').read_bytes())
            self.assertFalse((out / 'viewer/startup-logs').exists())
            self.assertFalse(result['raw_CAD_reconstruction_performed'])
            self.assertFalse(result['human_accepted'])
            package.portable.verify_payload(out)
            with zipfile.ZipFile(result['archive']['path']) as z:
                self.assertEqual(z.read(out.name + '/viewer/annotations/history.json'),
                                 (out / 'viewer/annotations/history.json').read_bytes())

    def test_changed_graph_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, _ = self.fixture(root)
            (root / 'current-viewer/public/data/graph.json').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'inventory changed'):
                package.package(path, package.digest(path), root / 'result')
            self.assertFalse((root / 'result').exists())

    def test_changed_binding_and_existing_destination_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, _ = self.fixture(root)
            with self.assertRaisesRegex(ValueError, 'binding changed'):
                package.package(path, '0' * 64, root / 'result')
            (root / 'result').mkdir()
            with self.assertRaises(FileExistsError):
                package.package(path, package.digest(path), root / 'result')

    def test_no_host_runtime_path_and_no_new_source_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, binding = self.fixture(root)
            (root / 'standard-python/python._pth').write_text('C:/host-python/Lib\n')
            binding['runtime']['files'] = package.inventory(root / 'standard-python')
            package.dump(path, binding)
            with self.assertRaisesRegex(ValueError, 'package-only'):
                package.package(path, package.digest(path), root / 'result')

    def test_current_annotation_changes_require_new_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, _ = self.fixture(root)
            (root / 'current-viewer/annotations/history.json').write_text('new expert answer')
            with self.assertRaisesRegex(ValueError, 'annotations changed'):
                package.package(path, package.digest(path), root / 'result')
            self.assertFalse((root / 'result').exists())

    def test_mutable_new_annotations_allowed_immutable_module_injection_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, _ = self.fixture(root)
            out = root / 'result'
            package.package(path, package.digest(path), out)
            (out / 'viewer/annotations/new.json').write_text('new local review')
            package.portable.verify_payload(out)
            (out / 'runtime/injected.py').write_text('unexpected module')
            with self.assertRaisesRegex(ValueError, 'Unlisted immutable'):
                package.portable.verify_payload(out)

    def test_extra_traversal_and_case_collision_rejected(self):
        for target in ['sources/../../escape', 'sources/../escape', 'sources\\escape']:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                path, binding = self.fixture(root)
                binding['extras'] = [dict(relative=target, path=str(path), sha256='0' * 64, bytes=1)]
                package.dump(path, binding)
                with self.assertRaises(ValueError):
                    package.package(path, package.digest(path), root / 'result')
                self.assertFalse((root / 'escape').exists())

    def test_missing_runtime_and_missing_viewer_do_not_use_installed_files(self):
        for owner, filename in [('runtime', 'python.exe'), ('viewer', 'hil_server.py')]:
            with self.subTest(owner=owner), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                path, binding = self.fixture(root)
                del binding[owner]['files'][filename]
                Path(binding[owner]['path'], filename).unlink()
                package.dump(path, binding)
                with self.assertRaises(ValueError):
                    package.package(path, package.digest(path), root / 'result')


if __name__ == '__main__':
    unittest.main()
