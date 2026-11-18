import copy,unittest
from rebuild_compound_member_projections import member_graph
from test_compound_carrier_members import fixture
from compound_carrier_members import member

class Tests(unittest.TestCase):
    def test_member_subgraph_rebinds_checked_Ts_and_retains_equipment_and_branch_evidence(self):
        args=list(fixture());plan=args[1]
        for i in(0,1):
            plan['nodes'].append(dict(node_id='DEVICE-'+str(i),node_type='equipment',floor=3,x=i*1000,y=100,source_handle='BODY'+str(i)))
            plan['edges'].append(dict(edge_id='BR'+str(i),start_node_id='DEVICE-'+str(i),end_node_id='P'+str(i),system='supply',attribute_paths=[[[i*1000,100],[i*1000,0]]],source_handle='B'+str(i),physical_port_verified=False))
        before=copy.deepcopy(plan);r=member(*args);g=member_graph(plan,[r]);self.assertEqual(plan,before)
        self.assertEqual(len(g['nodes']),4);self.assertEqual(len(g['edges']),3)
        self.assertEqual({n['node_id']for n in g['nodes']if n['node_type']=='equipment'},{'DEVICE-0','DEVICE-1'})
        branches=[e for e in g['edges']if e['drawing_edge_id'].startswith('BR')]
        self.assertTrue(all(e['end_node_id'].startswith('MEMBER:')for e in branches));self.assertTrue(all(e['physical_port_verified']is False for e in branches))
        self.assertFalse(g['global_topology_complete']);self.assertFalse(g['calculation_ready']);self.assertFalse(g['other_member_connections_inferred'])
if __name__=='__main__':unittest.main()
