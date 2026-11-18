import importlib,sys,tempfile,types,unittest,threading,json
from pathlib import Path
from unittest.mock import patch
import historical_parent_native_replay as owner

class Tests(unittest.TestCase):
    def fixture(self,root):
        old=root/'old';current=root/'current'
        for folder,text in ((old,'historical'),(current,'current')):
            scripts=folder/'build-cad-pipe-topology/scripts';scripts.mkdir(parents=True)
            (scripts/'cad_runtime_scope_test.py').write_text('VALUE='+repr(text)+'\n',encoding='utf8')
        module=types.ModuleType('cad_runtime_scope_test');module.__file__=str(current/'build-cad-pipe-topology/scripts/cad_runtime_scope_test.py');module.VALUE='current'
        return old,current,module
    def test_actual_historical_module_loaded_and_original_namespace_restored(self):
        with tempfile.TemporaryDirectory()as directory:
            old,current,module=self.fixture(Path(directory));name='cad_runtime_scope_test';before=sys.modules.get(name);paths=list(sys.path)
            sys.modules[name]=module
            try:
                with owner.historical_namespace(old,current):
                    historical=importlib.import_module(name);self.assertEqual(historical.VALUE,'historical')
                    self.assertTrue(Path(historical.__file__).is_relative_to(old));self.assertIsNot(historical,module)
                self.assertIs(sys.modules[name],module);self.assertEqual(sys.path,paths)
            finally:
                if before is None:sys.modules.pop(name,None)
                else:sys.modules[name]=before
    def test_exception_also_restores_current_modules_and_paths(self):
        with tempfile.TemporaryDirectory()as directory:
            old,current,module=self.fixture(Path(directory));name='cad_runtime_scope_test';before=sys.modules.get(name);paths=list(sys.path);sys.modules[name]=module
            try:
                with self.assertRaisesRegex(ValueError,'native failure'):
                    with owner.historical_namespace(old,current):
                        importlib.import_module(name);raise ValueError('native failure')
                self.assertIs(sys.modules[name],module);self.assertEqual(sys.path,paths)
            finally:
                if before is None:sys.modules.pop(name,None)
                else:sys.modules[name]=before
    def test_concurrent_namespace_use_is_rejected_before_any_import(self):
        with patch.object(owner.threading,'enumerate',return_value=[object(),object()]):
            with self.assertRaisesRegex(RuntimeError,'one main Python thread'):
                with owner.historical_namespace(Path('old'),Path('current')):self.fail('not entered')
    def test_factory_caches_only_callable_identity_and_runs_every_requested_replay(self):
        a=owner.verifier_for('test-historical-scope');b=owner.verifier_for('test-historical-scope');self.assertIs(a,b)
        with patch.object(owner,'verify_parent',side_effect=[dict(value=1),dict(value=2)])as native:
            self.assertEqual(a('one')['value'],1);self.assertEqual(b('one')['value'],2);self.assertEqual(native.call_count,2)
    def test_stale_original_library_rejected_before_historical_owner_import(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);run=root/'run';run.mkdir();skills=root/'skills';scripts=skills/'orchestrate-cad-drawing-pipeline/scripts';scripts.mkdir(parents=True)
            (run/owner.AUDIT).write_text(json.dumps(dict(implementation_sha256={'native_replay_session.py':owner.LEGACY_CACHE})),encoding='utf8')
            (scripts/'native_replay_session.py').write_text('not the original library',encoding='utf8')
            with patch.object(owner,'historical_namespace')as namespace:
                with self.assertRaisesRegex(ValueError,'library bytes'):owner.preflight(run,skills)
                namespace.assert_not_called()

if __name__=='__main__':unittest.main()
