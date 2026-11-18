from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from confirm_crossview_paths import encode,sha
from wave_main_cohort_stage import load_policy_map,run_stage,rebase_unchanged_annotation_policy,SETTINGS


class Tests(unittest.TestCase):
    def test_map_resolves_all_evidence_without_local_input_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for key in SETTINGS:(root/(key+'.json')).write_bytes(b'{}')
            path=root/'map.json';values={k:k+'.json' for k in SETTINGS};path.write_bytes(encode({'TASK':values}))
            result=load_policy_map(path,{'TASK'});self.assertTrue(all(p.is_absolute() for p in result['TASK'].values()))
            values['graph']='graph.json';path.write_bytes(encode({'TASK':values}))
            with self.assertRaisesRegex(ValueError,'only pinned'):load_policy_map(path,{'TASK'})

    def test_unknown_task_and_parent_outside_task_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'map.json';path.write_bytes(encode({'OTHER':{}}))
            with self.assertRaisesRegex(ValueError,'unrecognized'):load_policy_map(path,{'TASK'})
            with self.assertRaisesRegex(ValueError,'owned by current family'):
                run_stage(root/'source',root/'outside.json',{},root/'task')

    def test_unchanged_capped_annotation_is_replayed_on_both_graphs_before_policy_rebase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.write_bytes(b'cad')
            old=root/'old.json';new=root/'new.json';old.write_bytes(encode({'nodes':[]}));new.write_bytes(encode({'nodes':[],'new':True}))
            policy=root/'policy.json';policy.write_bytes(encode(dict(source_sha256=sha(source),graph_sha256=sha(old),selections=[])))
            (root/'reports').mkdir()
            with patch('source_readability.read_source',return_value=('doc',{})),patch('native_capped_branch_annotations.collect',return_value={'scope':'same'}) as collect:
                result=rebase_unchanged_annotation_policy(source,old,new,policy,root)
                self.assertEqual(collect.call_count,2)
            self.assertNotEqual(sha(result),sha(policy))
            with patch('source_readability.read_source',return_value=('doc',{})),patch('native_capped_branch_annotations.collect',side_effect=[{'scope':'old'},{'scope':'new'}]):
                with self.assertRaisesRegex(ValueError,'changed a capped-annotation scope'):
                    rebase_unchanged_annotation_policy(source,old,new,policy,root)


if __name__=='__main__':unittest.main()
