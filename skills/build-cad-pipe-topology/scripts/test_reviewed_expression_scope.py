import copy, unittest
from reviewed_expression_scope import bounded_alternate, orient_pair, qualify


def graph():
    nodes=[dict(node_id=n,node_type='tee',floor=2,x=i,y=0) for i,n in enumerate(['A','B','C','D','X'])]
    def edge(e,a,b):return dict(edge_id=e,start_node_id=a,end_node_id=b,system='return')
    return dict(nodes=nodes,edges=[edge('bypass','A','B'),edge('a','A','C'),edge('b','C','D'),edge('c','D','B'),edge('outside','C','X')])


class ScopeTests(unittest.TestCase):
    def test_complete_boundary_cut_preserves_original_and_avoids_shortest(self):
        g=graph();old=copy.deepcopy(g);r=bounded_alternate(g,'bypass',{'A','B','X'},2,'return')
        self.assertEqual(r['route']['edges'],['a','b','c']);self.assertEqual(g,old)
        self.assertEqual(r['closed_known_boundaries'],['X'])
        self.assertFalse(r['shortest_path_used'])

    def test_parallel_or_missing_or_other_system_never_becomes_unique(self):
        g=graph();g['edges'].append(dict(g['edges'][1],edge_id='parallel'))
        with self.assertRaises(ValueError):bounded_alternate(g,'bypass',{'A','B','X'},2,'return')
        with self.assertRaises(ValueError):bounded_alternate(graph(),'bypass',{'A'},2,'return')
        with self.assertRaises(ValueError):bounded_alternate(graph(),'bypass',{'A','B'},2,'supply')
        g=graph();g['edges'][2]['system']='supply'
        with self.assertRaises(ValueError):bounded_alternate(g,'bypass',{'A','B'},2,'return')

    def test_unequal_internal_counts_do_not_create_internal_ID_or_attributes(self):
        views={'plan':dict(route=dict(nodes=['P','Q'],edges=['p']),junction_failures={},path_failures=[]),
               'iso':dict(route=dict(nodes=['Y','M','X'],edges=['i','j']),junction_failures={},path_failures=[])}
        orient_pair(views,{'P':'X','Q':'Y'});self.assertEqual(views['iso']['route']['nodes'],['X','M','Y'])
        answer=dict(decision='同一范围，有省略或多画，见说明',comment='省略设备CAD')
        result=qualify(views,answer);self.assertEqual(result['status'],'native_bounded_range_correspondence')
        self.assertFalse(result['internal_branch_counts_equal']);self.assertFalse(result['internal_node_identities_assigned'])
        self.assertEqual(result['DN_values_assigned'],0);self.assertEqual(result['length_values_assigned'],0)
        views['iso']['junction_failures']['M']='source ray missing'
        held=qualify(views,answer);self.assertEqual(held['status'],'held_local_source_evidence')
        self.assertEqual(held['failures'][0]['owner'],'local_topology_source_evidence')
        with self.assertRaises(ValueError):qualify(views,dict(decision='原图仍不足以判断',comment='未知'))
        with self.assertRaises(ValueError):orient_pair(views,{'P':'X','Q':'Z'})


if __name__=='__main__':unittest.main()
