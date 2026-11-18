import copy,json,tempfile,unittest,warnings,zipfile
from pathlib import Path
from audit_historical_skill_inheritance import audit,unit_tests,executed_tests

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.source='build-cad-pipe-topology/scripts/old_rule.py';self.test='build-cad-pipe-topology/scripts/test_old_rule.py'
        self.registry={'features':[dict(id='old',origin='initial_skill',files=[self.source],tests=[self.test],families=['ceiling_plan'],depends_on=[],acceptance_status='unknown',evidence_references=['ref.md'])]}
        self.archive=self.root/'baseline.zip'
        with zipfile.ZipFile(self.archive,'w') as z:
            z.writestr(self.source,'old implementation');z.writestr(self.test,'old test');z.writestr('README.md','archive note')
        for name,text in [(self.source,'improved implementation'),(self.test,'improved test')]:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,'utf8')

    def test_changed_asset_and_registered_old_test_are_preserved_without_native_acceptance(self):
        result=audit(self.archive,self.root,self.registry,{self.test})
        self.assertEqual(result['errors'],[]);self.assertEqual(result['original_skill_assets'],2)
        self.assertEqual(result['archive_only_artifacts'],['README.md']);self.assertTrue(result['assets'][0]['changed_since_original'])
        self.assertFalse(result['whole_historical_native_matrix_passed']);self.assertFalse(result['human_accepted'])

    def test_missing_original_asset_and_unregistered_old_entry_each_block(self):
        missing=self.root/self.source;missing.unlink()
        result=audit(self.archive,self.root,self.registry,{self.test});self.assertTrue(any('missing original' in error for error in result['errors']))
        registry=copy.deepcopy(self.registry);registry['features'][0]['files']=[]
        self.assertTrue(any('unregistered original executable' in error for error in audit(self.archive,self.root,registry,{self.test})['errors']))

    def test_omitted_historical_test_is_not_hidden_by_other_green_units(self):
        result=audit(self.archive,self.root,self.registry,{'build-cad-pipe-topology/scripts/test_new_rule.py'})
        self.assertTrue(any('original test lacks' in error for error in result['errors']))
        self.assertEqual(result['missing_registered_tests'],[self.test])

    def test_unsafe_and_duplicate_archive_members_are_rejected(self):
        for name in ('../escape.py','C:/escape.py'):
            archive=self.root/'unsafe.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr(name,'bad')
            with self.assertRaisesRegex(ValueError,'Unsafe'):audit(archive,self.root,self.registry,{self.test})
        archive=self.root/'duplicate.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(archive,'w') as z:z.writestr(self.source,'a');z.writestr(self.source,'b')
        with self.assertRaisesRegex(ValueError,'Duplicate'):audit(archive,self.root,self.registry,{self.test})

    def test_aggregate_cannot_substitute_a_changed_inherited_report(self):
        inherited=self.root/'old.json';inherited.write_text('{}','utf8');path=self.root/'aggregate.json'
        path.write_text(json.dumps(dict(tests=[self.test],inherited_report=dict(path=str(inherited),sha256='0'*64),supplemental_executions=[])),'utf8')
        with self.assertRaisesRegex(ValueError,'Inherited test report changed'):unit_tests(path)

    def test_declared_report_tests_must_match_passed_execution_commands(self):
        path=self.root/'units.json';execution=dict(skill='build-cad-pipe-topology',exit_code=0,command=['python','-m','unittest','test_old_rule'])
        report=dict(tests=[self.test],executions=[execution]);path.write_text(json.dumps(report),'utf8')
        self.assertEqual(unit_tests(path),{self.test})
        report['tests'].append('build-cad-pipe-topology/scripts/test_unexecuted.py');path.write_text(json.dumps(report),'utf8')
        with self.assertRaisesRegex(ValueError,'do not cover'):unit_tests(path)
        execution['exit_code']=1
        with self.assertRaisesRegex(ValueError,'Failed'):executed_tests([execution])


if __name__=='__main__':unittest.main()
