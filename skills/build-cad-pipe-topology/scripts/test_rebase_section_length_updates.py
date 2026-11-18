import copy
import unittest
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from rebase_section_length_updates import apply


class RebaseTest(unittest.TestCase):
    def fixture(self):
        old={'edge_id':'E','system':'supply','source_handles':['L'],
             'attribute_paths':[[[0,0],[5,0]]],'path_points':[[0,0],[6,0]],
             'path_length':6,'source_path_length':5,'semantic_bridge_drawing_length':1,
             'source_connector_handles':['C'],'connection_mode':'source_calibrated_pipe_section_continuity',
             'length_scope':'old'}
        new=dict(old,length_scope='new',length_scope_before_graphic_separation='old',
                 path_length=5,path_length_before_graphic_separation=6,path_length_complete=False,
                 path_length_scope='source_drawn_pipe_only_section_connector_length_unknown')
        def g(edge):return {'metadata':{'source_sha256':'sha'},'nodes':[{'node_id':'N'}],'edges':[edge]}
        return g(old),g(new),g(copy.deepcopy(old))

    def test_rebase_preserves_target_and_sets_pending(self):
        a,b,t=self.fixture();t['edges'][0]['floor_location_text_zh']='一层';old=copy.deepcopy(t)
        r,audit=apply(a,b,t,'sha');self.assertEqual(t,old)
        self.assertEqual(r['edges'][0]['floor_location_text_zh'],'一层')
        self.assertEqual(r['edges'][0]['path_length'],5);self.assertFalse(r['metadata']['hil_ready'])
        self.assertEqual(audit['changed_edge_ids'],['E'])

    def test_geometry_and_system_changes_fail_closed(self):
        for where,key,value in [('target','source_handles',['OTHER']),('variant','system','return'),('variant','path_length',4),('target','path_length',9)]:
            with self.subTest(where=where,key=key):
                a,b,t=self.fixture();(b if where=='variant' else t)['edges'][0][key]=value
                with self.assertRaises(ValueError):apply(a,b,t,'sha')

    def test_wrong_source_fails(self):
        a,b,t=self.fixture()
        with self.assertRaisesRegex(ValueError,'source mismatch'):apply(a,b,t,'other')

    def test_serialized_output_stable_across_hash_seeds(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);a,b,t=self.fixture()
            (p/'fixture.json').write_text(json.dumps([a,b,t]),encoding='utf8')
            code="import json,sys; from rebase_section_length_updates import apply; x=json.load(open(sys.argv[1],encoding='utf8')); print(json.dumps(apply(*x,'sha')[0],ensure_ascii=True))"
            outputs=[]
            for seed in ('1','77','941'):
                env=dict(os.environ,PYTHONHASHSEED=seed)
                r=subprocess.run([sys.executable,'-c',code,str(p/'fixture.json')],cwd=Path(__file__).parent,env=env,capture_output=True,text=True)
                self.assertEqual(r.returncode,0,r.stderr);outputs.append(r.stdout)
            self.assertEqual(len(set(outputs)),1)

    def test_cli_rejects_unpinned_input_before_output(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);a,b,t=self.fixture()
            for name,value in [('control',a),('variant',b),('target',t)]:
                (p/(name+'.json')).write_text(json.dumps(value),encoding='utf8')
            (p/'policy.json').write_text(json.dumps({'source_sha256':'sha','control_sha256':'wrong'}),encoding='utf8')
            cmd=[sys.executable,str(Path(__file__).with_name('rebase_section_length_updates.py'))]
            for name in ('control','variant','target','policy'):
                cmd.extend(['--'+name,str(p/(name+'.json'))])
            r=subprocess.run(cmd+['--output',str(p/'out')],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0);self.assertIn('control graph hash mismatch',r.stderr)
            self.assertFalse((p/'out').exists())


if __name__=='__main__':unittest.main()
