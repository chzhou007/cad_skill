import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from attach_anchored_floor_main_attributes import ROOT,FIELD
from anchored_floor_main_fusion_gate import check
from source_comparison_gate import check as dispatch

class Tests(unittest.TestCase):
    def fixture(self,root):
        parent=root/'parent';parent.mkdir();p=parent/'graph_with_edges.json';p.write_text('{}',encoding='utf-8');ph=hashlib.sha256(p.read_bytes()).hexdigest()
        report=dict(graph_sha256=ph,errors=[],pending=['old unresolved'],status='pending');(parent/'source-comparison-gate.json').write_text(json.dumps(report),encoding='utf-8')
        run=root/'new';run.mkdir();g=run/'graph_with_edges.json';stage=dict(prior_topology_components_and_attributes_preserved=True,related_HIL_confirmation_inherited=False,human_accepted=False,records=[])
        g.write_text(json.dumps({ROOT:stage,'sourceWaveRebasedPlanScopeAdoption':{}}),encoding='utf-8');gh=hashlib.sha256(g.read_bytes()).hexdigest()
        audit=dict(stage=stage,output_graph_sha256=gh,hil_ready=False,parent_graph=dict(path=str(p),sha256=ph),verified_wave_parent=dict(output_graph_sha256=ph))
        return run,g,gh,report,audit
    def test_source_dispatch_precedes_parent_and_retains_complete_old_pending(self):
        with tempfile.TemporaryDirectory() as temp:
            run,g,gh,report,audit=self.fixture(Path(temp))
            with patch('attach_anchored_floor_main_attributes.verify_output',return_value=audit) as replay,patch('wave_plan_scope_adoption_gate.check_wave_plan_scope_adoption') as old:
                result=dispatch(report,gh,run,g)
            replay.assert_called_once();old.assert_not_called();self.assertEqual(result['pending'][0],'old unresolved');self.assertEqual(result['anchored_floor_main_attribute_stage']['source_replay'],'passed');self.assertFalse(result['hil_ready'])
    def test_native_failure_is_reported_as_failed_without_clearing_parent_issues(self):
        with tempfile.TemporaryDirectory() as temp:
            run,g,gh,report,audit=self.fixture(Path(temp))
            with patch('attach_anchored_floor_main_attributes.verify_output',side_effect=ValueError('source changed')):result=dispatch(report,gh,run,g)
            self.assertEqual(result['status'],'failed');self.assertIn('source changed',result['errors'][-1]);self.assertEqual(result['pending'],report['pending'])
    def test_forged_complete_parent_root_or_HIL_blocks(self):
        for case in ('report','root','parent','HIL'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                run,g,gh,report,audit=self.fixture(Path(temp))
                if case=='report':report['pending']=[]
                elif case=='root':audit['stage']=dict(audit['stage'],human_accepted=True)
                elif case=='parent':audit['verified_wave_parent']['output_graph_sha256']='wrong'
                else:audit['hil_ready']=True
                with patch('attach_anchored_floor_main_attributes.verify_output',return_value=audit),self.assertRaises(ValueError):check(run,report,gh,g)
if __name__=='__main__':unittest.main()
