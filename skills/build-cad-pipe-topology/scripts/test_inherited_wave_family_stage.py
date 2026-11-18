import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from inherited_wave_family_stage import load_policy_map,run_stage,digest,SETTINGS


class Tests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name).resolve()
        task=root/'task';parent=task/'parent/graph_with_edges.json';parent.parent.mkdir(parents=True);parent.write_text('{}','utf8')
        (parent.parent/'assigned_edge_device_instances.csv').write_text('component','utf8')
        source=root/'source.dxf';source.write_text('source','utf8')
        settings={key:root/(key+'.json') for key in SETTINGS}
        for p in settings.values():p.write_text('{}','utf8')
        return root,task,parent,source,settings

    def produce(self,task,parent,source,settings,mutate=None):
        paths=dict(source=source,graph=parent,devices=parent.parent/'assigned_edge_device_instances.csv',**settings)
        dest=task/'topology-inherited-wave-pair-continuity'
        graph=dict(metadata=dict(hil_ready=False),sourceInheritedWavePairContinuity=dict(source_sha256=digest(source),input_graph_sha256=digest(parent),
            physical_lengths_assigned=0,dependent_mapping_attributes_and_HIL_invalidated=True,human_accepted=False))
        if mutate:mutate(graph)
        dest.mkdir(parents=True);target=dest/'graph_with_edges.json';target.write_text(json.dumps(graph),'utf8')
        audit=dict(mode='native_inherited_wave_pair_continuity_v1',inputs={k:dict(path=str(p),sha256=digest(p)) for k,p in paths.items()},
            output_graph_sha256=digest(target),proof=dict(pairs=8,components=204))
        (dest/'inherited-wave-receipt.json').write_text(json.dumps(audit),'utf8')
        return audit

    def test_map_resolves_controls_and_rejects_unknown_or_overridden_current_task_inputs(self):
        root,task,parent,source,settings=self.fixture();p=root/'map.json'
        p.write_text(json.dumps({'T':{key:value.name for key,value in settings.items()}}),'utf8')
        self.assertEqual(load_policy_map(p,{'T'})['T'],settings)
        with self.assertRaisesRegex(ValueError,'unrecognized'):load_policy_map(p,{'OTHER'})
        p.write_text(json.dumps({'T':dict(settings={})}),'utf8')
        with self.assertRaises(ValueError):load_policy_map(p)
        values={key:str(value) for key,value in settings.items()};values['graph']=str(parent);p.write_text(json.dumps({'T':values}),'utf8')
        with self.assertRaisesRegex(ValueError,'only pinned'):load_policy_map(p)
        self.assertEqual(load_policy_map(None),{})

    def test_entry_cannot_substitute_an_external_graph(self):
        root,task,parent,source,settings=self.fixture()
        with patch('inherited_wave_family_stage.subprocess.run') as child:
            with self.assertRaisesRegex(ValueError,'current task graph'):run_stage(source,parent,settings,root/'other-task')
        child.assert_not_called()

    def test_native_output_is_independently_replayed_before_stage_publication(self):
        root,task,parent,source,settings=self.fixture();audit={}
        def child(command,check):
            self.assertTrue(check);self.assertIn(str(parent),command);audit.update(self.produce(task,parent,source,settings))
        with patch('inherited_wave_family_stage.subprocess.run',side_effect=child),patch('inherited_wave_pair_continuity.verify_output',side_effect=lambda path:audit) as verify:
            target,result=run_stage(source,parent,settings,task)
        verify.assert_called_once_with(task/'topology-inherited-wave-pair-continuity');self.assertTrue(target.is_file())
        receipt=json.loads((task/'reports/source-inherited-wave-continuity-stage.json').read_text('utf8'))
        self.assertEqual(receipt['paired_omissions'],8);self.assertEqual(receipt['physical_lengths_assigned'],0)
        self.assertIn('DN_inheritance',receipt['recompute_required']);self.assertFalse(receipt['hil_ready'])

    def test_failed_native_replay_never_writes_stage_receipt(self):
        root,task,parent,source,settings=self.fixture()
        with patch('inherited_wave_family_stage.subprocess.run'),patch('inherited_wave_pair_continuity.verify_output',side_effect=ValueError('native changed')):
            with self.assertRaisesRegex(ValueError,'native changed'):run_stage(source,parent,settings,task)
        self.assertFalse((task/'reports/source-inherited-wave-continuity-stage.json').exists())

    def test_mid_execution_parent_change_cannot_be_published(self):
        root,task,parent,source,settings=self.fixture();audit={}
        def child(command,check):
            audit.update(self.produce(task,parent,source,settings));parent.write_text('changed','utf8')
        with patch('inherited_wave_family_stage.subprocess.run',side_effect=child),patch('inherited_wave_pair_continuity.verify_output',side_effect=lambda path:audit):
            with self.assertRaisesRegex(ValueError,'inputs changed'):run_stage(source,parent,settings,task)
        self.assertFalse((task/'reports/source-inherited-wave-continuity-stage.json').exists())

    def test_unproven_physical_lengths_or_hil_claims_are_rejected(self):
        for key,value in [('physical_lengths_assigned',1),('dependent_mapping_attributes_and_HIL_invalidated',False),('human_accepted',True)]:
            root,task,parent,source,settings=self.fixture();audit={}
            def child(command,check):audit.update(self.produce(task,parent,source,settings,lambda graph:graph['sourceInheritedWavePairContinuity'].update({key:value})))
            with self.subTest(key=key),patch('inherited_wave_family_stage.subprocess.run',side_effect=child),patch('inherited_wave_pair_continuity.verify_output',side_effect=lambda path:audit):
                with self.assertRaisesRegex(ValueError,'evidence or invalidation'):run_stage(source,parent,settings,task)
            self.assertFalse((task/'reports/source-inherited-wave-continuity-stage.json').exists())


if __name__=='__main__':unittest.main()
