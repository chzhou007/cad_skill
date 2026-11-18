import copy,unittest
from test_native_touching_plan_path_chunks import fixture
from touching_plan_path_coverage import audit


class Tests(unittest.TestCase):
    def test_native_joined_coverage_keeps_original_indices_and_graph_hash(self):
        doc,graph,policy,metric=fixture();before=copy.deepcopy(graph)
        result=audit(doc,graph,policy,'S','G');row=result['edges'][0]
        self.assertEqual(result['graph_sha256'],'G');self.assertEqual(row['coverage_mode'],'native_exact_touching_path_chunks_no_added_span')
        self.assertEqual([(s['path_index'],s['index']) for s in row['segments']],[(0,0),(1,0)])
        self.assertEqual(row['source_covered_drawing_length'],300);self.assertEqual(graph,before)
        self.assertFalse(result['hil_ready']);self.assertFalse(result['graph_mutated'])
    def test_private_single_path_frontiers_keep_the_inherited_reader(self):
        doc,graph,policy,metric=fixture();graph['nodes'].append(dict(node_id='C',floor=3,x=250,y=300))
        doc.modelspace().add_line((200,300),(250,300),dxfattribs=dict(layer='空调冷冻水供水'))
        graph['edges'].append(dict(edge_id='Q',system='supply',start_node_id='B',end_node_id='C',attribute_paths=[[[200,300],[250,300]]]))
        result=audit(doc,graph,dict(policy,edges=['P','Q']),'S','G')
        self.assertEqual([r['edge_id'] for r in result['edges']],['P','Q']);self.assertNotIn('coverage_mode',result['edges'][1])
        self.assertEqual(result['edges'][1]['source_covered_drawing_length'],50)
    def test_gaps_empty_chunks_and_wrong_native_sources_never_gain_joined_evidence(self):
        for case in ('gap','empty','wrong_source','overlap'):
            doc,graph,policy,metric=fixture()
            if case=='gap':graph['edges'][0]['attribute_paths'][1][0][0]+=.001
            elif case=='empty':graph['edges'][0]['attribute_paths'][1]=[]
            elif case=='wrong_source':next(iter(doc.modelspace().query('LINE'))).dxf.layer='空调冷冻水回水'
            else:graph['edges'][0]['attribute_paths'][1]=[[200,100],[150,100]]
            with self.subTest(case=case),self.assertRaises(ValueError):audit(doc,graph,policy,'S','G')


if __name__=='__main__':unittest.main()
