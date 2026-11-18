import json,os,shutil,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'visualize-cad-pipe-topology/scripts'))
import refresh_attribute_templates as reader
import native_replay_session as observer
import reuse_verified_native_artifact as cache
from native_attribute_read_runtime import Runtime,attribute_read_runtime


class Tests(unittest.TestCase):
    def fixture(self,temp):
        p=Path(temp)/'bundle/public';p.mkdir(parents=True);(p/'data').mkdir()
        for js in (ROOT/'visualize-cad-pipe-topology/assets/viewer/public').glob('*.js'):shutil.copy2(js,p/js.name)
        (p/'data/graph.json').write_text('{"edges":[]}',encoding='utf-8')
        (p/'data/manifest.json').write_text('{"attributeValueContext":{}}',encoding='utf-8')
        return p.parent

    def test_exact_original_reader_output_gains_current_byte_closure(self):
        with tempfile.TemporaryDirectory()as temp:
            bundle=self.fixture(temp)
            with cache.capture(observer)as original:expected=reader.effective_attributes(bundle)
            self.assertFalse(original.cacheable)
            before=reader.effective_attributes
            with attribute_read_runtime(ROOT)as runtime:
                with cache.capture(observer)as reads:actual=reader.effective_attributes(bundle)
                self.assertEqual(runtime.stats['tracked_node_reads'],1)
            self.assertIs(reader.effective_attributes,before);self.assertEqual(actual,expected)
            closure=cache.closure_payload(reads);self.assertTrue(cache.check_closure(closure,observer,2))
            data=bundle/'public/data/graph.json';prior=data.stat();data.write_text('{"edges": []}',encoding='utf-8');os.utime(data,ns=(prior.st_atime_ns,prior.st_mtime_ns))
            self.assertFalse(cache.check_closure(closure,observer,2))

    def test_new_package_file_and_same_size_timestamp_graph_change_invalidate(self):
        with tempfile.TemporaryDirectory()as temp:
            bundle=self.fixture(temp);data=bundle/'public/data/graph.json';data.write_text('{"edges":[],"tag":"a"}',encoding='utf-8')
            with attribute_read_runtime(ROOT):
                with cache.capture(observer)as reads:reader.effective_attributes(bundle)
            closed=cache.closure_payload(reads);before=data.stat();data.write_text('{"edges":[],"tag":"b"}',encoding='utf-8');os.utime(data,ns=(before.st_atime_ns,before.st_mtime_ns));self.assertFalse(cache.check_closure(closed,observer,2))
            data.write_text('{"edges":[],"tag":"a"}',encoding='utf-8');os.utime(data,ns=(before.st_atime_ns,before.st_mtime_ns));self.assertTrue(cache.check_closure(closed,observer,2))
            (bundle/'public/package.json').write_text('{"type":"module"}',encoding='utf-8');self.assertFalse(cache.check_closure(closed,observer,2))

    def test_unknown_module_or_node_startup_options_keep_original_uncacheable_path(self):
        for kind in('module','NODE_OPTIONS','NODE_PATH'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory()as temp:
                bundle=self.fixture(temp)
                if kind=='module':
                    p=bundle/'public/edge-attributes.js';p.write_text(p.read_text('utf-8')+'\n// changed unapproved source\n',encoding='utf-8')
                with patch.dict(os.environ,{kind:'--no-warnings'if kind=='NODE_OPTIONS'else temp}if kind!='module'else{}):
                    with attribute_read_runtime(ROOT)as runtime:
                        with cache.capture(observer)as reads:self.assertEqual(reader.effective_attributes(bundle),[])
                        self.assertEqual(runtime.stats['original_fallbacks'],1)
                self.assertFalse(reads.cacheable)

    def test_late_input_mutation_raises_instead_of_reusing_result(self):
        with tempfile.TemporaryDirectory()as temp:
            bundle=self.fixture(temp);original=reader.subprocess.run
            def mutate(*args,**kwargs):
                result=original(*args,**kwargs);(bundle/'public/data/graph.json').write_text('{"edges":[],"changed":true}',encoding='utf-8');return result
            with attribute_read_runtime(ROOT),patch.object(reader.subprocess,'run',mutate):
                with self.assertRaisesRegex(ValueError,'changed during'),cache.capture(observer):reader.effective_attributes(bundle)

    def test_policy_change_raises_and_restores_original_functions(self):
        with tempfile.TemporaryDirectory()as temp:
            bundle=self.fixture(temp);policy=Path(temp)/'policy.json';shutil.copy2(ROOT/'orchestrate-cad-drawing-pipeline/assets/pure-attribute-reader-policy.json',policy);before=reader.effective_attributes
            with self.assertRaisesRegex(ValueError,'policy changed'):
                with attribute_read_runtime(ROOT,policy):
                    policy.write_text(policy.read_text('utf-8')+' ',encoding='utf-8')
                    with cache.capture(observer):reader.effective_attributes(bundle)
            self.assertIs(reader.effective_attributes,before)

if __name__=='__main__':unittest.main()
