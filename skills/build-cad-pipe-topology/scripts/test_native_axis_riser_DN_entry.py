import copy,subprocess,sys,tempfile,unittest
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from native_line_path_evidence import collect as lines
from native_axis_riser_DN_scopes import compute,verify_output,implementation_hashes,MODE
from source_readability import read_source
from test_native_axis_riser_DN_scopes import fixture


class Tests(unittest.TestCase):
    def make(self,root):
        doc,g,_,sp,p=fixture();src=root/'source.dxf';doc.saveas(src);sh=sha(src);g['metadata']['source_sha256']=sh
        gp=root/'graph.json';gp.write_bytes(encode(g));gh=sha(gp);doc,_=read_source(src)
        lp=dict(source_sha256=sh,graph_sha256=gh,selections=[dict(edge_id=e['edge_id'],line_handles=e['source_handles']) for e in g['edges'] if not e['edge_id'].endswith('F')])
        paths=dict(source=src,graph=gp,line_policy=root/'line-policy.json',line_evidence=root/'line-evidence.json',policy=root/'segment-policy.json')
        paths['line_policy'].write_bytes(encode(lp));paths['line_evidence'].write_bytes(encode(lines(doc,g,lp,sh,gh)))
        sp.update({k+'_sha256':sha(v) for k,v in paths.items() if k!='policy'});paths['policy'].write_bytes(encode(sp));run=root/'segments'
        command=[sys.executable,'-X','utf8',str(Path(__file__).with_name('native_segment_dn_candidates_v2.py'))]
        for k,v in dict(paths,output=run).items():command+=['--'+k.replace('_','-'),str(v)]
        result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8');self.assertEqual(result.returncode,0,result.stderr)
        paths=dict(segment_DN=run/'segment-DN-evidence.json',segment_receipt=run/'source-segment-DN-receipt.json',policy=root/'policy.json')
        p.update(segment_DN_sha256=sha(paths['segment_DN']),segment_receipt_sha256=sha(paths['segment_receipt']));paths['policy'].write_bytes(encode(p))
        out=compute(paths,p);directory=root/'scope';directory.mkdir();(directory/'axis-riser-DN-scopes.json').write_bytes(encode(out))
        receipt=dict(mode=MODE,inputs={k:dict(path=str(v),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(directory/'axis-riser-DN-scopes.json'),human_accepted=False)
        (directory/'axis-riser-DN-scope-receipt.json').write_bytes(encode(receipt));return directory,receipt,src
    def test_saved_native_Chinese_source_and_segment_scope_replay_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            out,_,_=self.make(Path(tmp));data=verify_output(out)
            self.assertEqual(len(data['records']),4);self.assertTrue(all(r['nominal_mm']==450 for r in data['records']))
            self.assertFalse(data['physical_values_fused']);self.assertTrue(data['source_preflight'])
    def test_updated_output_hash_cannot_bless_false_whole_edge_DN_or_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            out,receipt,_=self.make(Path(tmp));p=out/'axis-riser-DN-scopes.json';data=load(p);data['records'][0]['whole_local_edge_DN_assigned']=True;data['records'][0]['physical_length_mm']=0
            p.write_bytes(encode(data));receipt['output_sha256']=sha(p);(out/'axis-riser-DN-scope-receipt.json').write_bytes(encode(receipt))
            with self.assertRaisesRegex(ValueError,'native replay differs'):verify_output(out)
    def test_original_source_change_is_detected_through_segment_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            out,_,source=self.make(Path(tmp));source.write_bytes(source.read_bytes()+b'\n')
            with self.assertRaises(ValueError):verify_output(out)


if __name__=='__main__':unittest.main()
