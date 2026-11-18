import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from uniform_path_group_DN_context import collect,from_artifact

class UniformDNTests(unittest.TestCase):
    def setUp(self):
        scope=dict(mapping_id='m',kind='native_main_chain_between_independent_junctions',group_scope_not_allocated_to_child_edges=True,whole_axis_nominal_mm=None,whole_installed_length_mm=None,human_accepted=False,related_HIL_confirmation_inherited=False,plan_drawn_nominal_mm=250,plan_edges=['p1','p2'],iso_edges=['a','b'],system='supply',floor=3,
            plan_DN_records=[dict(edge_id=p,nominal_mm=250,lineage=[{'native':'known'}],system='supply',human_accepted=False,status='direct_plan_DN')for p in('p1','p2')],source_sha256={'plan':'a'*64,'iso':'b'*64},graph_sha256={'plan':'c'*64,'iso':'d'*64},plan_DN_receipt_sha256='e'*64,mapping_receipt_sha256='f'*64)
        self.g=dict(nodes=[dict(node_id=n,node_type='tee',floor=3,x=x,y=0)for n,x in [('n1',0),('n2',1),('n3',2)]],edges=[dict(edge_id=e,start_node_id=a,end_node_id=b,system='supply',floor_start=3,floor_end=3,attribute_paths=[[[x,0],[x+1,0]]],batch_plan_attribute_scopes=copy.deepcopy(scope))for e,a,b,x in [('a','n1','n2',0),('b','n2','n3',1)]],sourceFullPlanBatchAttributes=dict(mode='complete_plan_batch_axis_attribute_composition_v1',source_verification_pending=False,human_accepted=False,records=[scope]))
        self.p={'isometric_horizontal_directions_degrees':[0,45,135]}
    def run_context(self):return collect(self.g,'1'*64,'2'*64,self.p,'3'*64,'3'*64)
    def test_uniform_DN_applies_without_any_length_allocation(self):
        before=copy.deepcopy(self.g);r=self.run_context();self.assertEqual(r['child_DN_domains'],2);self.assertEqual(r['groups'][0]['nominal_mm'],250);self.assertIsNone(r['groups'][0]['physical_child_lengths_mm']);self.assertEqual(self.g,before)
    def test_unknown_conflicting_or_changing_DN_stays_unassigned(self):
        for value in(None,200):
            with self.subTest(value=value):
                original=copy.deepcopy(self.g);self.g['sourceFullPlanBatchAttributes']['records'][0]['plan_DN_records'][0]['nominal_mm']=value
                self.assertEqual(self.run_context()['child_DN_domains'],0);self.g=original
    def test_vertical_crossfloor_or_partial_child_rejected(self):
        for kind in('floor','vertical','partial'):
            with self.subTest(kind=kind):
                original=copy.deepcopy(self.g);e=self.g['edges'][1]
                if kind=='floor':e['floor_end']=4
                elif kind=='vertical':e['attribute_paths']=[[[1,0],[1,1]]];self.g['nodes'][2].update(x=1,y=1)
                else:e['attribute_paths']=[[[1.2,0],[2,0]]]
                self.assertEqual(self.run_context()['child_DN_domains'],0);self.g=original
    def test_policy_hash_must_be_bound_to_qualified_parent(self):
        with self.assertRaises(ValueError):collect(self.g,'1'*64,'2'*64,self.p,'3'*64,'4'*64)
    def test_native_and_cached_artifact_entries_share_exact_hash_bound_context(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);raw=root/'raw';rendered=root/'rendered';policy=root/'policy'
            raw.write_text(json.dumps(self.g),encoding='utf8');rendered.write_text(json.dumps(self.g)+'\n',encoding='utf8');policy.write_text(json.dumps(self.p),encoding='utf8')
            digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            context=from_artifact(raw,rendered,policy,digest(raw),digest(policy));self.assertEqual(context['child_DN_domains'],2);self.assertEqual(context['rendered_graph_sha256'],digest(rendered))
            with self.assertRaisesRegex(ValueError,'inputs changed'):from_artifact(raw,rendered,policy,digest(raw),'4'*64)
if __name__=='__main__':unittest.main()
