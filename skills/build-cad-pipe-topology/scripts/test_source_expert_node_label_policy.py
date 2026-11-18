import copy
import unittest
import ezdxf
from source_expert_node_label_policy import apply


class LabelPolicy(unittest.TestCase):
    def setUp(self):
        self.doc = ezdxf.new()
        self.line = self.doc.modelspace().add_line((0, 0), (10, 0))
        self.graph = {'metadata': {'source_sha256': 'abc'}, 'nodes': [
            {'node_id': 'T1', 'node_type': 'tee', 'x': 5, 'y': 0,
             'source_handles': [self.line.dxf.handle]}], 'edges': [{'edge_id': 'E1'}]}
        self.record = {'node_type': 'tee', 'point': [5, 0],
                       'source_pipe_handle': self.line.dxf.handle,
                       'expert_issue': 'ERR-1', 'expert_note': '不参与节点标注'}
        self.policy = {'source_sha256': 'abc', 'records': [self.record]}

    def test_only_node_label_changes(self):
        old = copy.deepcopy(self.graph)
        audit = apply(self.graph, self.doc, self.policy)
        self.assertEqual(audit[0]['node_id'], 'T1')
        self.assertFalse(self.graph['nodes'][0]['node_label_visible'])
        self.assertEqual(self.graph['edges'], old['edges'])
        self.assertEqual(self.graph['metadata'], old['metadata'])

    def test_hash_geometry_and_ambiguity_fail_closed(self):
        for alter in ('hash', 'geometry', 'duplicate', 'missing_issue'):
            with self.subTest(alter=alter):
                g, p = copy.deepcopy(self.graph), copy.deepcopy(self.policy)
                if alter == 'hash': p['source_sha256'] = 'wrong'
                if alter == 'geometry': p['records'][0]['point'] = [5, 1]
                if alter == 'duplicate': g['nodes'].append(dict(g['nodes'][0], node_id='T2'))
                if alter == 'missing_issue': p['records'][0]['expert_issue'] = ''
                old = copy.deepcopy(g)
                with self.assertRaises(ValueError): apply(g, self.doc, p)
                self.assertEqual(g, old)

    def test_preexisting_policy_cannot_partially_mutate(self):
        g = copy.deepcopy(self.graph)
        g['nodes'][0]['node_label_visible'] = True
        old = copy.deepcopy(g)
        with self.assertRaises(ValueError): apply(g, self.doc, self.policy)
        self.assertEqual(g, old)


if __name__ == '__main__': unittest.main()
