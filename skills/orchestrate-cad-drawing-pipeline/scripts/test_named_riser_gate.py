import copy,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pipeline
OWNER=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
sys.path.insert(0,str(OWNER))
import test_native_named_riser_evidence as fixtures
from native_named_riser_evidence import collect
from source_readability import read_source


class NamedRiserGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.f=fixtures.NamedRiserEvidenceTests();self.f.setUp()
        self.source=self.root/'source.dxf';self.graph=self.root/'graph.json';self.policy=self.root/'policy.json';self.evidence=self.root/'evidence.json';self.f.doc.saveas(self.source)
        self.f.graph['metadata']['source_sha256']=pipeline.sha(self.source);self.write(self.graph,self.f.graph)
        self.f.policy.update(source_sha256=pipeline.sha(self.source),graph_sha256=pipeline.sha(self.graph));self.write(self.policy,self.f.policy)
        doc,preflight=read_source(self.source);data=collect(doc,self.f.graph,self.f.policy,pipeline.sha(self.source),pipeline.sha(self.graph))
        data.update(policy_sha256=pipeline.sha(self.policy),source_preflight=preflight,implementation_sha256={name:pipeline.sha(OWNER/name) for name in ('native_named_riser_evidence.py','native_dn_text_position.py','native_line_path_evidence.py','source_readability.py')})
        self.write(self.evidence,data)

    def write(self,path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    def check(self):return pipeline.validate_named_risers(self.source,self.graph,self.policy,self.evidence)

    def test_native_readback_pass_is_pending_without_connection_or_values(self):
        before=self.graph.read_bytes();r=self.check();self.assertEqual(r['source_replay'],'passed');self.assertEqual(r['status'],'pending');self.assertEqual(r['native_named_annotations'],1);self.assertFalse(r['physical_values_fused']);self.assertFalse(r['hil_ready']);self.assertEqual(self.graph.read_bytes(),before)

    def test_claimed_DN_or_extra_acceptance_cannot_be_injected(self):
        base=pipeline.read(self.evidence);v=copy.deepcopy(base);v['records'][0]['nominal_mm_observed']=999;self.write(self.evidence,v)
        with self.assertRaises(ValueError):self.check()
        v=copy.deepcopy(base);v['crossview_mapping_confirmed']=True;self.write(self.evidence,v)
        with self.assertRaises(ValueError):self.check()

    def test_policy_source_graph_and_code_drift_rejected(self):
        base=pipeline.read(self.evidence)
        for key,value in [('implementation_sha256',{}),('source_sha256','c'*64),('graph_sha256','c'*64),('policy_sha256','c'*64)]:
            with self.subTest(key=key):
                v=copy.deepcopy(base);v[key]=value;self.write(self.evidence,v)
                with self.assertRaises(ValueError):self.check()
        self.write(self.evidence,base);self.source.write_bytes(self.source.read_bytes()+b'\n')
        with self.assertRaises(ValueError):self.check()

    def test_pipeline_CLI_dispatch_preserves_pending_exit_contract(self):
        args=['pipeline.py','validate-named-risers','--source',str(self.source),'--graph',str(self.graph),'--policy',str(self.policy),'--evidence',str(self.evidence)]
        stream=io.StringIO()
        with patch.object(sys,'argv',args),patch('sys.stdout',stream):status=pipeline.main()
        self.assertEqual(status,2);self.assertEqual(json.loads(stream.getvalue())['source_replay'],'passed')


if __name__=='__main__':unittest.main()
