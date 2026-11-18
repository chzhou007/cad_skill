import contextlib,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import reuse_verified_native_artifact as original
from reuse_attribute_native_artifact import run,OWNER,PROOF,initialize_numerical_runtime,preload

class Tests(unittest.TestCase):
    def test_numerical_runtime_initializes_before_source_dependency_capture(self):
        import native_replay_session as observer
        initialize_numerical_runtime()
        with tempfile.TemporaryDirectory()as temp:
            with original.capture(observer)as reads:
                initialize_numerical_runtime()
                Path(temp,'missing-source-config.json').exists()
            self.assertTrue(reads.cacheable)
        fake=types.SimpleNamespace(__file__=str(Path(temp)/'numpy/__init__.py'))
        with patch('reuse_attribute_native_artifact.importlib.import_module',return_value=fake):
            with self.assertRaisesRegex(ValueError,'bound installed libraries'):initialize_numerical_runtime()

    def test_current_owner_application_reuses_complete_engine_without_mutating_original_owner_table(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);skills=root/'skills';script=skills/'build-cad-pipe-topology/scripts'/f'{OWNER}.py';script.parent.mkdir(parents=True);script.write_text('# fixture current owner\n')
            native=root/'native';native.mkdir();source=root/'source';source.write_text('中文01',encoding='utf-8');calls=[]
            from confirm_crossview_paths import encode
            result=dict(text='中文01');(native/PROOF).write_bytes(encode(result));module=types.ModuleType(OWNER);module.__file__=str(script)
            def verify(_):calls.append(1);return dict(text=source.read_text('utf-8'))
            module.verify_output=verify
            @contextlib.contextmanager
            def runtime(_):yield types.SimpleNamespace(stats={})
            owner_table=original.OWNERS.copy()
            with patch.dict(sys.modules,{OWNER:module}),patch.object(original,'inventory',return_value=[str(script)]),patch('native_projection_runtime_v1.default_native_runtime',runtime),patch('reuse_attribute_native_artifact.attribute_read_runtime',runtime),patch.object(sys,'dont_write_bytecode',True),patch.object(sys,'path',list(sys.path)):
                a=run(skills,native,root/'cache',root/'first',workers=2);b=run(skills,native,root/'cache',root/'second',workers=2)
                self.assertTrue(a['native_replay_performed']);self.assertTrue(b['dependency_checked_reuse']);self.assertEqual(len(calls),1)
                self.assertEqual((root/'first/proof.json').read_bytes(),(root/'second/proof.json').read_bytes());self.assertEqual(original.OWNERS,owner_table)
                self.assertFalse(b['human_accepted'])
                source.write_text('中文02',encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'artifact replay differs'):run(skills,native,root/'cache',root/'changed',workers=2)
if __name__=='__main__':unittest.main()
