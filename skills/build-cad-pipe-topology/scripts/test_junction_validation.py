import unittest
from junction_validation import compare


def graph(x=0, degree=2, node_id='T1'):
    nodes = [{'node_id': node_id, 'node_type':'tee', 'system':'supply', 'x':x, 'y':0}]
    edges = []
    for i in range(degree):
        nid='N'+str(i)
        nodes.append({'node_id':nid,'node_type':'equipment','x':i,'y':1})
        edges.append({'start_node_id':node_id,'end_node_id':nid})
    return {'nodes':nodes,'edges':edges}


class JunctionValidationTest(unittest.TestCase):
    def test_old_exception_remains_pending(self):
        r=compare(graph(),graph(),same_source=True)
        self.assertEqual(r['new_unexplained_degree_exceptions'],[])
        self.assertEqual(r['existing_pending'][0]['node_id'],'T1')
    def test_prior_without_source_and_graph_identity_is_new(self):
        self.assertEqual(compare(graph(),graph())['new_unexplained_degree_exceptions'],['T1'])
    def test_same_id_moved_is_new(self):
        r=compare(graph(x=1),graph(),same_source=True)
        self.assertEqual(r['new_unexplained_degree_exceptions'],['T1'])
    def test_degree_changed_is_new(self):
        r=compare(graph(degree=1),graph(degree=2),same_source=True)
        self.assertEqual(r['new_unexplained_degree_exceptions'],['T1'])
    def test_rewired_same_degree_is_new(self):
        g=graph();g['nodes'][1]['node_id']='N-new';g['edges'][0]['end_node_id']='N-new'
        self.assertEqual(compare(g,graph(),same_source=True)['new_unexplained_degree_exceptions'],['T1'])
    def test_corrected_junction_is_not_pending(self):
        r=compare(graph(degree=3),graph(degree=2),same_source=True)
        self.assertEqual(r['existing_pending'],[])
        self.assertEqual(r['new_unexplained_degree_exceptions'],[])
    def test_invalid_edge_fails_closed(self):
        g=graph();g['edges'][0]['end_node_id']='missing'
        with self.assertRaises(ValueError): compare(g,graph(),same_source=True)


if __name__=='__main__':unittest.main()
