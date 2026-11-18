import tempfile,unittest,os,subprocess
from pathlib import Path
from capture_current_delivery_inputs import observed_input_states,compare_bindings,process_event_metadata
import native_replay_session as observer
from reuse_verified_native_artifact import norm

class ObservedInputTests(unittest.TestCase):
    def test_list_process_arguments_keep_readonly_and_native_parent_categories(self):
        self.assertTrue(process_event_metadata('node',['node','--input-type=module','-e','trusted reader'],None)['node_inline_reader'])
        self.assertEqual(process_event_metadata('python',['python','reuse-native-artifact','--native-run','case'],None)['recognized_native_parent_command'],'reuse-native-artifact')
    @unittest.skipUnless(os.name=='nt','Windows audit passes a command-line string')
    def test_windows_string_arguments_decode_quotes_without_running_a_process(self):
        cmd=['node','--input-type=module','-e','console.log("a b\\\\c")','E:\\a b\\viewer'];r=process_event_metadata(None,subprocess.list2cmdline(cmd),None);self.assertTrue(r['windows_command_line_decoded']);self.assertTrue(r['node_inline_reader']);self.assertEqual(r['executable'],'node')
        cmd=['python','reuse-bounded-attribute-artifact','--native-run','E:\\a b\\case'];self.assertEqual(process_event_metadata(None,subprocess.list2cmdline(cmd),None)['recognized_native_parent_command'],'reuse-bounded-attribute-artifact')
    def test_resolver_evolution_never_becomes_a_reusable_binding_or_hides_code_drift(self):
        before=dict(sys_path=['original'],runtime_and_skill_files={'a':'old'},environment_sha256='same');after=dict(before,sys_path=['imported','original']);r=compare_bindings(before,after);self.assertFalse(r['runtime_bindings_exact']);self.assertTrue(r['immutable_runtime_code_and_context_exact']);self.assertFalse(r['reusable_binding_proven'])
        after['runtime_and_skill_files']={'a':'changed'};self.assertFalse(compare_bindings(before,after)['immutable_runtime_code_and_context_exact'])
    def test_positive_and_negative_dependencies_both_checked_without_completeness_claim(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);p=root/'source.json';p.write_text('source');missing=root/'absent.json';names=[str(p),str(missing)];closure=dict(files={n:norm(observer._file_state(n))for n in names},directories={},probes=[])
            r=observed_input_states(closure,observer);self.assertEqual(r['status'],'observed_states_exact');self.assertEqual(len(r['positive_files']),1);self.assertEqual(len(r['negative_file_states']),1);self.assertFalse(r['process_inputs_proven_complete'])
            missing.write_text('new input');self.assertEqual(observed_input_states(closure,observer)['changed'][0]['path'],str(missing))
    def test_same_size_changed_bytes_and_directory_addition_detected(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);p=root/'a';p.write_text('aaa');closure=dict(files={str(p):norm(observer._file_state(str(p)))},directories={str(root):norm(observer._dir_state(str(root)))},probes=[])
            p.write_text('bbb');self.assertTrue(observed_input_states(closure,observer)['changed']);p.write_text('aaa');(root/'new').write_text('');self.assertTrue(any(r.get('kind')=='directory'for r in observed_input_states(closure,observer)['changed']))

if __name__=='__main__':unittest.main()
