from pathlib import Path
import hashlib,json,os,tempfile,unittest
import delivered_source_input_runtime as code
import delivered_node_read_bridge as node
from types import SimpleNamespace

class GeneratedParentInputTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.package=self.root/'package';self.package.mkdir();self.work=self.root/'work';self.work.mkdir()
        self.historical=self.root/'historical.json';self.historical.write_text('old host data',encoding='utf8')
        self.fixed=self.package/'fixed.json';self.fixed.write_text('新生成的父图',encoding='utf8');self.digest=hashlib.sha256(self.fixed.read_bytes()).hexdigest()
        self.fresh=self.work/'fresh.json';self.fresh.write_bytes(self.fixed.read_bytes())
        self.receipt=self.work/'producer.json';self.receipt.write_text(json.dumps(dict(mode='raw_CAD_to_current_local_topology_delivered_API_input_replay_v1',
            local_topologies=[dict(graph_and_component_bytes_exact=True,graph=dict(path='actual native output',sha256=self.digest))])),encoding='utf8')
        self.row=dict(relative='fresh.json',sha256=self.digest,producer_receipt_relative='producer.json',producer_receipt_sha256=hashlib.sha256(self.receipt.read_bytes()).hexdigest(),producer_field=['local_topologies',0,'graph'])
        self.index=dict(files={os.path.normcase(str(self.historical)):dict(relative='fixed.json',sha256=self.digest)},directories={},negative=[],
            generated_local_parents={os.path.normcase(str(self.historical)):self.row},forbidden_historical_final_graph_hashes=[self.digest],adapter_sha256=hashlib.sha256(Path(code.__file__).read_bytes()).hexdigest())
    def runtime(self):
        path=self.package/'logical-input-index.json';path.write_text(json.dumps(self.index),encoding='utf8')
        return code.Runtime(self.package,self.work,hashlib.sha256(path.read_bytes()).hexdigest())
    def test_fresh_source_is_used_and_historical_copy_remains_blocked(self):
        runtime=self.runtime()
        with runtime.open(self.historical,encoding='utf8')as stream:self.assertEqual(stream.read(),'新生成的父图')
        self.assertEqual(self.historical.read_text('utf8'),'old host data')
        self.assertEqual(runtime.stat(self.historical).st_ino,self.fresh.stat().st_ino)
        with self.assertRaisesRegex(ValueError,'Historical final graph'):runtime.open(self.fixed)
    def test_reference_graph_is_not_a_generated_output(self):
        self.row['producer_field'][-1]='reference_graph'
        with self.assertRaisesRegex(ValueError,'actual output role'):self.runtime()
    def test_escape_write_and_content_mutation_are_rejected(self):
        self.row['relative']='../historical.json'
        with self.assertRaisesRegex(ValueError,'escaped'):self.runtime()
        self.row['relative']='fresh.json';runtime=self.runtime()
        with self.assertRaises(PermissionError):runtime.open(self.fresh,'w')
        self.fresh.write_text('different source',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Generated parent bytes changed'):runtime.open(self.historical)
    def test_known_relative_sources_retain_original_project_base(self):
        self.index['historical_read_cwd']=str(self.root);runtime=self.runtime()
        with runtime.open('historical.json',encoding='utf8')as stream:self.assertEqual(stream.read(),'新生成的父图')
        self.assertEqual(runtime.realpath('historical.json'),str(self.historical))
    def test_directory_case_restores_original_identity_only(self):
        logical=self.root/'logical';child=logical/'source-DN';(self.package/'child').mkdir()
        self.index['directories']={os.path.normcase(str(logical)):'.',os.path.normcase(str(child)):'child'}
        self.index['entry_spellings']={os.path.normcase(str(child)):'source-DN'}
        self.assertEqual(self.runtime().listdir(logical),['source-DN'])
        self.index['entry_spellings'][os.path.normcase(str(child))]='other-source'
        with self.assertRaisesRegex(ValueError,'logical identity'):self.runtime()

    def cache_role(self):
        logical=self.root/'historical-cache';manifest=self.package/'cache-role.json'
        manifest.write_text(json.dumps(dict(parent_application=dict(cache_root=str(logical)))),encoding='utf8')
        expected=hashlib.sha256(manifest.read_bytes()).hexdigest();logical_manifest=self.root/'fixed-manifest.json'
        self.index['files'][os.path.normcase(str(logical_manifest))]=dict(relative='cache-role.json',sha256=expected)
        (self.work/'cache').mkdir()
        self.cache=dict(mode='derived_cache_from_fixed_parent_application_v1',relative='cache',
            manifest=str(logical_manifest),manifest_sha256=expected)
        self.index['derived_cache_roots']={str(logical):self.cache}
        return logical,manifest
    def test_fixed_parent_cache_resolves_to_fresh_owned_execution_resource(self):
        logical,manifest=self.cache_role();runtime=self.runtime()
        target=Path(runtime.realpath(logical));self.assertEqual(target,self.work/'cache')
        with runtime.open(target/'new-key.json','w')as stream:stream.write('new derived value')
        self.assertFalse(logical.exists())
        with self.assertRaises(FileNotFoundError):runtime.open(target/'missing-key.json')
        self.assertFalse(runtime.misses)
    def test_cache_requires_fixed_manifest_role_and_matching_original_location(self):
        logical,manifest=self.cache_role();self.cache['manifest_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'fixed delivered input'):self.runtime()
        self.cache['manifest_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
        self.index['derived_cache_roots']={str(self.root/'other-cache'):self.cache}
        with self.assertRaisesRegex(ValueError,'fixed parent role'):self.runtime()
    def test_derived_cache_cannot_escape_or_cover_entire_work_directory(self):
        self.cache_role()
        for relative in ['../escape','.']:
            self.cache['relative']=relative
            with self.assertRaisesRegex(ValueError,'escaped'):self.runtime()

class HistoricalNodeReaderRootsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.root=self.base/'historical/skills'
        self.policy=self.root/'orchestrate-cad-drawing-pipeline/assets/pure-attribute-reader-policy.json'
        self.mode='shipped_pure_attribute_reader_inputs_v1';self.sha='a'*64
        self.binding=dict(root=str(self.root),policy=str(self.policy),sha256=self.sha,mode=self.mode)
        key=lambda p:os.path.normcase(os.path.abspath(p))
        self.checked=[]
        self.runtime=SimpleNamespace(package=self.base/'package',key=key,
            index=dict(qualified_node_reader_roots=[self.binding]),files={key(self.policy):dict(sha256=self.sha)},
            checked_file=lambda p:self.checked.append(p))
        self.owner=SimpleNamespace(root=self.root,policy_path=self.policy,policy=dict(mode=self.mode),policy_hash=self.sha)
    def test_explicit_historical_policy_is_rechecked(self):
        node.qualify_root(self.runtime,self.owner)
        self.assertEqual(self.checked,[self.runtime.key(self.policy)])
    def test_unknown_or_sibling_root_is_rejected(self):
        self.owner.root=self.base/'other/skills'
        with self.assertRaisesRegex(PermissionError,'root or policy'):node.qualify_root(self.runtime,self.owner)
    def test_policy_digest_and_original_binding_cannot_change(self):
        self.owner.policy_hash='b'*64
        with self.assertRaisesRegex(PermissionError,'byte-bound'):node.qualify_root(self.runtime,self.owner)
        self.owner.policy_hash=self.sha;self.runtime.files.clear()
        with self.assertRaisesRegex(PermissionError,'byte-bound'):node.qualify_root(self.runtime,self.owner)
    def test_policy_cannot_be_outside_declared_root(self):
        self.binding['policy']=str(self.base/'outside.json');self.owner.policy_path=Path(self.binding['policy'])
        with self.assertRaisesRegex(PermissionError,'declared root'):node.qualify_root(self.runtime,self.owner)
    def test_current_root_still_requires_original_policy_mode(self):
        self.owner.root=self.runtime.package/'skills'
        node.qualify_root(self.runtime,self.owner)
        self.owner.policy['mode']='arbitrary-process'
        with self.assertRaisesRegex(PermissionError,'policy mode'):node.qualify_root(self.runtime,self.owner)

if __name__=='__main__':unittest.main()
