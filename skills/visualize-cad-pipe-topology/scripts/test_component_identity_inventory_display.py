import copy,unittest
from component_identity_inventory_display import normalize

def fixture():
    g=dict(nodes=[dict(node_id='A'),dict(node_id='B')],edges=[dict(edge_id='E',equipment_inventory=[dict(equipment_type='金属软接',count=2,device_names=['A/软接-01','B/软接-01'])])],
        sourceExplodedCaptionIdentity=dict(mode='native_exploded_equipment_caption_permutation_v1',aliases={'A':'B','B':'A'},source_geometry_changed=False,connections_changed=False,human_accepted=False))
    rows=[dict(edge_id='E',device_name=new+'/软接-01',owner_equipment=new,original_owner_equipment=old,original_device_name=old+'/软接-01')for old,new in [('A','B'),('B','A')]]
    return g,rows

class Tests(unittest.TestCase):
    def test_closed_swap_is_simultaneous_and_preserves_original_graph_and_assignments(self):
        g,rows=fixture();before=copy.deepcopy(g);old_rows=copy.deepcopy(rows);out,audit=normalize(g,rows,'GRAPH','CSV')
        self.assertEqual(g,before);self.assertEqual(rows,old_rows);self.assertEqual(out['edges'][0]['equipment_inventory'][0]['device_names'],['B/软接-01','A/软接-01'])
        self.assertEqual(len(audit['records']),2);self.assertFalse(audit['source_graph_mutated']);self.assertFalse(audit['component_counts_or_edge_assignments_changed'])

    def test_missing_alias_proof_wrong_prefix_edge_count_and_repeated_rows_fail(self):
        for mode in('open','proof','prefix','edge','count','duplicate','unowned','missing'):
            g,rows=fixture()
            if mode=='open':g['sourceExplodedCaptionIdentity']['aliases']={'A':'B'}
            elif mode=='proof':g['sourceExplodedCaptionIdentity']['connections_changed']=True
            elif mode=='prefix':rows[0]['device_name']='BA/软接-01'
            elif mode=='edge':rows[0]['edge_id']='OTHER'
            elif mode=='count':g['edges'][0]['equipment_inventory'][0]['count']=1
            elif mode=='duplicate':rows.append(copy.deepcopy(rows[0]))
            elif mode=='unowned':rows[0]['original_owner_equipment']='UNKNOWN'
            else:rows[0].pop('original_device_name')
            with self.subTest(mode=mode),self.assertRaises(ValueError):normalize(g,rows,'GRAPH','CSV')

    def test_no_identity_change_is_exact_and_double_application_is_rejected(self):
        g,rows=fixture();g.pop('sourceExplodedCaptionIdentity');out,audit=normalize(g,rows,'G','C');self.assertEqual(out,g);self.assertIsNone(audit)
        g,rows=fixture();out,_=normalize(g,rows,'G','C')
        with self.assertRaises(ValueError):normalize(out,rows,'G','C')

if __name__=='__main__':unittest.main()
