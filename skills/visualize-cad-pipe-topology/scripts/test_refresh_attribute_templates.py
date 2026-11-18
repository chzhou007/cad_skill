import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from refresh_attribute_templates import artifact_inventory,encoded,parent_check,revised_manifest,sha

class RefreshTests(unittest.TestCase):
    def test_operational_startup_logs_do_not_invalidate_native_cache(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);(root/'public').mkdir();(root/'public/data.json').write_text('{}',encoding='utf8');(root/'startup-logs').mkdir();(root/'startup-logs/startup.log').write_text('first',encoding='utf8')
            before=artifact_inventory(root);(root/'startup-logs/startup.log').write_text('second',encoding='utf8');self.assertEqual(artifact_inventory(root),before)
            (root/'public/data.json').write_text('{"changed":1}',encoding='utf8');self.assertNotEqual(artifact_inventory(root),before)
    def test_changes_are_strictly_bounded_and_semantics_get_new_identity(self):
        old=dict(bundleId='old',preferredPort=8000,sourceHashes={'graph':'g'},templateHashes={'public/edge-attributes.js':'old'},reviewContentHashes={'viewer_graph':'v'})
        before=copy.deepcopy(old);new=revised_manifest(old,{'public/edge-attributes.js':'new'},'effective','implementation',10401)
        self.assertEqual(old,before);self.assertEqual(new['sourceHashes'],old['sourceHashes']);self.assertNotEqual(new['bundleId'],'old');self.assertFalse(new['attributeTemplateRefresh']['human_confirmation_inherited']);self.assertEqual(new['reviewContentHashes']['effective_edge_attributes'],'effective')
        for changes in ({},{'public/core.js':'bad'},{'public/data/graph.json':'bad'}):
            with self.assertRaises(ValueError):revised_manifest(old,changes,'e','i',10401)
    def test_parent_requires_matching_all_native_inputs_and_qualified_reports(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);parent=root/'parent';(parent/'public/data').mkdir(parents=True)
            inputs={key:root/(key+'.txt')for key in('graph','devices','main_dxf','legend_dxf')}
            for key,path in inputs.items():path.write_text(key,encoding='utf8')
            graph=parent/'public/data/graph.json';graph.write_text('{}',encoding='utf8');(parent/'public/index.html').write_text('build-id',encoding='utf8')
            m=dict(sourceHashes={key:sha(path)for key,path in inputs.items()},bundleId='build-id',templateHashes={'public/index.html':hashlib.sha256(b'__BUILD_ID__').hexdigest()},reviewContentHashes={'viewer_graph':sha(graph)})
            (parent/'public/data/manifest.json').write_bytes(encoded(m));(parent/'quality-gate.json').write_bytes(encoded(dict(machine_status='PASS',graph_sha256=sha(graph))));(parent/'validation-report.json').write_bytes(encoded(dict(status='passed')))
            comparison=root/'comparison.json';comparison.write_bytes(encoded(dict(errors=[],graph_sha256=sha(inputs['graph']))))
            args=(parent,inputs['graph'],inputs['devices'],inputs['main_dxf'],inputs['legend_dxf'],comparison)
            parent_check(*args)
            inputs['devices'].write_text('changed',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'native inputs changed'):parent_check(*args)
            inputs['devices'].write_text('devices',encoding='utf8');(parent/'public/index.html').write_text('tampered',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'template bytes changed'):parent_check(*args)
    def test_unpassed_source_comparison_cannot_qualify_cached_artifact(self):
        # A real complete 576-edge native artifact is exercised separately;
        # this contract test covers the guard before any copying or rendering.
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);(root/'public/data').mkdir(parents=True)
            for key in('graph','devices','source'):(root/key).write_text(key,encoding='utf8')
            (root/'public/data/manifest.json').write_bytes(encoded(dict(sourceHashes={key:sha(root/file)for key,file in [('graph','graph'),('devices','devices'),('main_dxf','source')]})))
            (root/'quality-gate.json').write_text('{}',encoding='utf8');(root/'comparison').write_bytes(encoded(dict(errors=['unresolved deterministic failure'],graph_sha256=sha(root/'graph'))))
            with self.assertRaisesRegex(ValueError,'source comparison'):parent_check(root,root/'graph',root/'devices',root/'source',None,root/'comparison')
if __name__=='__main__':unittest.main()
