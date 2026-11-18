import unittest
from pathlib import Path
from unittest.mock import patch
import reuse_riser_provider_artifact as adapter
import reuse_verified_native_artifact as original
import reuse_attribute_native_artifact as existing
class Tests(unittest.TestCase):
    def test_only_owner_whitelist_is_extended_in_private_original_algorithm(self):
        old=dict(original.OWNERS);f=adapter.reader();self.assertIs(f.__code__,existing.run.__code__);self.assertEqual(original.OWNERS,old);self.assertIsNot(f.__globals__,existing.run.__globals__);self.assertEqual(f.__globals__['OWNER'],adapter.OWNER);self.assertEqual(f.__globals__['PROOF'],adapter.PROOF);self.assertNotIn(adapter.OWNER,original.OWNERS)
        changed={k for k in f.__globals__ if f.__globals__[k] is not existing.run.__globals__.get(k)};self.assertEqual(changed,{'OWNER','PROOF','preload','original'});self.assertIs(f.__globals__['preload']._private_preload.__code__,existing.preload.__code__);self.assertIs(f.__globals__['original'].run,original.run)
    def test_owner_cannot_be_selected_from_cache_data_or_command_text(self):
        with patch.dict('os.environ',{},clear=False),patch.object(adapter,'reader')as factory:
            factory.return_value.return_value={'native_replay_performed':False,'dependency_checked_reuse':True};r=adapter.run(Path('root'),Path('native'),Path('cache'),Path('new'),workers=22)
        self.assertEqual(len(factory.return_value.call_args.args),4);self.assertEqual(factory.return_value.call_args.kwargs,dict(force_native=False,workers=22));self.assertTrue(r['dependency_checked_reuse'])
    def test_explicit_runtime_version_is_preserved(self):
        import os
        with patch.dict(os.environ,{'CAD_NATIVE_OWNER_BATCH_VERSION':'1'}),patch.object(adapter,'reader')as factory:
            factory.return_value.return_value={};adapter.run(Path('root'),Path('native'),Path('cache'),Path('new'));self.assertEqual(os.environ['CAD_NATIVE_OWNER_BATCH_VERSION'],'1')
if __name__=='__main__':unittest.main()
