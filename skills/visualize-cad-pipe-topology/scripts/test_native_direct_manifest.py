"""Explicit execution backends must be traceable in the portable manifest."""
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from build_visualization import SKILL,execution_dependency_paths


class Tests(unittest.TestCase):
    def test_legacy_or_absent_runtime_has_no_extra_dependencies(self):
        for runtime in (None,SimpleNamespace(__file__='legacy.py')):
            with self.subTest(runtime=runtime),patch.dict(sys.modules,{'native_replay_session':runtime}):
                self.assertEqual(execution_dependency_paths(),{})

    def test_explicit_worker_binds_both_real_execution_sources(self):
        owner=SKILL.parent/'orchestrate-cad-drawing-pipeline/scripts'
        runtime=owner/'native_direct_verification_runtime.py';worker=owner/'native_direct_worker.py'
        modules={'native_replay_session':SimpleNamespace(execution_backend='native_direct_verification_v1',__file__=str(runtime)),
                 '__main__':SimpleNamespace(__file__=str(worker))}
        with patch.dict(sys.modules,modules):
            result=execution_dependency_paths()
        self.assertEqual(result,{'native_direct_verification_runtime':runtime.resolve(),'native_direct_worker_entry':worker.resolve()})
        self.assertTrue(all(path.is_file() for path in result.values()))

    def test_false_runtime_or_worker_identity_is_rejected(self):
        owner=SKILL.parent/'orchestrate-cad-drawing-pipeline/scripts'
        for runtime,worker,message in [('other.py',owner/'native_direct_worker.py','runtime path'),
                                       (owner/'native_direct_verification_runtime.py','other.py','worker entry')]:
            modules={'native_replay_session':SimpleNamespace(execution_backend='native_direct_verification_v1',__file__=str(runtime)),
                     '__main__':SimpleNamespace(__file__=str(worker))}
            with self.subTest(runtime=str(runtime)),patch.dict(sys.modules,modules),self.assertRaisesRegex(ValueError,message):
                execution_dependency_paths()


if __name__=='__main__':unittest.main()
