import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
import batch_native_path_coverage as reader
from confirm_crossview_paths import encode
from native_path_serialization_runtime import path_serialization_runtime
from test_reconstruct_native_block_branches import fixture


class Tests(unittest.TestCase):
    def test_original_graph_bytes_unicode_signed_zero_key_order_and_mutation(self):
        root=Path(__file__).resolve().parents[2];original=reader.encode
        graph=dict(nodes=[dict(node_id='暖通井',values=[-0.0,1e-7,None,True])],edges=[dict(edge_id='E',attribute_paths=[[[0,0],[1,1]]])],tail={'甲':1,'乙':2})
        with path_serialization_runtime(root)as stats:
            for i in range(4):
                if i==1:graph['nodes'][0]['values'].append(15)
                if i==2:graph['tail']={'乙':2,'甲':1}
                if i==3:graph['edges'][0]['attribute_paths'][0][1][0]=3
                self.assertEqual(reader.encode(graph),original(graph))
            self.assertEqual(stats['exact_graph_encodings'],4)
        self.assertIs(reader.encode,original)

    def test_complete_native_multi_path_proof_unchanged(self):
        root=Path(__file__).resolve().parents[2]
        for omission in (False,True):
            for mirror in (False,True):
                doc,g,_,_,_=fixture(omission,mirror);before=copy.deepcopy(g)
                expected=reader.collect(doc,g,['E'],'S','G')
                with path_serialization_runtime(root):actual=reader.collect(doc,g,['E'],'S','G')
                self.assertEqual(encode(actual),encode(expected));self.assertEqual(g,before)

    def test_empty_edges_unsupported_values_and_exception_keep_original_behavior(self):
        root=Path(__file__).resolve().parents[2];original=reader.encode
        with self.assertRaisesRegex(ValueError,'stop'):
            with path_serialization_runtime(root)as stats:
                for value in ({'edges':[]},{'a':1},{'edges':[{}]},{'edges':[{'edge_id':'E'}],'custom':(1,2)}):
                    self.assertEqual(reader.encode(value),original(value))
                with self.assertRaises(TypeError):reader.encode({'edges':[{'edge_id':'E'}],'custom':object()})
                self.assertGreater(stats['original_fallbacks'],0)
                raise ValueError('stop')
        self.assertIs(reader.encode,original)

if __name__=='__main__':unittest.main()
