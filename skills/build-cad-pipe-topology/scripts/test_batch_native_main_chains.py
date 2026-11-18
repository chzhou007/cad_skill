import copy,unittest
from unittest.mock import patch
from batch_native_main_chains import discover,apply,straight_corridor
from match_source_checked_crossview_paths import bridge_main_path


def graph(prefix):
    nodes=[dict(node_id=prefix+str(i),node_type='physical_junction',floor=1,x=i*10,y=0) for i in range(4)]
    edges=[]
    def edge(name,a,b,points):edges.append(dict(edge_id=prefix+name,start_node_id=a,end_node_id=b,system='supply',attribute_paths=[points]))
    for i in range(3):edge('E'+str(i),prefix+str(i),prefix+str(i+1),[[i*10,0],[(i+1)*10,0]])
    for i,n in enumerate(nodes[:]):
        for k in range(2 if i in (0,3) else 1):
            v=prefix+'V'+str(i)+str(k);nodes.append(dict(node_id=v,node_type='virtual_equipment',floor=1,x=i*10,y=10+k))
            edge('B'+str(i)+str(k),n['node_id'],v,[[i*10,0],[i*10,10+k]])
    return dict(nodes=nodes,edges=edges)


class Tests(unittest.TestCase):
    def fixture(self):return dict(plan=graph('P'),iso=graph('A')),dict(junction_mapping={'P0':'A0','P3':'A3'},records=[])
    def test_whole_chain_is_found_without_replacing_direct_writers_or_inventing_internal_node_identity(self):
        graphs,parent=self.fixture();before=copy.deepcopy((graphs,parent));rows,pending=discover(graphs,parent,1)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['plan_edges'],['PE0','PE1','PE2'])
        self.assertEqual(rows[0]['iso_edges'],['AE0','AE1','AE2']);self.assertFalse(rows[0]['internal_node_identities_assigned'])
        self.assertFalse(rows[0]['per_axis_edge_metric_allocation_known']);self.assertEqual((graphs,parent),before)
    def test_reversed_anchor_orientation_preserves_path_order(self):
        graphs,parent=self.fixture();parent['junction_mapping']={'P0':'A3','P3':'A0'}
        rows,_=discover(graphs,parent,1);self.assertEqual(rows[0]['iso_edges'],['AE2','AE1','AE0'])
    def test_service_or_floor_changes_and_unresolved_junctions_cannot_be_silently_bridged(self):
        for kind in ['system','floor','unresolved']:
            graphs,parent=self.fixture()
            if kind=='system':graphs['plan']['edges'][1]['system']='return'
            elif kind=='floor':graphs['plan']['nodes'][1]['floor']=2
            else:graphs['plan']['nodes'][1]['review_required']=True
            with self.subTest(kind=kind):self.assertEqual(discover(graphs,parent,1)[0],[])
    def test_missing_native_junction_evidence_keeps_a_technical_exception(self):
        graphs,parent=self.fixture()
        with patch('batch_native_main_chains.native_tee',side_effect=ValueError('source ray absent')):
            value=apply(dict(plan=None,iso=None),graphs,parent,1,dict(plan=dict(source_sha256='s',graph_sha256='p'),iso=dict(source_sha256='s',graph_sha256='a')))
        self.assertEqual(value['records'],[]);self.assertEqual(value['pending'][0]['detail'],'source ray absent')
        self.assertFalse(value['graph_mutated']);self.assertFalse(value['hil_ready'])
    def test_geometry_scoped_corridor_excludes_bent_alternative_but_keeps_true_parallel_paths(self):
        g=graph('P');g['edges']=[e for e in g['edges'] if e['edge_id'] not in ['PB01','PB31']]
        for i,p in enumerate([[0,20],[30,20]],4):g['nodes'].append(dict(node_id='P'+str(i),node_type='physical_junction',floor=1,x=p[0],y=p[1]))
        for name,a,b,path in [('X0','P0','P4',[[0,0],[0,20]]),('X1','P4','P5',[[0,20],[30,20]]),('X2','P5','P3',[[30,20],[30,0]])]:
            g['edges'].append(dict(edge_id=name,start_node_id=a,end_node_id=b,system='supply',attribute_paths=[path]))
        with self.assertRaises(ValueError):bridge_main_path(g,'P0','P3','supply',1)
        corridor,proof=straight_corridor(g,'P0','P3','supply',1)
        self.assertEqual(bridge_main_path(corridor,'P0','P3','supply',1)['edges'],['PE0','PE1','PE2'])
        self.assertTrue(proof['other_ring_routes_not_asserted_unique'])
        duplicate=copy.deepcopy(g['edges'][0]);duplicate['edge_id']='parallel';corridor['edges'].append(duplicate)
        with self.assertRaises(ValueError):bridge_main_path(corridor,'P0','P3','supply',1)

if __name__=='__main__':unittest.main()
