import copy,json,os,shutil,unittest
from pathlib import Path
import producer_parent_receipt_observation as adapter
import build_parent_receipt_producer_policy as policy
import test_generated_local_parent_inputs as generated
import test_producer_input_observation as oldobs
import test_observed_generated_parent_inputs as oldpolicy

class ReceiptObservationTests(unittest.TestCase):
    setUp=generated.GeneratedParentInputTests.setUp
    runtime=generated.GeneratedParentInputTests.runtime
    finish=oldobs.ProducerObservationTests.finish
    def observed(self):
        oldruntime,old=oldobs.ProducerObservationTests.observed(self,strict=True)
        binding=self.index['producer_observation'];binding['base_observer']=dict(relative=binding['relative'],sha256=binding['sha256'])
        target=self.package/'helpers/receipt-observer.py';shutil.copyfile(adapter.__file__,target)
        binding.update(relative='helpers/receipt-observer.py',sha256=adapter.sha(target))
        runtime=self.runtime();return runtime,runtime.producer_observer
    def test_actual_producer_receipt_is_readonly_input_with_real_bytes_and_stat(self):
        runtime,obs=self.observed()
        self.assertEqual(obs.call('stat',runtime.stat,(self.receipt,),{}),self.receipt.stat())
        with obs.call('open',runtime.open,(self.receipt,),dict(encoding='utf8'))as f:self.assertEqual(f.read(),self.receipt.read_text('utf8'))
        report=self.finish(obs);self.assertTrue(report['strict_API_input_gate_passed']);self.assertFalse(report['owned_seed_hashes'])
        proof=report['qualified_fresh_parent_producer_receipts'][0];self.assertFalse(proof['startup_seed']);self.assertEqual(proof['actual_generated_outputs'][0]['sha256'],self.digest)
    def test_receipt_write_and_graph_or_receipt_mutation_rejected(self):
        runtime,obs=self.observed()
        with self.assertRaisesRegex(PermissionError,'read-only'):obs.call('open',runtime.open,(self.receipt,'w'),{},True,True)
        self.fresh.write_text('changed')
        with self.assertRaisesRegex(ValueError,'output changed'):obs.call('open',runtime.open,(self.receipt,),{})
        self.fresh.write_bytes(self.fixed.read_bytes());self.receipt.write_text('{}')
        with self.assertRaisesRegex(ValueError,'receipt changed'):obs.call('stat',runtime.stat,(self.receipt,),{})
    def test_unrelated_owned_file_and_original_observer_changes_still_rejected(self):
        runtime,obs=self.observed();unknown=self.work/'unproved.json';unknown.write_text('{}')
        with self.assertRaisesRegex(PermissionError,'without_seed'):obs.call('open',runtime.open,(unknown,),{})
        base=self.index['producer_observation']['base_observer'];(self.package/base['relative']).write_text('changed')
        with self.assertRaisesRegex(ValueError,'original observer changed'):self.runtime()
    def test_reference_role_escape_and_bool_pointer_rejected(self):
        for value in ['reference_graph',True]:
            index=copy.deepcopy(self.index)
            if value is True:index['generated_local_parents'][os.path.normcase(str(self.historical))]['producer_field'][1]=True
            else:index['generated_local_parents'][os.path.normcase(str(self.historical))]['producer_field'][2]=value
            with self.assertRaisesRegex(ValueError,'actual output role'):adapter.receipt_bindings(index,self.work)
        index=copy.deepcopy(self.index);next(iter(index['generated_local_parents'].values()))['producer_receipt_relative']='../escape.json'
        with self.assertRaisesRegex(ValueError,'escaped work'):adapter.receipt_bindings(index,self.work)

class ReceiptPolicyTests(unittest.TestCase):
    setUp=oldpolicy.GeneratedParentPolicyTests.setUp
    refresh=oldpolicy.GeneratedParentPolicyTests.refresh
    compute=oldpolicy.GeneratedParentPolicyTests.compute
    def add_receipt_hold(self):
        row=dict(path=str(self.proof),role='owned_output',operation='open',state=dict(kind='file',sha256=policy.sha(self.proof)),reason='owned_read_without_seed_or_successful_writer')
        self.reports[0]['unresolved'].append(row);self.refresh();return row
    def new_compute(self):return policy.compute(self.run/'execution-result.json',self.package,self.seeds)
    def test_original_guard_kept_and_only_source_proved_receipt_reclassified(self):
        self.add_receipt_hold();before=copy.deepcopy(self.reports)
        with self.assertRaisesRegex(ValueError,'Unproved owned reads'):self.compute()
        actual,proof=self.new_compute();self.assertEqual(len(proof['typed_role_reclassifications']),1)
        self.assertEqual(self.reports,before);self.assertFalse(proof['raw_observations_rewritten'])
        self.assertNotIn(str(self.proof),actual['additional_files']);self.assertNotIn('producer.json',actual['owned_seeds'])
        self.assertTrue(proof['strict_producer_execution_required'])
    def test_another_owned_file_is_not_promoted_to_seed(self):
        row=self.add_receipt_hold();row['path']=str(self.run/'work/not-producer.json');self.refresh()
        with self.assertRaisesRegex(ValueError,'Unproved owned reads'):self.new_compute()
    def test_content_or_source_observation_mutation_rejected(self):
        self.add_receipt_hold();self.fresh.write_text('bad')
        with self.assertRaisesRegex(ValueError,'output changed'):self.new_compute()
if __name__=='__main__':unittest.main()
