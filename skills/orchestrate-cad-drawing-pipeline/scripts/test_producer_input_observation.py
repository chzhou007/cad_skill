"""Real API semantics and producer-owned provenance, without replacing CAD tests."""
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import test_delivered_source_input_runtime as fixtures
import delivered_source_input_runtime as adapter
import producer_input_observation as observation


class ProducerObservationTests(unittest.TestCase):
    setUp = fixtures.SealedSourceInputTests.setUp
    runtime = fixtures.SealedSourceInputTests.runtime

    def observed(self, strict=False, **policy):
        helper=self.package/'helpers/observation.py'
        helper.parent.mkdir(exist_ok=True)
        shutil.copyfile(observation.__file__,helper)
        raw=dict(mode='producer_API_input_enforcement_v1' if strict else 'producer_API_input_discovery_v1',**policy)
        policy_path=self.package/'helpers/policy.json'
        policy_path.write_text(json.dumps(raw),encoding='utf8')
        self.index['producer_observation']=dict(relative='helpers/observation.py',sha256=observation.sha(helper),
            policy_relative='helpers/policy.json',policy_sha256=observation.sha(policy_path))
        runtime=self.runtime()
        return runtime,runtime.producer_observer

    def finish(self, observer):
        return json.loads(Path(observer.finish()['path']).read_text('utf8'))

    def test_absent_and_empty_probes_retain_original_exception_and_errno(self):
        runtime,obs=self.observed()
        for p in [self.root/'absent.txt','']:
            with self.assertRaises(FileNotFoundError)as original:
                runtime.open(p)
            with self.assertRaises(FileNotFoundError)as actual:
                obs.call('open',runtime.open,(p,),{})
            self.assertEqual((type(actual.exception),actual.exception.errno),(type(original.exception),original.exception.errno))
        report=self.finish(obs)
        self.assertEqual([r['outcome']for r in report['events']],['raised','raised'])
        self.assertEqual(report['events'][1]['role'],'empty_native_probe')
        self.assertFalse(report['strict_API_input_gate_passed'])

    def test_successful_native_stat_and_read_bytes_are_unchanged(self):
        runtime,obs=self.observed(strict=True)
        actual=obs.call('stat',runtime.stat,(self.host,),{})
        self.assertEqual(actual,adapter.NATIVE_STAT(self.delivered))
        with obs.call('open',runtime.open,(self.host,),dict(encoding='utf8'))as f:
            self.assertEqual(f.read(),'已交付原始数据')
        self.assertTrue(self.finish(obs)['strict_API_input_gate_passed'])

    def test_unknown_existing_package_file_is_discovered_and_strictly_held(self):
        p=self.package/'unknown.txt';p.write_text('not a bound source')
        runtime,obs=self.observed()
        with obs.call('open',runtime.open,(p,),{})as f:self.assertEqual(f.read(),'not a bound source')
        self.assertEqual(self.finish(obs)['unresolved'][0]['reason'],'packaged_or_external_file_not_fixed')
        runtime,obs=self.observed(strict=True)
        with self.assertRaisesRegex(PermissionError,'Unqualified producer input'):
            obs.call('open',runtime.open,(p,),{})

    def test_absence_changed_after_failed_open_remains_input_change(self):
        runtime,obs=self.observed()
        p=self.root/'absent.txt'
        with self.assertRaises(FileNotFoundError):obs.call('open',runtime.open,(p,),{})
        p.write_text('appeared after missing probe')
        report=self.finish(obs)
        self.assertEqual(report['changed_inputs'][0]['path'],runtime.key(p))

    def test_fixed_directory_records_actual_native_state_and_changes(self):
        runtime,obs=self.observed(strict=True,directories={os.path.normcase(str(self.package/'data')):os.listdir(self.package/'data')})
        self.assertEqual(obs.call('listdir',runtime.listdir,(self.root/'logical-dir',),{}),[])
        (self.package/'data/extra.txt').write_text('new directory member')
        report=self.finish(obs)
        self.assertEqual(len(report['changed_inputs']),1)
        self.assertFalse(report['strict_API_input_gate_passed'])

    def test_owned_seed_required_and_historical_final_graph_seed_rejected(self):
        seed=self.work/'seed.json';seed.write_text('pre-existing seed')
        runtime,obs=self.observed(strict=True)
        with self.assertRaisesRegex(PermissionError,'without_seed'):
            obs.call('open',runtime.open,(seed,),{})
        runtime,obs=self.observed(strict=True,owned_seeds={'seed.json':observation.sha(seed)})
        with obs.call('open',runtime.open,(seed,),{})as f:self.assertEqual(f.read(),'pre-existing seed')
        self.assertTrue(self.finish(obs)['strict_API_input_gate_passed'])
        self.index['forbidden_historical_final_graph_hashes']=[observation.sha(seed)]
        with self.assertRaisesRegex(ValueError,'Historical final graph'):
            self.observed(strict=True,owned_seeds={'seed.json':observation.sha(seed)})

    def test_successful_write_then_atomic_rename_proves_generated_input(self):
        runtime,obs=self.observed(strict=True)
        p=self.work/'generated.tmp';target=self.work/'generated.json'
        with obs.call('open',runtime.open,(p,'w'),{},True,True)as f:f.write('actual new output')
        obs.call('replace',os.replace,(p,target),{},True,False,target)
        with obs.call('open',runtime.open,(target,),{})as f:self.assertEqual(f.read(),'actual new output')
        report=self.finish(obs)
        self.assertEqual(report['events'][-1]['provenance']['role'],'generated_owned_file')
        self.assertTrue(report['strict_API_input_gate_passed'])

    def test_another_process_owner_uses_shared_success_journal(self):
        runtime,obs=self.observed(strict=True)
        p=self.work/'new-parent.json'
        with obs.call('open',runtime.open,(p,'w'),{},True,True)as f:f.write('new parent')
        # A new Runtime has no process-local writer cache; it must consume the
        # successful effect journal, as spawned workers do in actual execution.
        other=self.runtime();next_observer=other.producer_observer
        with next_observer.call('open',other.open,(p,),{})as f:self.assertEqual(f.read(),'new parent')
        self.assertEqual(self.finish(next_observer)['events'][0]['provenance']['writer']['started_ns'],runtime.started)

    def test_failed_write_and_native_audit_attempt_do_not_invent_success(self):
        runtime,obs=self.observed()
        missing=self.work/'absent-parent/out.txt'
        with self.assertRaises(FileNotFoundError):
            obs.call('open',runtime.open,(missing,'w'),{},True,True)
        obs.native_event('open',(str(missing),'w',os.O_WRONLY|os.O_CREAT|os.O_TRUNC))
        report=self.finish(obs)
        self.assertEqual(report['owned_successful_effects'],[])
        self.assertEqual(report['events'][-1]['outcome'],'audit_attempt_only')

    def test_helper_and_policy_hashes_fail_closed(self):
        self.observed()
        (self.package/'helpers/policy.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'helper/policy changed'):
            self.runtime()

    def test_changed_then_restored_input_is_not_hidden_by_latest_snapshot(self):
        p=self.package/'unfixed.txt';p.write_text('initial')
        runtime,obs=self.observed()
        original=p.read_bytes()
        for text in ['initial','changed','initial']:
            p.write_text(text)
            with obs.call('open',runtime.open,(p,),{})as f:f.read()
        self.assertEqual(p.read_bytes(),original)
        self.assertTrue(any(x.get('detected')=='later_API_observation'for x in self.finish(obs)['changed_inputs']))

    def test_installed_open_code_wrapper_executes_bytes_and_never_calls_mutators(self):
        seed=self.work/'entry.py'
        seed.write_text("from pathlib import Path\nprint('中文真实执行')\nPath('generated.txt').write_text('实际产物',encoding='utf8')\n",encoding='utf8')
        before=seed.stat()
        runtime,_=self.observed(owned_seeds={'entry.py':observation.sha(seed)})
        code="""import sys,pkgutil
sys.path.insert(0,sys.argv[1])
from delivered_source_input_runtime import Runtime
Runtime.install_native_fonts=lambda self:None
Runtime.install_multiprocessing=lambda self:None
r=Runtime(sys.argv[2],sys.argv[3],sys.argv[4]);r.execute([sys.argv[5]])
"""
        p=subprocess.run([sys.executable,'-I','-X','utf8','-B','-c',code,str(Path(adapter.__file__).parent),
            str(self.package),str(self.work),runtime.index_sha256,str(seed)],cwd=self.work,
            capture_output=True,text=True,encoding='utf8')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout,'中文真实执行\n')
        self.assertEqual((self.work/'generated.txt').read_text('utf8'),'实际产物')
        self.assertEqual(seed.stat().st_mtime_ns,before.st_mtime_ns)


if __name__=='__main__':unittest.main()
