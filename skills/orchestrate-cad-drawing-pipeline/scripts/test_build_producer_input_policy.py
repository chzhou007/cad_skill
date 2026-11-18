import json
from pathlib import Path
import tempfile
import unittest

import build_producer_input_policy as builder


class PolicyDerivationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.package=self.root/'package';self.package.mkdir()
        (self.package/'data').mkdir();self.source=self.package/'data/source.txt';self.source.write_text('中文原始数据',encoding='utf8')
        (self.package/'helper.py').write_text('original helper fixture',encoding='utf8')
        (self.package/'helper-policy.json').write_text('{}',encoding='utf8')
        (self.package/'seed.json').write_text('{"runtime":"cache"}',encoding='utf8')
        self.run=self.root/'run';self.receipts=self.run/'work/producer-observation';self.receipts.mkdir(parents=True)
        self.result_path=self.run/'execution-result.json';self.seeds=self.root/'seeds.json'
        self.seeds.write_bytes(builder.encode(dict(schema='delivered_producer_startup_seed_bindings_v1',seeds=[dict(relative='runtime-cache/seed.json',source_relative='seed.json',sha256=builder.sha(self.package/'seed.json'),role='runtime_cache_seed')])))
        self.index=dict(producer_observation=dict(relative='helper.py',sha256=builder.sha(self.package/'helper.py'),
            policy_relative='helper-policy.json',policy_sha256=builder.sha(self.package/'helper-policy.json')),forbidden_historical_final_graph_hashes=[])
        self.reports=[]
        for pid,parent in [(12345,9876),(12346,12345)]:
            self.reports.append(dict(mode='producer_API_input_discovery_v1',pid=pid,parent_pid=parent,input_index_sha256='',
                changed_inputs=[],helper_binding=self.index['producer_observation'],
                immutable_inputs={str(self.source):dict(kind='file',sha256=builder.sha(self.source),bytes=self.source.stat().st_size),
                    str(self.package/'data'):dict(kind='directory',entries=['source.txt']),
                    str(self.package/'missing.json'):dict(kind='missing',errno=2)},unresolved=[]))
        self.refresh()

    def refresh(self):
        path=self.package/'logical-input-index.json';path.write_bytes(builder.encode(self.index));digest=builder.sha(path)
        rows=[]
        for report in self.reports:
            report['input_index_sha256']=digest
            path=self.receipts/(str(report['pid'])+'.json');path.write_bytes(builder.encode(report))
            rows.append(dict(path=str(path),sha256=builder.sha(path),pid=report['pid'],parent_pid=report['parent_pid']))
        result=dict(status='producer_command_returned',exit_code=0,strict_production_closure_not_inferred_from_exit_code=True,
            actual_root_pid=12345,observations=rows,access_receipts=[dict(pid=r['pid'],unrecorded_reads=[])for r in rows])
        self.result_path.write_bytes(builder.encode(result))

    def compute(self):
        return builder.compute(self.result_path,self.package,self.seeds)

    def test_deduplicate_actual_states_without_assigning_CAD_values_or_certifying_unseen_processes(self):
        policy,proof=self.compute()
        self.assertEqual(policy['mode'],'producer_API_input_enforcement_v1')
        self.assertEqual(len(policy['additional_files']),1)
        self.assertEqual(len(policy['directories']),1)
        self.assertEqual(policy['negative'],[str(self.package/'missing.json')])
        self.assertEqual(proof['observed_processes'],2)
        self.assertTrue(proof['strict_producer_execution_required'])
        self.assertEqual(proof['raw_CAD_values_assigned'],0)

    def test_output_rederives_and_refuses_overwrite_or_modified_policy(self):
        output=self.root/'strict-policy'
        builder.produce(self.result_path,self.package,self.seeds,output)
        builder.verify(output)
        with self.assertRaisesRegex(ValueError,'Fresh'):
            builder.produce(self.result_path,self.package,self.seeds,output)
        (output/'policy.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'policy differs'):
            builder.verify(output)

    def test_changed_receipt_rejected(self):
        (self.receipts/'12346.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'receipt moved or changed'):self.compute()

    def test_changed_same_range_source_file_rejected(self):
        self.source.write_text('替换后的输入',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'file changed'):self.compute()

    def test_directory_and_missing_states_cannot_be_silently_rebound(self):
        (self.package/'data/new.txt').write_text('new member')
        with self.assertRaisesRegex(ValueError,'directory state changed'):self.compute()
        (self.package/'data/new.txt').unlink()
        (self.package/'missing.json').write_text('now exists')
        with self.assertRaisesRegex(ValueError,'missing input appeared'):self.compute()

    def test_unrelated_process_and_input_changes_not_qualified(self):
        self.reports[1]['parent_pid']=99999;self.refresh()
        with self.assertRaisesRegex(ValueError,'Unrelated process'):self.compute()
        self.reports[1]['parent_pid']=12345;self.reports[1]['changed_inputs']=[dict(path='changed')];self.refresh()
        with self.assertRaisesRegex(ValueError,'input changes'):self.compute()

    def test_adapter_misses_not_hidden_by_successful_exit(self):
        result=builder.load(self.result_path);result['access_receipts'][1]['unrecorded_reads']=[dict(path='unrecorded')]
        self.result_path.write_bytes(builder.encode(result))
        with self.assertRaisesRegex(ValueError,'unrecorded input'):self.compute()

    def test_unproved_owned_read_not_promoted_from_a_final_output(self):
        self.reports[0]['unresolved']=[dict(path=str(self.run/'work/final.json'),role='owned_output',state=dict(kind='file',sha256='0'*64))]
        self.refresh()
        with self.assertRaisesRegex(ValueError,'Unproved owned reads'):self.compute()

    def test_seed_escape_and_historical_final_hash_rejected(self):
        seeds=builder.load(self.seeds);seeds['seeds'][0]['relative']='../final.json';self.seeds.write_bytes(builder.encode(seeds))
        with self.assertRaisesRegex(ValueError,'Invalid package-relative'):self.compute()
        seeds['seeds'][0]['relative']='runtime-cache/seed.json';self.seeds.write_bytes(builder.encode(seeds))
        self.index['forbidden_historical_final_graph_hashes']=[builder.sha(self.package/'seed.json')];self.refresh()
        with self.assertRaisesRegex(ValueError,'historical final graph'):self.compute()

    def test_positive_input_outside_package_and_unsupported_errors_remain_held(self):
        outside=self.root/'outside.txt';outside.write_text('not delivered')
        self.reports[0]['immutable_inputs'][str(outside)]=dict(kind='file',sha256=builder.sha(outside));self.refresh()
        with self.assertRaisesRegex(ValueError,'outside the delivered package'):self.compute()
        del self.reports[0]['immutable_inputs'][str(outside)]
        self.reports[0]['immutable_inputs'][str(self.package/'unknown-resource')]=dict(kind='stat_error',errno=13);self.refresh()
        with self.assertRaisesRegex(ValueError,'Unsupported resource'):self.compute()


if __name__=='__main__':unittest.main()
