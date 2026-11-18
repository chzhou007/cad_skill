import copy,unittest
from test_match_network_named_lower_approaches import fixture as structure_fixture
from match_network_named_lower_approaches import select_structure
from network_named_lower_plan_attributes import topology_contract,MAPPING_MODE

def fixture():
    args=structure_fixture();graph=args[0]['plan'];rows=select_structure(*args);seeds=[]
    for row in rows:
        suffix='S' if row['system']=='supply' else 'R';nid=row['plan_network_T'];peer='PMAIN'+suffix;feed='PFEED'+suffix
        graph['nodes'] += [dict(node_id=peer,floor=1),dict(node_id=feed,floor=1)]
        for eid in (peer,feed):graph['edges'].append(dict(edge_id=eid,start_node_id=nid,end_node_id=eid,system=row['system'],attribute_paths=[[[0,0],[10,0]]]))
        incident=[row['plan_edges'][0],peer,feed];proof=dict(source_sha256='S',graph_sha256='G',graph_mutated=False,junctions=[dict(node_id=nid,source_rays=[dict(edge_id=eid) for eid in incident])])
        row['native_T_roles']=dict(plan=dict(through_edges=[row['plan_edges'][0],peer],off_edge=feed,native_T=proof));seeds.append(dict(edge_id=peer,text_handle='DN'+suffix))
    mapping=dict(mode=MAPPING_MODE,floor=1,records=rows,source_sha256=dict(plan='S'),graph_sha256=dict(plan='G'),local_graphs_mutated=False,physical_values_fused=False,physical_ports_verified=False,human_accepted=False,hil_ready=False)
    return graph,mapping,seeds,'S','G'

class Tests(unittest.TestCase):
    def test_original_through_kernel_contract_excludes_off_branch_feeds(self):
        args=fixture();before=copy.deepcopy(args);contract=topology_contract(*args)
        self.assertEqual(args,before);self.assertEqual(set(contract['main_edges']),{'PAPPS','PAPPR'});self.assertEqual(set(contract['branch_frontier_edges']),{'PFEEDS','PFEEDR'})
        self.assertEqual(set(contract['adjoining_main_edges']),{'PMAINS','PMAINR'});self.assertEqual(len(contract['junctions']),2)
    def test_wrong_seed_role_unknown_riser_floor_or_native_proof_block(self):
        for case in ('branch_seed','floor','review','role','hash','proof_T','mode'):
            args=list(fixture());graph,mapping,seeds=args[:3]
            if case=='branch_seed':seeds[0]['edge_id']='PFEEDS'
            elif case=='floor':graph['nodes'][1]['floor']=2
            elif case=='review':graph['nodes'][1]['review_required']=True
            elif case=='role':mapping['records'][0]['native_T_roles']['plan']['off_edge']='PAPPS'
            elif case=='hash':mapping['graph_sha256']['plan']='old'
            elif case=='proof_T':mapping['records'][0]['native_T_roles']['plan']['native_T']['junctions'][0]['node_id']='OTHER'
            else:mapping['mode']='old'
            with self.subTest(case=case),self.assertRaises(ValueError):topology_contract(*args)
if __name__=='__main__':unittest.main()
