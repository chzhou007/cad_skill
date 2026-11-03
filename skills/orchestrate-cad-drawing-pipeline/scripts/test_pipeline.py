import copy,json,tempfile,unittest
from pathlib import Path
from pipeline import plan,validate,read,write,sha

class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'source.dxf').write_text('immutable CAD fixture')
        self.cfg={'project_id':'CENTER','tasks':[{'task_id':'A','source':'source.dxf','family':'outdoor_plan','tags':['pipe','architecture'],'evidence':['Native plan and layer inventory']} ]}
        self.config=self.root/'batch.json';self.run=self.root/'run'
    def tearDown(self):self.tmp.cleanup()
    def start(self):write(self.config,self.cfg);plan(self.config,self.run);return read(self.run/'A/task-plan.json')
    def save(self,t):write(self.run/'A/task-plan.json',t)
    def complete(self,t):
        for name,s in t['stages'].items():
            if not s['required']:continue
            p=self.run/'A'/f'{name}.json';write(p,{'evidence':'fixture content'})
            role={'source':'inventory','parameters':'parameter_bindings','topology':'graph','architecture':'building_context','source_comparison':'comparison','visualization':'quality'}[name]
            if name=='source_comparison':write(p,{'graph_sha256':sha(self.run/'A/topology.json'),'rounds_completed':1,'native_comparisons':[{'path':'source.json','sha256':sha(self.run/'A/source.json')}],'families':[{'id':'fixture','status':'resolved','source_handles':['L1'],'disposition':'native comparison qualified'}],'algorithm_blockers':[],'unclassified_terminal_count':0})
            a={'path':p.name,'sha256':sha(p),'role':role}
            if role in ('graph','building_context'):a['coordinate_contract']={'frame':'WCS','units':'mm','source_sha256':t['source_sha256']}
            s.update(status='completed',task_id='A',source_sha256=t['source_sha256'],artifacts=[a])
        self.save(t)
    def test_mixed_plan_starts_pending_and_branches_are_independent(self):
        t=self.start();self.assertEqual(validate(self.run)['status'],'pending');self.assertNotIn('parameters',t['stages']['architecture']['depends_on']);self.assertIn('architecture',t['stages']['visualization']['depends_on'])
    def test_all_supported_families_route(self):
        from pipeline import FAMILIES
        for family in FAMILIES:
            with self.subTest(family=family):
                self.cfg['tasks'][0]['family']=family;write(self.config,self.cfg)
                r=self.root/family;plan(self.config,r);self.assertEqual(read(r/'A/task-plan.json')['routing_status'],'completed')
    def test_unknown_stays_pending(self):
        self.cfg['tasks'][0]['family']='unknown';t=self.start();self.complete(t);self.assertEqual(validate(self.run)['status'],'pending')
    def test_completed_contracts(self):t=self.start();self.complete(t);self.assertEqual(validate(self.run)['status'],'completed')
    def test_changed_source_fails(self):
        self.start();(self.root/'source.dxf').write_text('changed');self.assertEqual(validate(self.run)['status'],'failed')
    def test_changed_profile_fails(self):
        (self.root/'profile.json').write_text('{}');self.cfg['profile_files']=['profile.json'];self.start();(self.root/'profile.json').write_text('[]')
        with self.assertRaises(ValueError):validate(self.run)
    def test_completed_without_artifact_fails(self):
        t=self.start();self.complete(t);t['stages']['topology']['artifacts']=[];self.save(t);self.assertEqual(validate(self.run)['status'],'failed')
    def test_cannot_skip_required_stage_or_dependency(self):
        t=self.start();self.complete(t);t['stages']['topology'].update(required=False,status='not_applicable');t['stages']['visualization']['depends_on']=[];self.save(t);self.assertEqual(validate(self.run)['status'],'failed')
    def test_wrong_owner_and_role_fail(self):
        t=self.start();self.complete(t);t['stages']['architecture']['owner']='visualize-cad-pipe-topology';t['stages']['architecture']['artifacts'][0]['role']='graph';self.save(t);self.assertEqual(validate(self.run)['status'],'failed')
    def test_transform_units_mismatch_fails(self):
        t=self.start();self.complete(t);t['stages']['architecture']['artifacts'][0]['coordinate_contract']['units']='m';self.save(t);self.assertEqual(validate(self.run)['status'],'failed')
    def test_path_escape_fails(self):
        t=self.start();self.complete(t);t['stages']['source']['artifacts'][0]['path']='../../source.dxf';self.save(t);self.assertEqual(validate(self.run)['status'],'failed')
    def test_duplicate_task_and_overwrite_rejected(self):
        self.start()
        with self.assertRaises(ValueError):plan(self.config,self.run)
        self.cfg['tasks'].append(copy.deepcopy(self.cfg['tasks'][0]));write(self.config,self.cfg)
        with self.assertRaises(ValueError):plan(self.config,self.root/'new')
    def test_receipt_source_identity_fails(self):
        t=self.start();self.complete(t);t['stages']['topology']['source_sha256']='other';self.save(t);self.assertEqual(validate(self.run)['status'],'failed')
if __name__=='__main__':unittest.main()
