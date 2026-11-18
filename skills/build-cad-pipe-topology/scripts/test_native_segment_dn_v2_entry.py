import copy,tempfile,unittest
from pathlib import Path
import test_native_segment_dn_candidates_v2 as fixtures
from confirm_crossview_paths import load,sha,encode
from native_line_path_evidence import collect as collect_lines
from native_segment_dn_candidates_v2 import compute,verify_output,implementation_hashes,MODE


class QualifiedSegmentNativeEntryTests(unittest.TestCase):
    def build(self,root):
        doc,g,w,policy,text=fixtures.fixture();doc.modelspace().add_text('竖向管径对照',dxfattribs=dict(insert=(1000,1000)))
        source=root/'source.dxf';doc.saveas(source);g['metadata']['source_sha256']=sha(source);gp=root/'graph.json';gp.write_bytes(encode(g))
        line=next(e for e in doc.modelspace().query('LINE') if e.dxf.layer=='空调冷冻水回水')
        lp=root/'line-policy.json';lp.write_bytes(encode(dict(source_sha256=sha(source),graph_sha256=sha(gp),selections=[dict(edge_id='RISER',line_handles=[line.dxf.handle])])))
        le=root/'line-evidence.json';le.write_bytes(encode(collect_lines(doc,g,load(lp),sha(source),sha(gp))))
        paths=dict(source=source,graph=gp,line_policy=lp,line_evidence=le,policy=root/'policy.json')
        policy.update({k+'_sha256':sha(v) for k,v in paths.items() if k!='policy'})
        policy['display_stub_policy'].update(source_sha256=sha(source),graph_sha256=sha(gp));paths['policy'].write_bytes(encode(policy))
        result=compute(paths,policy);out=root/'output';out.mkdir();(out/'segment-DN-evidence.json').write_bytes(encode(result))
        receipt=dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(out/'segment-DN-evidence.json'),human_accepted=False)
        (out/'source-segment-DN-receipt.json').write_bytes(encode(receipt));return paths,out,receipt,result
    def test_replay_reads_native_chinese_and_retains_source_graph_files(self):
        with tempfile.TemporaryDirectory() as folder:
            paths,out,receipt,result=self.build(Path(folder));before={k:sha(v) for k,v in paths.items()}
            replay=verify_output(out);self.assertEqual(replay,result);self.assertEqual({k:sha(v) for k,v in paths.items()},before)
            self.assertEqual(replay['source_preflight']['native_chinese_entity_count'],1);self.assertFalse(replay['physical_values_fused'])
    def test_updated_hashes_do_not_bless_fabricated_line_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            paths,out,receipt,result=self.build(Path(folder));witness=load(paths['line_evidence']);witness['edges'][0]['segments'][0]['source_handle']='FAKE';paths['line_evidence'].write_bytes(encode(witness))
            policy=load(paths['policy']);policy['line_evidence_sha256']=sha(paths['line_evidence']);paths['policy'].write_bytes(encode(policy))
            for k in ('policy','line_evidence'):receipt['inputs'][k]['sha256']=sha(paths[k])
            (out/'source-segment-DN-receipt.json').write_bytes(encode(receipt))
            with self.assertRaisesRegex(ValueError,'line evidence does not replay'):verify_output(out)
    def test_false_acceptance_in_output_or_changed_code_receipt_is_rejected(self):
        for case in ('acceptance','code'):
            with tempfile.TemporaryDirectory() as folder:
                paths,out,receipt,result=self.build(Path(folder))
                if case=='acceptance':
                    result['human_accepted']=True;(out/'segment-DN-evidence.json').write_bytes(encode(result));receipt['output_sha256']=sha(out/'segment-DN-evidence.json')
                else:receipt['implementation_sha256']['native_valve_display_stub_evidence.py']='FAKE'
                (out/'source-segment-DN-receipt.json').write_bytes(encode(receipt))
                with self.subTest(case=case),self.assertRaises(ValueError):verify_output(out)


if __name__=='__main__':unittest.main()
