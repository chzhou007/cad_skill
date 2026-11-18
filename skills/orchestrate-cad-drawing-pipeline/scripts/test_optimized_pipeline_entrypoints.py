"""The public pipeline must reach new batch owners without legacy parsing."""
import sys
import types
import unittest
from unittest.mock import patch
import pipeline

class OptimizedEntrypoints(unittest.TestCase):
    def test_owner_arguments_and_exit_status_are_preserved(self):
        owners={'actions':'pipeline_actions','batch':'pipeline_batch_runtime',
                'batch-release':'integration_batch_release','hil-feedback':'hil_feedback_pipeline'}
        for command,owner in owners.items():
            seen=[]
            module=types.ModuleType(owner)
            def run(args):seen.append(args);return 2
            module.main=run
            with self.subTest(command=command),patch.dict(sys.modules,{owner:module}),patch.object(sys,'argv',['pipeline.py',command,'status','--run','some path']),patch.object(pipeline,'_main',side_effect=AssertionError('legacy parser entered')):
                self.assertEqual(pipeline.main(),2)
                self.assertEqual(seen,[['status','--run','some path']])

    def test_legacy_plan_still_reaches_legacy_entry(self):
        with patch.object(sys,'argv',['pipeline.py','plan','--config','input.json','--output','new']),patch.object(pipeline,'_main',return_value=17)as legacy:
            self.assertEqual(pipeline.main(),17)
            legacy.assert_called_once_with()

if __name__=='__main__':unittest.main()
