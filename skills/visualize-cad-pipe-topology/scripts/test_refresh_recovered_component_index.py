import copy,json,tempfile,unittest
from pathlib import Path
from refresh_recovered_component_index import context_from,exact_attributes,sha,NATIVE_MODE
class Tests(unittest.TestCase):
    def test_historical_attribute_domain_is_explicitly_bridged_without_rebinding_source_proofs(self):
        with tempfile.TemporaryDirectory()as t:
            p=Path(t)/'manifest.json';ctx=dict(rendered_graph_sha256='a'*64,original_native_proof={'rendered_graph':'a'*64,'DN':150});p.write_text(json.dumps(dict(attributeValueContext=ctx)),encoding='utf8');native=Path(t)/'native.json';native.write_text('{}',encoding='utf8')
            proof=dict(mode=NATIVE_MODE,inputs=dict(parent_viewer_manifest=dict(sha256=sha(p)),parent_rendered_graph=dict(sha256='a'*64)),complete_parent_and_native_inventory_replayed=True,pipe_graph_restoration_exact=True,rendered_graph_sha256='b'*64,protected_edge_bases={'E':['E','A','B','return',1,1,[[[0,0],[1,0]]]]})
            before=copy.deepcopy(proof);c=context_from(proof,native,p);self.assertEqual(c['rendered_graph_sha256'],'a'*64);self.assertEqual(c['original_native_proof'],ctx['original_native_proof']);self.assertEqual(c['current_rendered_graph_sha256'],'b'*64);self.assertEqual(proof,before)
            for key in('complete_parent_and_native_inventory_replayed','pipe_graph_restoration_exact'):
                bad=copy.deepcopy(proof);bad[key]=False
                with self.subTest(key=key),self.assertRaises(ValueError):context_from(bad,native,p)
    def test_index_addition_never_authorizes_a_pipe_attribute_delta(self):
        prior=[dict(edge_id='E',values={'diameter_nominal_mm':150,'whole_length_mm':None,'source':['native']})];self.assertTrue(exact_attributes(prior,copy.deepcopy(prior))['all_prior_effective_pipe_values_exact'])
        for mode in('DN','length','evidence','edge'):
            current=copy.deepcopy(prior)
            if mode=='DN':current[0]['values']['diameter_nominal_mm']=200
            elif mode=='length':current[0]['values']['whole_length_mm']=0
            elif mode=='evidence':current[0]['values']['source']=[]
            else:current=[]
            with self.subTest(mode=mode),self.assertRaises(ValueError):exact_attributes(prior,current)
if __name__=='__main__':unittest.main()
