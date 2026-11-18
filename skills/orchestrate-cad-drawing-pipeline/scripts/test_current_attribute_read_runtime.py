import json,os,shutil,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
for n in ['build-cad-pipe-topology','visualize-cad-pipe-topology']:sys.path.insert(0,str(ROOT/n/'scripts'))
import native_replay_session as observer
import reuse_verified_native_artifact as cache
import refresh_reviewed_ring_partition_DN as current
import refresh_attribute_templates as legacy
from current_attribute_read_runtime import current_attribute_read_runtime,command,command_inputs,module_closure
from build_current_attribute_reader_policy import build
from capture_current_readonly_inputs import combine_observed_closure,reobserve_initialized_inputs

class CurrentReaderTests(unittest.TestCase):
    def fixture(self,temp):
        p=Path(temp)/'bundle/public';p.mkdir(parents=True);(p/'data').mkdir()
        for js in(ROOT/'visualize-cad-pipe-topology/assets/viewer/public').glob('*.js'):shutil.copy2(js,p/js.name)
        (p/'app.js').write_text("import { crossViewAttributeCsvValues } from './edge-attributes-effective-provider.js';",encoding='utf8')
        (p/'data/graph.json').write_text('{"edges":[{"edge_id":"E0001","system":"supply","path":[],"path_length":17}]}',encoding='utf8')
        (p/'data/manifest.json').write_text('{"attributeValueContext":{}}',encoding='utf8')
        return p.parent
    def policy(self):return ROOT/'orchestrate-cad-drawing-pipeline/assets/current-attribute-reader-policy.json'

    def test_actual_current_facade_output_and_exact_input_closure(self):
        with tempfile.TemporaryDirectory()as temp:
            bundle=self.fixture(temp);expected=current.effective(bundle)
            self.assertEqual(expected[0]['edge_id'],'E0001')
            with current_attribute_read_runtime(ROOT,self.policy())as runtime:
                with cache.capture(observer)as reads:actual=current.effective(bundle)
                self.assertEqual(runtime.stats['tracked_node_reads'],1)
            self.assertEqual(actual,expected);closed=cache.closure_payload(reads)
            self.assertTrue(cache.check_closure(closed,observer,2));self.assertIn(os.path.normcase(str(bundle/'public/app.js')),closed['files'])
            self.assertTrue(any(n.endswith('edge-attributes-effective-provider.js')for n in closed['files']))

    def test_legacy_absolute_entry_remains_original_output(self):
        with tempfile.TemporaryDirectory()as temp:
            bundle=self.fixture(temp);expected=legacy.effective_attributes(bundle)
            with current_attribute_read_runtime(ROOT,self.policy())as runtime:
                with cache.capture(observer)as reads:actual=legacy.effective_attributes(bundle)
                self.assertEqual(runtime.stats['tracked_node_reads'],1)
            self.assertEqual(actual,expected);self.assertTrue(cache.check_closure(cache.closure_payload(reads),observer,2))

    def test_same_size_same_timestamp_data_change_and_new_package_invalidate(self):
        with tempfile.TemporaryDirectory()as temp:
            bundle=self.fixture(temp);path=bundle/'public/data/graph.json'
            with current_attribute_read_runtime(ROOT,self.policy()):
                with cache.capture(observer)as reads:current.effective(bundle)
            closed=cache.closure_payload(reads);before=path.stat();raw=path.read_bytes();path.write_bytes(raw.replace(b':17',b':18'));os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns));self.assertFalse(cache.check_closure(closed,observer,2))
            path.write_bytes(raw);os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns));self.assertTrue(cache.check_closure(closed,observer,2));(bundle/'package.json').write_text('{"type":"module"}');self.assertFalse(cache.check_closure(closed,observer,2))

    def test_unapproved_module_and_node_options_keep_original_unsafe_boundary(self):
        for kind in ['module','NODE_OPTIONS','NODE_PATH']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory()as temp:
                bundle=self.fixture(temp)
                if kind=='module':
                    p=bundle/'public/edge-attributes-effective-provider.js';p.write_text(p.read_text('utf8')+'\n// unapproved change\n',encoding='utf8')
                with patch.dict(os.environ,{kind:'--no-warnings'if kind=='NODE_OPTIONS'else temp}if kind!='module'else{}):
                    with current_attribute_read_runtime(ROOT,self.policy())as runtime:
                        with cache.capture(observer)as reads:current.effective(bundle)
                        self.assertEqual(runtime.stats['original_fallbacks'],1)
                self.assertFalse(reads.cacheable)

    def test_late_mutation_rejected_without_accepting_changed_values(self):
        with tempfile.TemporaryDirectory()as temp:
            bundle=self.fixture(temp);original=current.subprocess.run
            def mutate(*args,**kwargs):
                result=original(*args,**kwargs);p=bundle/'public/data/graph.json';p.write_text(p.read_text().replace(':17',':18'));return result
            with current_attribute_read_runtime(ROOT,self.policy()),patch.object(current.subprocess,'run',mutate):
                with self.assertRaisesRegex(ValueError,'changed during'),cache.capture(observer):current.effective(bundle)

    def test_existing_and_late_aliases_restore_with_compare_and_swap(self):
        name='_current_reader_test_alias';module=types.ModuleType(name);module.__file__=str(ROOT/'orchestrate-cad-drawing-pipeline/scripts/alias.py');original=current.effective;module.before=original;sys.modules[name]=module
        try:
            with current_attribute_read_runtime(ROOT,self.policy()):
                self.assertIs(module.before,current.effective);self.assertIsNot(module.before,original);module.late=current.effective
                changed=lambda x:None;module.foreign=current.effective;module.foreign=changed
            self.assertIs(module.before,original);self.assertIs(module.late,original);self.assertIs(module.foreign,changed);self.assertIs(current.effective,original)
        finally:del sys.modules[name]

    def test_command_construction_never_executes_node(self):
        with tempfile.TemporaryDirectory()as temp:
            bundle=self.fixture(temp)
            with patch.object(current.subprocess,'run',side_effect=AssertionError('must not run')):argv=command(current.effective,bundle)
            entry,graph,manifest,_=command_inputs(argv,bundle);self.assertEqual(entry,bundle/'public/edge-attributes-effective-provider.js');self.assertEqual(graph,bundle/'public/data/graph.json')
            argv[-1]='../outside.js'
            with self.assertRaises(ValueError):command_inputs(argv,bundle)

    def test_external_dynamic_and_symlink_modules_cannot_be_sealed(self):
        with tempfile.TemporaryDirectory()as temp:
            p=Path(temp)/'reader.js'
            for raw in ["import x from 'node:fs';", "export const x=import('./other.js');", "export const x=fetch('x');"]:
                p.write_text(raw)
                with self.assertRaises(ValueError):module_closure(p)

    def test_forged_current_audit_digest_is_not_a_trust_anchor(self):
        with tempfile.TemporaryDirectory()as temp:
            bundle=self.fixture(temp);(bundle/'effective-provider-refresh.json').write_text('{"output_hashes":{}}')
            with self.assertRaisesRegex(ValueError,'trust anchor'):build(ROOT,bundle,'0'*64)

    def test_all_previously_qualified_legacy_versions_are_inherited(self):
        old=json.loads((ROOT/'orchestrate-cad-drawing-pipeline/assets/pure-attribute-reader-policy.json').read_text('utf8'));new=json.loads(self.policy().read_text('utf8'))
        for name,versions in old['module_sha256'].items():self.assertTrue(set(versions)<=set(new['module_sha256'].get(name,[])),name)

    def test_child_witnessed_parent_file_hashes_retains_old_module_and_rejects_tampering(self):
        from native_attribute_read_runtime import sha
        with tempfile.TemporaryDirectory()as temp:
            bundle=self.fixture(temp);parent=Path(temp)/'old-viewer';(parent/'public/data').mkdir(parents=True);(parent/'public/data/manifest.json').write_text('{}')
            js=parent/'public/historical-reader.js';js.write_text('export const historical=1;')
            audit=bundle/'old-refresh.json';audit.write_text(json.dumps(dict(parent=str(parent),parent_file_hashes={'public/historical-reader.js':sha(js)})))
            anchor=bundle/'effective-provider-refresh.json';anchor.write_text(json.dumps(dict(output_hashes={'old-refresh.json':sha(audit)})))
            policy=build(ROOT,bundle,sha(anchor));self.assertIn(sha(js),policy['module_sha256']['historical-reader.js'])
            js.write_text('export const historical=2;')
            with self.assertRaisesRegex(ValueError,'audited frontend module bytes'):build(ROOT,bundle,sha(anchor))

    def test_policy_change_rejected_and_functions_restored(self):
        with tempfile.TemporaryDirectory()as temp:
            bundle=self.fixture(temp);policy=Path(temp)/'policy.json';shutil.copy2(self.policy(),policy);before=current.effective
            with self.assertRaisesRegex(ValueError,'policy changed'):
                with current_attribute_read_runtime(ROOT,policy):
                    policy.write_text(policy.read_text()+' ')
                    with cache.capture(observer):current.effective(bundle)
            self.assertIs(current.effective,before)

    def test_json_native_states_and_original_import_tuples_merge_without_false_conflict(self):
        with tempfile.TemporaryDirectory()as temp:
            p=Path(temp)/'input';p.write_text('original input');initial=observer._Reads(True);initial.files[str(p)]=observer._file_state(p);initial.empty_read_probes=set();captured=cache.closure_payload(initial)
            combined=combine_observed_closure(captured,initial,observer);self.assertTrue(combined.cacheable);self.assertTrue(cache.check_closure(cache.closure_payload(combined),observer,2))
            p.write_text('changed input');self.assertFalse(cache.check_closure(cache.closure_payload(combined),observer,2))

    def test_owned_setup_read_reobservation_retains_original_false_flag_and_detects_drift(self):
        with tempfile.TemporaryDirectory()as temp:
            p=Path(temp)/'configuration';p.write_text('runtime config');initial=observer._Reads(True);initial.files[str(p)]=observer._file_state(p);initial.empty_read_probes=set();initial.cacheable=False
            current_reads=reobserve_initialized_inputs(initial,observer);self.assertFalse(initial.cacheable);self.assertTrue(current_reads.cacheable);self.assertTrue(cache.check_closure(cache.closure_payload(current_reads),observer,2))
            p.write_text('configuration changed')
            with self.assertRaisesRegex(ValueError,'runtime initialization changed'):reobserve_initialized_inputs(initial,observer)

if __name__=='__main__':unittest.main()
