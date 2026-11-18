import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from capped_branch_annotation_stage import load_policy_map,run_stage,digest


class Tests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);r=Path(temp.name);task=r/'task';task.mkdir()
        paths=[r/'source.dxf',task/'graph.json',r/'policy.json']
        for p in paths:p.write_text('{}','utf8')
        return r,task,paths

    def test_map_resolves_only_existing_policy_for_known_tasks(self):
        r,task,paths=self.fixture();mapping=r/'map.json';mapping.write_text(json.dumps({'task':{'policy':'policy.json'}}),'utf8')
        self.assertEqual(load_policy_map(mapping,{'task'}),{'task':paths[2].resolve()});self.assertEqual(load_policy_map(None),{})
        with self.assertRaises(ValueError):load_policy_map(mapping,{'other'})
        mapping.write_text(json.dumps({'task':{'policy':'policy.json','graph':'external'}}),'utf8')
        with self.assertRaises(ValueError):load_policy_map(mapping,{'task'})

    def test_external_parent_cannot_be_silently_substituted(self):
        r,task,paths=self.fixture()
        with self.assertRaisesRegex(ValueError,'owned by current'):run_stage(paths[0],paths[1],paths[2],task/'other')

    def native_stub(self,paths,task):
        def invoke(command,check):
            out=Path(command[-1]);out.mkdir(parents=True);(out/'native-capped-branch-annotations-audit.json').write_text('{}','utf8')
        audit=dict(inputs=dict(source=dict(sha256=digest(paths[0])),graph=dict(sha256=digest(paths[1]))),records=1,graph_mutated=False,hil_ready=False)
        return invoke,audit

    def test_independent_replay_and_exact_inputs_required_before_receipt(self):
        r,task,paths=self.fixture();invoke,audit=self.native_stub(paths,task)
        with patch('capped_branch_annotation_stage.subprocess.run',side_effect=invoke),patch('native_capped_branch_annotations.verify_output',return_value=audit) as verify:
            result=run_stage(*paths,task);verify.assert_called_once()
        self.assertEqual(result['records'],1);self.assertFalse(result['graph_mutated']);self.assertEqual(result['retired_nodes'],0)
        self.assertEqual(result['graph_sha256'],digest(paths[1]));self.assertFalse(result['hil_ready'])
        with self.assertRaises(FileExistsError):run_stage(*paths,task)

    def test_replay_cannot_claim_modified_graph_or_close_hil(self):
        for key in ('graph_mutated','hil_ready'):
            r,task,paths=self.fixture();invoke,audit=self.native_stub(paths,task);audit[key]=True
            with self.subTest(key=key),patch('capped_branch_annotation_stage.subprocess.run',side_effect=invoke),patch('native_capped_branch_annotations.verify_output',return_value=audit):
                with self.assertRaisesRegex(ValueError,'preserve exact'):run_stage(*paths,task)
            self.assertFalse((task/'reports/native-capped-branch-annotations-stage.json').exists())

    def test_input_change_or_replay_failure_never_writes_receipt(self):
        for failure in ('input','replay'):
            r,task,paths=self.fixture();invoke,audit=self.native_stub(paths,task)
            def changed(command,check):
                invoke(command,check)
                if failure=='input':paths[1].write_text('changed','utf8')
            with self.subTest(failure=failure),patch('capped_branch_annotation_stage.subprocess.run',side_effect=changed),patch('native_capped_branch_annotations.verify_output',return_value=audit,side_effect=ValueError('native replay failed') if failure=='replay' else None):
                with self.assertRaises(ValueError):run_stage(*paths,task)
            self.assertFalse((task/'reports/native-capped-branch-annotations-stage.json').exists())


if __name__=='__main__':unittest.main()
