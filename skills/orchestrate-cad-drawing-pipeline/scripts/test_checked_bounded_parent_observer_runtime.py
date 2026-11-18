import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import checked_bounded_parent_observer_runtime as bridge
import native_replay_session as observer
from confirm_crossview_paths import encode

class Tests(unittest.TestCase):
    def fixture(self,root):
        proof=root/'proof.json';data=dict(a=1);proof.write_bytes(encode(data));digest=hashlib.sha256(proof.read_bytes()).hexdigest();cache=root/'cache';cache.mkdir();binding='a'*64
        closure=dict(cacheable=True,files={str(proof):list(observer._file_state(proof))},directories={},probes=[],scratch_roots=[],empty_read_probes=[])
        payload=dict(mode=bridge.engine.MODE,binding_sha256=binding,proof_sha256=digest,result=data,closure=closure);p=cache/(binding+'.json');p.write_bytes(bridge.engine.encode(dict(payload=payload,payload_sha256=hashlib.sha256(bridge.engine.encode(payload)).hexdigest())))
        report=dict(owner=bridge.OWNER,mode=bridge.engine.MODE,human_accepted=False,proof_sha256=digest,native_replay_performed=False,dependency_checked_reuse=True,source_graphs_mutated=False,binding_sha256=binding,cache_file=str(p));spec=dict(owner=bridge.OWNER,proof_sha256=digest,cache_root=str(cache));return proof,data,report,spec
    def test_complete_current_child_closure_is_merged_as_original_states(self):
        with tempfile.TemporaryDirectory()as tmp:
            proof,data,report,spec=self.fixture(Path(tmp));reads=bridge.child_closure(report,data,proof,spec,observer)
            self.assertTrue(reads.cacheable);self.assertTrue(reads.unchanged());self.assertEqual(reads.files[str(proof)],observer._file_state(proof))
    def test_missing_child_capsule_is_never_a_reusable_pass_flag(self):
        with tempfile.TemporaryDirectory()as tmp:
            proof,data,report,spec=self.fixture(Path(tmp));report['cache_file']=None;self.assertIsNone(bridge.child_closure(report,data,proof,spec,observer))
    def test_wrong_owner_proof_digest_capsule_or_changed_dependency_is_rejected(self):
        for kind in('owner','mode','execution','digest','data','outside','dependency'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory()as tmp:
                proof,data,report,spec=self.fixture(Path(tmp))
                if kind=='owner':report['owner']='unknown'
                elif kind=='mode':report['mode']='unknown'
                elif kind=='execution':report['dependency_checked_reuse']=False
                elif kind=='digest':Path(report['cache_file']).write_text('{}',encoding='utf8')
                elif kind=='data':data=dict(a=2)
                elif kind=='outside':report['cache_file']=str(Path(tmp)/'outside.json')
                else:proof.write_bytes(encode(dict(a=2)))
                with self.assertRaises((ValueError,KeyError)):bridge.child_closure(report,data,proof,spec,observer)
    def test_job_reuse_rechecks_dependencies_copies_values_and_keeps_generic_process_policy(self):
        import checked_bounded_attribute_parent as original
        import subprocess
        original_run=subprocess.run;root=Path(original.__file__).resolve().parents[2];runtime=bridge.Runtime(root,observer)
        with tempfile.TemporaryDirectory()as tmp:
            proof,data,report,spec=self.fixture(Path(tmp));calls=[];reads=observer._Reads(True)
            def child(*args):
                self.assertIsNone(observer._trace.get());calls.append(1);original.LAST_APPLICATION.clear();original.LAST_APPLICATION.update(report);return copy.deepcopy(data),dict(native=True)
            runtime.original=child
            with patch.object(original,'check',return_value=(root,proof,{})):
                token=observer._trace.set(reads)
                try:
                    a=runtime.call(spec,root);a[0]['a']=99;b=runtime.call(spec,root)
                finally:observer._trace.reset(token)
            self.assertEqual(b[0]['a'],1);self.assertEqual(len(calls),1);self.assertEqual(runtime.stats['content_checked_job_reuses'],1);self.assertTrue(reads.cacheable);self.assertIs(subprocess.run,original_run)
if __name__=='__main__':unittest.main()
