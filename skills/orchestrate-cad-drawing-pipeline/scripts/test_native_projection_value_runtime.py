import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
import reconstruct_native_block_branches as kernel
from test_reconstruct_native_block_branches import fixture
from native_projection_value_runtime_v1 import fragments,projected,projection_values,serialization_fragments,clear_projection_serializations

class Tests(unittest.TestCase):
    def test_reused_serialization_exact_after_value_and_nested_key_order_changes(self):
        clear_projection_serializations()
        g=dict(edges=[dict(edge_id='E',attribute_paths=[[[0,0],[1,1]]])],metadata={'甲':1,'乙':2})
        for step in range(4):
            if step==1:g['metadata']['甲']=3
            if step==2:g['metadata']={'乙':2,'甲':3}
            if step==3:g['edges'][0]['attribute_paths'][0][0][0]=-0.0
            prefix,suffix,index=serialization_fragments(g,'E',kernel.encode)
            middle=kernel.encode(g['edges'][index])[:-1].replace(b'\n',b'\n    ')
            self.assertEqual(bytes(prefix)+middle+bytes(suffix),kernel.encode(g))
        clear_projection_serializations()

    def test_serialization_budget_and_disable_retain_original_bytes(self):
        from unittest.mock import patch
        import native_projection_value_runtime_v1 as values
        g=dict(edges=[dict(edge_id='E',attribute_paths=[[[0,0],[1,1]]])])
        clear_projection_serializations()
        with patch.object(values,'_envelope_budget',1):
            a,b,i=serialization_fragments(g,'E',kernel.encode)
            self.assertEqual((a,b,i),fragments(g,'E',kernel.encode));self.assertEqual(len(values._envelopes),0)
        with patch.dict(values.os.environ,{'CAD_NATIVE_SERIALIZATION_REUSE':'0'}):
            self.assertEqual(serialization_fragments(g,'E',kernel.encode),fragments(g,'E',kernel.encode))

    def test_exact_projection_bytes_across_root_key_edge_order_unicode_and_float_values(self):
        for root_index in range(4):
            for edge_index in range(3):
                edges=[dict(edge_id=str(i),attribute_paths=[[[1,-0.0],[1e20,3]],[[5,6],[7,8]]],中文='供水\n"字')for i in range(3)]
                props=[('source',{'中文':'暖通井'}),('edges',edges),('nodes',[]),('tail',{'empty':{},'values':[None,True,False,1e-7]})];item=props.pop(1);props.insert(root_index,item);graph=dict(props)
                before,after,index=fragments(graph,str(edge_index),kernel.encode);edge=dict(edges[edge_index],attribute_paths=[edges[edge_index]['attribute_paths'][1]])
                expected=copy.deepcopy(graph);expected['edges'][index]=edge
                self.assertEqual(before+kernel.encode(edge)[:-1].replace(b'\n',b'\n    ')+after,kernel.encode(expected))
                left,right,selected=serialization_fragments(graph,str(edge_index),kernel.encode)
                self.assertEqual(selected,index)
                self.assertEqual(bytes(left)+kernel.encode(edge)[:-1].replace(b'\n',b'\n    ')+bytes(right),kernel.encode(expected))
    def test_complete_original_native_proofs_equal_and_mutable_input_preserved(self):
        for omission in (False,True):
            for mirror in (False,True):
                doc,graph,_,_,_=fixture(omission,mirror);before=copy.deepcopy(graph);expected=kernel.projected_coverage(doc,graph,'E','S');self.assertEqual(projected(kernel,doc,graph,'E','S'),expected);self.assertEqual(graph,before)
    def test_all_runtime_functions_restore_on_exception(self):
        _,g,_,_,_=fixture();old_copy=copy.deepcopy;old_hash=kernel.value_sha
        with self.assertRaises(ValueError):
            with projection_values(kernel,g,'E'):raise ValueError('stop')
        self.assertIs(copy.deepcopy,old_copy);self.assertIs(kernel.value_sha,old_hash)
if __name__=='__main__':unittest.main()
