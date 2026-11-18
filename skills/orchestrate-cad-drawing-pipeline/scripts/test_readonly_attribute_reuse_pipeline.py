import sys,unittest
from unittest.mock import patch
import pipeline

class Tests(unittest.TestCase):
    def test_bounded_application_dispatches_without_changing_original_validation(self):
        args=['pipeline.py','reuse-bounded-attribute-artifact','--native-run','native','--cache-root','cache','--output','output']
        seen=[]
        with patch.object(sys,'argv',args),patch('reuse_attribute_native_artifact.main',side_effect=lambda:seen.append(sys.argv[:])),patch('reuse_verified_native_artifact.main')as old:
            pipeline.main();self.assertEqual(seen,[['pipeline.py',*args[2:]]]);old.assert_not_called();self.assertIs(sys.argv,args)
    def test_old_reuse_entry_remains_original_owner_dispatch(self):
        with patch.object(sys,'argv',['pipeline.py','reuse-native-artifact']),patch('reuse_verified_native_artifact.main')as old,patch('reuse_attribute_native_artifact.main')as new:
            pipeline.main();old.assert_called_once();new.assert_not_called()

if __name__=='__main__':unittest.main()
