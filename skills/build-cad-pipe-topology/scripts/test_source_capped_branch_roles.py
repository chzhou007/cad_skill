import copy,unittest
from source_capped_branch_roles import apply


class Tests(unittest.TestCase):
    def fixture(self):
        n=dict(node_id='UT',node_type='virtual_equipment',subtype='unresolved_source_terminal',boundary_type='unresolved_source_terminal',
            x=100,y=200,system='supply',source_handles=['P'],review_required=True)
        tee=dict(node_id='T',node_type='tee',system='supply',x=100,y=0)
        e=dict(edge_id='E',start_node_id='T',end_node_id='UT',system='supply',edge_type='tee_to_virtual_equipment',source_handles=['P'],
            path=[[100,0],[100,200]],attribute_paths=[[[100,0],[100,200]]],physical_length='unknown',equipment_names=['valve'])
        from edge_endpoint_semantics import reconcile
        g,_=reconcile(dict(nodes=[tee,n],edges=[e],metadata=dict(source_sha256='S')))
        r=dict(node_id='UT',edge_id='E',system='supply',source_geometry=dict(source_pipe_handle='P',source_pipe_endpoints=[[100,200,21],[100,0,0]]),
            status='native_caption_leader_marker_frontier_witness_only',role='reserved_capped_branch_annotation',physical_connection_assigned=False,
            physical_length_mm=None,quantity_expanded_into_ports=False,qualifier=dict(text='盲板封堵'),caption=dict(text='预留支管接口/共2处'))
        inventory=dict(mode='native_capped_branch_annotation_witness_v1',graph_sha256='G',source_sha256='S',graph_mutated=False,connections_added=0,physical_lengths_assigned=0,records=[r])
        return g,inventory

    def test_classify_without_deleting_nodes_adding_edges_or_assigning_lengths(self):
        g,i=self.fixture();before=copy.deepcopy(g);out,p=apply(g,i,'G','I')
        self.assertEqual(g,before);self.assertEqual([n['node_id'] for n in out['nodes']],['T','UT']);self.assertEqual(len(out['edges']),1)
        n=out['nodes'][1];self.assertEqual(n['subtype'],'source_declared_capped_branch_interface');self.assertFalse(n['review_required']);self.assertFalse(n['human_accepted'])
        self.assertEqual(out['edges'][0]['path'],g['edges'][0]['path']);self.assertEqual(out['edges'][0]['physical_length'],'unknown');self.assertEqual(out['edges'][0]['equipment_names'],['valve'])
        self.assertEqual(out['edges'][0]['endpoint_semantics']['end']['subtype'],n['subtype']);self.assertEqual(p['nodes_retired'],0)
        self.assertEqual(out['sourceDeclaredCappedBranchInterfaces']['records'][0]['parent_node_snapshot'],g['nodes'][1])

    def test_stale_source_graph_or_non_native_physical_claims_block(self):
        for mode in ('graph','source','length','connected','quantity'):
            g,i=self.fixture()
            if mode=='graph':i['graph_sha256']='OLD'
            elif mode=='source':i['source_sha256']='OTHER'
            elif mode=='length':i['records'][0]['physical_length_mm']=0
            elif mode=='connected':i['records'][0]['physical_connection_assigned']=True
            else:i['records'][0]['quantity_expanded_into_ports']=True
            with self.subTest(mode=mode),self.assertRaises(ValueError):apply(g,i,'G','I')

    def test_existing_port_source_role_or_nonleaf_requires_reconciliation(self):
        for mode in ('port','role','nonleaf','node_port'):
            g,i=self.fixture()
            if mode=='port':g['edges'][0]['end_port_id']='PORT'
            elif mode=='node_port':g['virtual_equipment_ports']=[dict(node_id='UT')]
            elif mode=='role':g['nodes'][1]['source_endpoint_annotation']={'other':'role'}
            else:g['edges'].append(copy.deepcopy(g['edges'][0]));g['edges'][-1]['edge_id']='OTHER'
            with self.subTest(mode=mode),self.assertRaises(ValueError):apply(g,i,'G','I')

    def test_other_service_geometry_and_duplicate_selection_cannot_be_reused(self):
        for mode in ('system','coordinate','duplicate'):
            g,i=self.fixture()
            if mode=='system':i['records'][0]['system']='return'
            elif mode=='coordinate':i['records'][0]['source_geometry']['source_pipe_endpoints'][0][0]=101
            else:i['records'].append(copy.deepcopy(i['records'][0]))
            with self.subTest(mode=mode),self.assertRaises(ValueError):apply(g,i,'G','I')


if __name__=='__main__':unittest.main()
