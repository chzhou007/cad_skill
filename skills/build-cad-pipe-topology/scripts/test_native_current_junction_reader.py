import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
from confirm_crossview_paths import sha
from native_current_junction_reader import make_reader

class Tests(unittest.TestCase):
    def scope(self,folder,projected=False):
        source=Path(folder)/'source.dxf';source.write_text('中文原图快照',encoding='utf8');sp=dict(path=str(source),sha256=sha(source))
        graph=dict(nodes=[dict(node_id='N',source_reviewed_circle={'circle':'C'},expert_circle_evidence={'circle':'C'}if projected else{})],edges=[])
        p=Path(folder)/'graph.json';p.write_text(json.dumps(graph),encoding='utf8');gp=dict(path=str(p),sha256=sha(p))
        m=dict(plans=[dict(inputs=dict(source=sp,graph=gp),circle_main_lineage_parents=[])],projected_circle_expert_authorities=[])
        return m,graph,sp['sha256'],gp['sha256']
    def test_old_normalized_circle_adapter_is_reused_without_DN(self):
        with tempfile.TemporaryDirectory()as f:
            m,g,sh,gh=self.scope(f)
            with patch('native_current_junction_reader.native_tee',side_effect=ValueError('reviewed main child identity differs')),patch('current_circle_plan_DN.circle_collect',return_value={'current_main_lineage':True})as inherited:
                proof=make_reader(m,sh,gh)(None,g,'N',sh,gh)
                self.assertTrue(proof['current_main_lineage']);inherited.assert_called_once_with(None,g,'N',sh,gh,[])
    def test_projected_source_role_is_reused_only_for_explicit_flag(self):
        with tempfile.TemporaryDirectory()as f:
            m,g,sh,gh=self.scope(f,True)
            with patch('native_current_junction_reader.native_tee',side_effect=ValueError('missing or ambiguous graph T ray')),patch('native_current_junction_reader.projected_collect',return_value={'native_projection':True})as inherited:
                self.assertTrue(make_reader(m,sh,gh)(None,g,'N',sh,gh)['native_projection']);inherited.assert_called_once()
    def test_geometry_error_does_not_fall_through_to_another_rule(self):
        with tempfile.TemporaryDirectory()as f:
            m,g,sh,gh=self.scope(f,True)
            with patch('native_current_junction_reader.native_tee',side_effect=ValueError('native source ray changed')),patch('native_current_junction_reader.projected_collect')as other:
                with self.assertRaisesRegex(ValueError,'native source ray changed'):make_reader(m,sh,gh)(None,g,'N',sh,gh)
                other.assert_not_called()
    def test_changed_source_and_other_scope_are_rejected(self):
        with tempfile.TemporaryDirectory()as f:
            m,g,sh,gh=self.scope(f)
            reader=make_reader(m,sh,gh)
            with self.assertRaisesRegex(ValueError,'another native scope'):reader(None,g,'N','other',gh)
            Path(m['plans'][0]['inputs']['source']['path']).write_text('changed',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'input changed'):make_reader(m,sh,gh)
    def test_missing_or_duplicate_configuration_is_not_guessed(self):
        with tempfile.TemporaryDirectory()as f:
            m,g,sh,gh=self.scope(f);m['plans']*=2
            with self.assertRaisesRegex(ValueError,'one exact'):make_reader(m,sh,gh)
            m['plans']=[]
            with self.assertRaisesRegex(ValueError,'one exact'):make_reader(m,sh,gh)
    def test_calibrated_duplicate_circle_uses_inherited_source_incidence_only(self):
        with tempfile.TemporaryDirectory()as f:
            m,g,sh,gh=self.scope(f);g['nodes'][0]['calibrated_duplicate_circle']={'physical_main_identity':'unresolved'}
            with patch('native_inherited_duplicate_circle_evidence.collect',return_value={'physical_main_identity':'unresolved','incidence':'source_replayed'})as inherited,patch('native_current_junction_reader.native_tee')as ordinary:
                proof=make_reader(m,sh,gh)(None,g,'N',sh,gh)
                self.assertEqual(proof['physical_main_identity'],'unresolved');inherited.assert_called_once_with(None,g,'N',sh,gh,None);ordinary.assert_not_called()

if __name__=='__main__':unittest.main()
