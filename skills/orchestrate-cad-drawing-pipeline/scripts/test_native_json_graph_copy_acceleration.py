import copy,unittest
from native_json_graph_copy_acceleration import accelerated_graph_copy,clone_graph

class Tests(unittest.TestCase):
    def graph(self):return dict(metadata={'文字':'供水／回水'},nodes=[dict(node_id='N1',x=-0.0,y=1e20)],edges=[dict(edge_id='E1',path=[[1.0,2],[3,4]])])
    def test_exact_JSON_values_isolation_alias_cycles_and_infinity(self):
        g=self.graph();g['shared']=g['edges'][0]['path'];g['self']=g;g['inf']=float('inf')
        with accelerated_graph_copy()as stats:r=copy.deepcopy(g)
        self.assertEqual(stats['graph_copies'],1);self.assertIs(r['self'],r);self.assertIs(r['shared'],r['edges'][0]['path']);self.assertIsNot(r['nodes'],g['nodes']);self.assertEqual(r['metadata'],g['metadata']);self.assertEqual(r['inf'],g['inf'])
        r['edges'][0]['path'][0][0]=9;self.assertEqual(g['edges'][0]['path'][0][0],1)
    def test_custom_objects_fallback_before_custom_pickle_reducer_and_preserve_deepcopy(self):
        calls=[]
        class Custom:
            def __reduce_ex__(self,n):calls.append('pickle');raise AssertionError('custom pickle must never run')
            def __deepcopy__(self,memo):calls.append('deepcopy');return 'copied'
        g=self.graph();g['custom']=Custom()
        with accelerated_graph_copy()as stats:r=copy.deepcopy(g)
        self.assertEqual(calls,['deepcopy']);self.assertEqual(r['custom'],'copied');self.assertEqual(stats['fallbacks'],1)
    def test_explicit_memo_non_graph_and_runtime_restoration(self):
        original=copy.deepcopy;g=self.graph();memo={id(g):'explicit'}
        with accelerated_graph_copy()as stats:self.assertEqual(copy.deepcopy(g,memo),'explicit');self.assertEqual(copy.deepcopy([1,2]),[1,2])
        self.assertEqual(stats['graph_copies'],0);self.assertIs(copy.deepcopy,original)
        with self.assertRaises(ValueError):
            with accelerated_graph_copy():raise ValueError('stop')
        self.assertIs(copy.deepcopy,original)
if __name__=='__main__':unittest.main()
