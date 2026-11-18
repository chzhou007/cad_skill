from pathlib import Path
import copy,hashlib,json,os,tempfile,unittest
from collect_execution_package_ancestors import extend

class ExecutionPackageAncestorsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.package=self.base/'inputs';self.package.mkdir()
        self.work=self.base/'run/work';self.work.mkdir(parents=True)
        self.index=dict(files={},negative=[])
        self.original=self.base/'package.json';self.original.write_text('{"type":"module"}\n',encoding='utf8')
        self.key=lambda p:os.path.normcase(str(p.resolve()))
    def test_existing_package_is_delivered_and_new_output_parent_absence_recorded(self):
        result=extend(self.index,self.package,self.work)
        row=self.index['files'][self.key(self.original)]
        self.assertEqual((self.package/row['relative']).read_bytes(),self.original.read_bytes())
        self.assertEqual(row['sha256'],hashlib.sha256(self.original.read_bytes()).hexdigest())
        self.assertIn(self.key(self.work.parent/'package.json'),self.index['negative'])
        self.assertTrue(result['observed'])
    def test_repeated_collection_preserves_identical_index(self):
        extend(self.index,self.package,self.work);before=copy.deepcopy(self.index)
        result=extend(self.index,self.package,self.work)
        self.assertEqual(before,self.index);self.assertFalse(result['added'])
    def test_changed_existing_package_is_not_silently_rebound(self):
        extend(self.index,self.package,self.work);self.original.write_text('{"type":"commonjs"}',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'changed'):extend(self.index,self.package,self.work)
    def test_previously_absent_package_cannot_appear_silently(self):
        extend(self.index,self.package,self.work)
        (self.work.parent/'package.json').write_text('{}',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'appeared'):extend(self.index,self.package,self.work)
    def test_overlapping_runtime_and_output_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'disjoint'):extend(self.index,self.package,self.package/'work')

if __name__=='__main__':unittest.main()
