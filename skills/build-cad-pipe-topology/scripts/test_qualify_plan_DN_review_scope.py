import copy,unittest
from qualify_plan_DN_review_scope import qualify

class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.g={'edges':[dict(edge_id=e,start_node_id=a,end_node_id=b,system='supply') for e,a,b in [('a','n0','n1'),('b','n1','n2')]]}
        witnesses=lambda value,path:dict(nominal_mm=value,evidence=[dict(evidence_id='source:'+str(value),edge_path=path,transfers=[] if len(path)==1 else [dict(node_id='n1',from_edge='a',to_edge='b')])])
        self.f=dict(source_T_exceptions={'elsewhere':'unknown'},annotation_barriers={},records=[dict(edge_id='b',system='supply',status='conflict',nominal_mm=None,human_accepted=False,lineage=[witnesses(200,['a','b']),witnesses(300,['b'])])])
    def test_unrelated_gap_does_not_block_local_question(self):
        r=qualify(self.g,self.f,['b']);self.assertTrue(r['review_enabled']);self.assertEqual(r['unrelated_source_T_gaps'],['elsewhere']);self.assertFalse(r['whole_graph_hil_ready'])
    def test_gap_on_path_endpoint_blocks_even_without_transfer(self):
        self.f['source_T_exceptions']['n0']='gap';self.assertFalse(qualify(self.g,self.f,['b'])['review_enabled'])
    def test_barrier_anywhere_in_lineage_blocks(self):
        self.f['annotation_barriers']['a']='label';self.assertFalse(qualify(self.g,self.f,['b'])['review_enabled'])
    def test_different_service_and_wrong_incidence_rejected(self):
        for mutation in ('system','incidence'):
            with self.subTest(mutation=mutation):
                g=copy.deepcopy(self.g)
                if mutation=='system':g['edges'][0]['system']='return'
                else:g['edges'][0]['end_node_id']='other'
                with self.assertRaises(ValueError):qualify(g,self.f,['b'])
    def test_does_not_mutate_graph_or_result(self):
        before=copy.deepcopy((self.g,self.f));qualify(self.g,self.f,['b']);self.assertEqual(before,(self.g,self.f))
    def test_nonconflict_or_bad_lineage_not_question(self):
        self.f['records'][0]['nominal_mm']=200
        with self.assertRaises(ValueError):qualify(self.g,self.f,['b'])
    def test_confirmed_non_node_boundary_is_not_missing_source_T(self):
        edge=self.g['edges'][1];edge['end_node_id']=None
        with self.assertRaises(ValueError):qualify(self.g,self.f,['b'])
        edge['end_boundary_id']='A1';edge['endpoint_semantics']={'end':{'kind':'source_boundary','id':'A1'}}
        self.assertTrue(qualify(self.g,self.f,['b'])['review_enabled'])

if __name__=='__main__':unittest.main()
