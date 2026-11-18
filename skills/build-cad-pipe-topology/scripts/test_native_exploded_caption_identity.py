import copy
import unittest
from native_exploded_caption_identity import apply_aliases,migrate_components


class Tests(unittest.TestCase):
    def test_component_names_and_owners_migrate_with_source_and_edge_unchanged(self):
        rows=[dict(device_name='A/Valve-1',owner_equipment='A',edge_id='E',source_top_handle='FF',x='1',y='2')]
        changed,audit=migrate_components(rows,{'A':'B','B':'A'})
        self.assertEqual(changed[0]['owner_equipment'],'B');self.assertEqual(changed[0]['device_name'],'B/Valve-1')
        self.assertEqual(changed[0]['original_device_name'],'A/Valve-1')
        self.assertEqual(changed[0]['edge_id'],'E');self.assertEqual(changed[0]['source_top_handle'],'FF')
        self.assertEqual(rows[0]['owner_equipment'],'A');self.assertEqual(len(audit),1)
    def test_closed_swap_changes_identity_references_and_preserves_paths_services_ids(self):
        graph=dict(nodes=[dict(node_id='A',label='A',x=1,y=2),dict(node_id='B',label='B',x=3,y=4),dict(node_id='T')],
            edges=[dict(edge_id='E1',start_node_id='T',end_node_id='A',end_port_id='A-P1',system='supply',attribute_paths=[[[0,0],[1,2]]]),
                   dict(edge_id='E2',start_node_id='B',end_node_id='T',start_port_id='B-P1',system='return',attribute_paths=[[[3,4],[0,0]]])],
            sourceHistoricalEvidence=dict(equipment_id='A'))
        before=copy.deepcopy(graph);out=apply_aliases(graph,{'A':'B','B':'A'})
        self.assertEqual(graph,before)
        self.assertEqual(out['nodes'][0]['node_id'],'B');self.assertEqual(out['nodes'][0]['x'],1)
        self.assertEqual(out['edges'][0]['end_node_id'],'B');self.assertEqual(out['edges'][0]['end_port_id'],'B-P1')
        for a,b in zip(graph['edges'],out['edges']):
            self.assertEqual(a['attribute_paths'],b['attribute_paths']);self.assertEqual(a['edge_id'],b['edge_id']);self.assertEqual(a['system'],b['system'])
        self.assertEqual(out['sourceHistoricalEvidence'],before['sourceHistoricalEvidence'])

    def test_partial_or_collapsed_identity_change_is_rejected(self):
        for aliases in ({'A':'B'},{'A':'B','C':'B'}):
            with self.subTest(aliases=aliases),self.assertRaisesRegex(ValueError,'closed identity'):
                apply_aliases(dict(nodes=[],edges=[]),aliases)

    def test_complete_cycle_is_simultaneous_not_sequential_string_replacement(self):
        g=dict(nodes=[dict(node_id=n) for n in ['A','B','C']],edges=[])
        self.assertEqual([n['node_id'] for n in apply_aliases(g,{'A':'B','B':'C','C':'A'})['nodes']],['B','C','A'])


if __name__=='__main__':unittest.main()
