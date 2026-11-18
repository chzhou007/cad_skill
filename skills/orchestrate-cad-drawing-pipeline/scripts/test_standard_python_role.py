from pathlib import Path
import base64,csv,hashlib,tempfile,unittest
from materialize_standard_python_role import restore

class StandardPythonRoleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name,text in {'runtime/python/python.exe':'delivered interpreter bytes','runtime/python/python312._pth':'old configuration',
            'runtime/python/Lib/site-packages/pip/value.txt':'base pip','runtime/site-packages/pip/value.txt':'supplied environment pip',
            'runtime/site-packages/numpy/__init__.py':'supplied numerical library'}.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    def test_standard_layout_preserves_input_bytes_and_selects_supplied_libraries(self):
        proof=restore(self.root);out=self.root/'runtime/standard-python'
        self.assertEqual((out/'Lib/site-packages/pip/value.txt').read_text(),'supplied environment pip')
        self.assertEqual((self.root/'runtime/python/Lib/site-packages/pip/value.txt').read_text(),'base pip')
        self.assertEqual((self.root/'runtime/python/python312._pth').read_text(),'old configuration')
        self.assertIn('Lib/site-packages',(out/'python312._pth').read_text())
        self.assertFalse(proof['source_runtime_bytes_modified'])
    def test_output_cannot_escape_or_recurse_into_input_runtime(self):
        for relative in ('../outside','runtime/python/recursive','runtime'):
            with self.assertRaises(ValueError):restore(self.root,relative)
    def test_existing_role_is_not_overwritten(self):
        restore(self.root)
        with self.assertRaises(FileExistsError):restore(self.root)
    def pillow_record(self,bad_hash=False):
        site=self.root/'runtime/site-packages'
        for name in ['pil/__init__.py','pil/image.py']:
            p=site/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'# supplied wheel bytes\n')
        record=site/'pillow-1.dist-info/RECORD';record.parent.mkdir()
        with record.open('w',encoding='utf8',newline='')as stream:
            writer=csv.writer(stream)
            for original,native in [('PIL/__init__.py','pil/__init__.py'),('PIL/Image.py','pil/image.py')]:
                raw=(site/native).read_bytes();digest=hashlib.sha256(raw).digest()
                writer.writerow([original,'sha256='+base64.urlsafe_b64encode(digest).decode().rstrip('=')if not bad_hash else 'sha256=wrong',len(raw)])
    def test_wheel_RECORD_restores_package_and_module_case_without_changing_bytes(self):
        cache=self.root/'runtime/site-packages/pil/__pycache__/unrecorded.pyc'
        cache.parent.mkdir(parents=True);cache.write_bytes(b'unrecorded supplied cache')
        self.pillow_record();proof=restore(self.root);site=self.root/'runtime/standard-python/Lib/site-packages'
        self.assertIn('PIL',[p.name for p in site.iterdir()])
        self.assertIn('Image.py',[p.name for p in (site/'PIL').iterdir()])
        self.assertEqual((site/'PIL/Image.py').read_bytes(),(self.root/'runtime/site-packages/pil/image.py').read_bytes())
        self.assertEqual(proof['wheel_RECORD_case_entries'],2)
    def test_wheel_RECORD_content_must_match_supplied_bytes(self):
        self.pillow_record(bad_hash=True)
        with self.assertRaisesRegex(ValueError,'content hash'):restore(self.root)

if __name__=='__main__':unittest.main()
