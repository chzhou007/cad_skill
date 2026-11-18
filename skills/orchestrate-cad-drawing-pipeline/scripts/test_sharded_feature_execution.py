import hashlib,json,os,tempfile,threading,time,types,unittest
from pathlib import Path
from unittest.mock import patch
from feature_impact import run_selected

class Tests(unittest.TestCase):
    def test_isolated_shard_imports_untested_sibling_skill_without_prior_test_import(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);scripts=root/'one/scripts';dependency=root/'two/scripts'
            scripts.mkdir(parents=True);dependency.mkdir(parents=True)
            (dependency/'cad_sibling_only_dep.py').write_text('VALUE="中文"\n',encoding='utf8')
            (scripts/'test_isolated_dependency.py').write_text('import unittest\nfrom cad_sibling_only_dep import VALUE\nclass Tests(unittest.TestCase):\n def test_value(self):self.assertEqual(VALUE,"中文")\n',encoding='utf8')
            rows=run_selected(dict(tests=['one/scripts/test_isolated_dependency.py'],fallback_full_suites=False),root,workers=2)
            self.assertEqual(len(rows),1);self.assertEqual(rows[0]['exit_code'],0,rows[0]['stderr'])

    def test_qualified_independent_methods_expand_once_serial_and_changed_sources_keep_modules(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);scripts=root/'one/scripts';scripts.mkdir(parents=True)
            module=scripts/'test_example.py';module.write_text('import unittest\nclass Example(unittest.TestCase):\n def test_a(self):self.assertEqual(1,1)\n def test_b(self):self.assertEqual(2,2)\n',encoding='utf8')
            assets=root/'orchestrate-cad-drawing-pipeline/assets';assets.mkdir(parents=True)
            (assets/'test-execution-policy.json').write_text(json.dumps(dict(isolated_method_modules={'one/scripts/test_example.py':hashlib.sha256(module.read_bytes()).hexdigest()})),encoding='utf8')
            result=dict(tests=['one/scripts/test_example.py'],fallback_full_suites=False)
            rows=run_selected(result,root,workers=2)
            self.assertEqual(sorted(item for row in rows for item in row['command'][3:]),['test_example.Example.test_a','test_example.Example.test_b'])
            self.assertTrue(all(row['exit_code']==0 for row in rows))
            serial=run_selected(result,root,workers=1);self.assertEqual(serial[0]['command'][3:],['test_example'])
            module.write_text(module.read_text()+'\n# changed\n')
            rows=run_selected(result,root,workers=2);self.assertEqual(rows[0]['command'][3:],['test_example'])
    def test_class_shared_fixture_cannot_be_split(self):
        from discover_isolated_test_cases import discover
        import sys
        with tempfile.TemporaryDirectory()as folder:
            module=Path(folder)/'test_shared_fixture.py';module.write_text('import unittest\nclass Example(unittest.TestCase):\n @classmethod\n def setUpClass(cls):pass\n def test_a(self):pass\n',encoding='utf8');sys.path.insert(0,folder)
            try:
                with self.assertRaisesRegex(ValueError,'class fixtures'):discover('test_shared_fixture')
            finally:sys.path.remove(folder);sys.modules.pop('test_shared_fixture',None)
    def test_same_owner_is_split_without_omission_duplication_or_hidden_failure(self):
        active=0;peak=0;lock=threading.Lock();environments=[]
        def invoke(command,**kwargs):
            nonlocal active,peak
            with lock:active+=1;peak=max(peak,active);environments.append(kwargs['env'])
            time.sleep(.02)
            with lock:active-=1
            return types.SimpleNamespace(returncode=7 if 'test_07'in command else 0,stdout='中文',stderr='')
        expected=['test_%02d'%i for i in range(30)]
        result=dict(tests=['one/scripts/'+name+'.py'for name in expected],fallback_full_suites=False)
        with patch('feature_impact.subprocess.run',side_effect=invoke):rows=run_selected(result,workers=4)
        self.assertEqual(sorted(name for row in rows for name in row['command'][3:]),expected)
        self.assertEqual(len(rows),4);self.assertEqual(peak,4);self.assertEqual(sum(row['exit_code']!=0 for row in rows),1)
        self.assertTrue(all(env['CAD_NATIVE_WORKERS']==env['CAD_TEST_WORKERS']=='1'for env in environments))
    def test_fallback_discovers_unregistered_files_serial_and_recursive_discovery_preserved(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);scripts=root/'one/scripts';scripts.mkdir(parents=True)
            for name in ('test_old.py','test_unmapped.py','test_js.mjs'):(scripts/name).write_text('')
            result=dict(tests=['one/scripts/test_old.py'],fallback_full_suites=True)
            with patch('feature_impact.subprocess.run',return_value=types.SimpleNamespace(returncode=0,stdout='',stderr='')):
                rows=run_selected(result,root,workers=2);serial=run_selected(result,root,workers=1)
            self.assertEqual(sorted(name for row in rows for name in row['command']if name.startswith('test_')),['test_js.mjs','test_old','test_unmapped'])
            self.assertIn('discover',serial[0]['command'])
            nested=scripts/'nested';nested.mkdir();(nested/'test_child.py').write_text('')
            with patch('feature_impact.subprocess.run',return_value=types.SimpleNamespace(returncode=0,stdout='',stderr='')):rows=run_selected(result,root,workers=2)
            self.assertIn('discover',rows[0]['command'])
if __name__=='__main__':unittest.main()
