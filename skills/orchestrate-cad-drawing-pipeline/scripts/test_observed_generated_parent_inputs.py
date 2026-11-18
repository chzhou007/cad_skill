"""Preserve original proved-parent roles when producer observation is enabled."""
import json,os,unittest
from pathlib import Path
import producer_input_observation as observation
import build_producer_input_policy as builder
import test_generated_local_parent_inputs as generated
import test_producer_input_observation as observer_fixture
import test_build_producer_input_policy as policies

class ObservedGeneratedParentTests(unittest.TestCase):
    setUp=generated.GeneratedParentInputTests.setUp
    runtime=generated.GeneratedParentInputTests.runtime
    observed=observer_fixture.ProducerObservationTests.observed
    finish=observer_fixture.ProducerObservationTests.finish
    def test_original_fresh_parent_proof_is_inherited_without_a_seed(self):
        runtime,obs=self.observed(strict=True)
        with obs.call('open',runtime.open,(self.historical,),dict(encoding='utf8'))as stream:
            self.assertEqual(stream.read(),'新生成的父图')
        report=self.finish(obs);self.assertTrue(report['strict_API_input_gate_passed'])
        provenance=report['events'][0]['provenance']
        self.assertEqual(provenance['role'],'qualified_fresh_parent')
        self.assertEqual(provenance['producer_receipt_sha256'],self.row['producer_receipt_sha256'])
        self.assertFalse(report['owned_seed_hashes'])
    def test_receipt_content_and_write_guards_are_not_bypassed(self):
        runtime,obs=self.observed(strict=True)
        with self.assertRaises(PermissionError):obs.call('open',runtime.open,(self.fresh,'w'),{},True,True)
        self.receipt.write_text('{}',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'producer receipt changed'):
            obs.call('open',runtime.open,(self.historical,),{})
    def test_historical_same_hash_copy_stays_forbidden(self):
        runtime,obs=self.observed(strict=True)
        with self.assertRaisesRegex(ValueError,'Historical final graph'):
            obs.call('open',runtime.open,(self.fixed,),{})

class GeneratedParentPolicyTests(unittest.TestCase):
    refresh=policies.PolicyDerivationTests.refresh
    compute=policies.PolicyDerivationTests.compute
    def setUp(self):
        policies.PolicyDerivationTests.setUp(self)
        self.fresh=self.run/'work/fresh.json';self.fresh.write_text('实际新父图',encoding='utf8')
        self.proof=self.run/'work/producer.json'
        self.proof.write_bytes(builder.encode(dict(mode='raw_CAD_to_current_local_topology_delivered_API_input_replay_v1',
            local_topologies=[dict(graph_and_component_bytes_exact=True,graph=builder.pin(self.fresh))])))
        self.parent=dict(relative='fresh.json',sha256=builder.sha(self.fresh),producer_receipt_relative='producer.json',
            producer_receipt_sha256=builder.sha(self.proof),producer_field=['local_topologies',0,'graph'])
        self.index['generated_local_parents']={'historical-graph':self.parent}
        self.index['forbidden_historical_final_graph_hashes']=[builder.sha(self.fresh)]
        self.reports[0]['immutable_inputs'][str(self.fresh)]=dict(kind='file',sha256=builder.sha(self.fresh))
        self.refresh()
    def test_proved_output_is_not_promoted_to_seed_or_package_file(self):
        policy,proof=self.compute()
        self.assertNotIn(str(self.fresh),policy['additional_files'])
        self.assertNotIn('fresh.json',policy['owned_seeds'])
        self.assertEqual(len(proof['qualified_generated_parent_inputs']),1)
        self.assertEqual(proof['qualified_generated_parent_inputs'][0]['producer_field'],['local_topologies',0,'graph'])
    def test_parent_bytes_and_original_proof_changes_are_rejected(self):
        self.proof.write_text('{}')
        with self.assertRaisesRegex(ValueError,'producer receipt changed'):self.compute()
    def test_reference_role_and_escaping_source_stay_unqualified(self):
        self.parent['producer_field'][-1]='reference_graph';self.refresh()
        with self.assertRaisesRegex(ValueError,'actual output role'):self.compute()
        self.parent['relative']='../escape.json';self.refresh()
        with self.assertRaisesRegex(ValueError,'escaped actual work'):self.compute()
if __name__=='__main__':unittest.main()
