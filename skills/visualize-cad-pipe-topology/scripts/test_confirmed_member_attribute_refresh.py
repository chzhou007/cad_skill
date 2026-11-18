import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import refresh_confirmed_member_attributes as owner

class Tests(unittest.TestCase):
    def test_refresh_of_previously_refreshed_bundle_preserves_history_and_gets_new_HIL_identity(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);parent=root/'parent';(parent/'public/data').mkdir(parents=True);templates=root/'templates';(templates/'public').mkdir(parents=True)
            graph=root/'graph.json';graph.write_text(json.dumps(dict(edges=[],sourceFullPlanBatchAttributes={})),encoding='utf8')
            # A nonempty qualified batch activates its existing group context.
            graph.write_text(json.dumps(dict(edges=[],sourceFullPlanBatchAttributes={'qualified':True})),encoding='utf8')
            devices=root/'devices.csv';devices.write_text('name\n',encoding='utf8');source=root/'source.dxf';source.write_text('native',encoding='utf8')
            policy=root/'policy.json';policy.write_text('{"isometric_horizontal_directions_degrees":[0]}',encoding='utf8');member=root/'member.json';member.write_text('{}',encoding='utf8')
            (parent/'public/data/graph.json').write_text('{"edges":[]}',encoding='utf8');(parent/'public/index.html').write_text('OLD-BUNDLE',encoding='utf8')
            script='export function crossViewAttributeCsvValues(){return{}}\n'
            template_hashes={'public/index.html':hashlib.sha256(b'__BUILD_ID__').hexdigest()}
            for name in owner.ALLOWED:
                content=script if name.endswith('edge-attributes.js')else'// template\n'
                (parent/name).write_text(content,encoding='utf8');(templates/name).write_text(content+'// updated\n',encoding='utf8');template_hashes[name]=owner.sha(parent/name)
            manifest=dict(bundleId='OLD-BUNDLE',sourceHashes=dict(graph=owner.sha(graph),devices=owner.sha(devices),main_dxf=owner.sha(source),full_batch_plan_policy=owner.sha(policy)),
                templateHashes=template_hashes,reviewContentHashes=dict(viewer_graph=owner.sha(parent/'public/data/graph.json')))
            (parent/'public/data/manifest.json').write_bytes(owner.encoded(manifest));(parent/'quality-gate.json').write_bytes(owner.encoded(dict(machine_status='PASS',graph_sha256=owner.sha(parent/'public/data/graph.json'))));(parent/'validation-report.json').write_text('{"status":"passed"}',encoding='utf8')
            (parent/'attribute-template-refresh').mkdir();(parent/'attribute-template-refresh/history.json').write_text('old history',encoding='utf8');(parent/'attribute-template-refresh.json').write_text('old owner audit',encoding='utf8')
            (parent/'annotations').mkdir();(parent/'annotations/review.json').write_text('{"bundle_id":"OLD-BUNDLE"}',encoding='utf8');comparison=root/'comparison.json';comparison.write_bytes(owner.encoded(dict(errors=[],graph_sha256=owner.sha(graph))))
            context=dict(child_DN_domains=0);result_context=dict(axis_edges=1)
            with patch('uniform_path_group_DN_context.from_artifact',return_value=context),patch('confirmed_member_plan_attribute_context.from_artifact',return_value=result_context),patch('source_readability.read_source',return_value=(object(),{})),patch('validate_visualization.validate_bundle',return_value=dict(status='passed')),patch('post_drawing_gate.check',return_value=dict(machine_status='PASS')):
                result=owner.refresh(parent,graph,devices,source,None,comparison,templates,root/'output',10345,policy,member)
            output=root/'output';self.assertNotEqual(result['bundle_id'],'OLD-BUNDLE');self.assertFalse(result['human_confirmation_inherited']);self.assertEqual(result['member_plan_run_edges'],1)
            self.assertEqual((output/'attribute-template-refresh/history.json').read_text(),'old history');self.assertEqual((output/'attribute-template-refresh.json').read_text(),'old owner audit')
            self.assertEqual((output/'annotations/review.json').read_bytes(),(parent/'annotations/review.json').read_bytes());self.assertTrue((output/'confirmed-member-attribute-refresh.json').is_file())
            self.assertEqual(json.loads((output/'public/data/manifest.json').read_text())['attributeValueContext']['member_plan_runs'],result_context)
if __name__=='__main__':unittest.main()
