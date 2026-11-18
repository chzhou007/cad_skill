import copy,unittest
from test_native_external_pipe_destination import fixture as plan_fixture
from test_native_external_port_destination import fixture as axis_fixture
from native_external_pipe_destination import collect as plan_collect
from native_external_port_destination import collect as axis_collect
from match_named_external_boundary_paths import match


def fixture():
    pd,pg,pp,_,_=plan_fixture();ad,ag,ap,_,_=axis_fixture();pp['graph_sha256']='P';ap['graph_sha256']='A'
    plan=plan_collect(pd,pg,pp,'S','P');axis=axis_collect(ad,ag,ap,'S','A')
    coverage=[];gaps=[]
    for e in ag['edges']:
        start,port,centre=e['attribute_paths'][0];a=[port[0],40];b=[port[0],20];e['attribute_paths']=[[start,a,b,port,centre]]
        gap=dict(edge_id=e['edge_id'],gap_segment_index=1,gap_endpoints=[a,b],status='user_confirmed_inline_joint_logical_continuity',physical_length='unknown',parameter_status='unknown_not_zero')
        e['source_confirmed_gap_joints']=[gap];gaps.append(copy.deepcopy(gap));coverage.append(dict(edge_id=e['edge_id'],segments=[dict(index=i,status='no_witness_in_scoped_search' if i in (1,3) else 'single_source_line_covers') for i in range(4)]))
    for graph in (pg,ag):
        for e in list(graph['edges']):
            tid=e['start_node_id'];system=e['system']
            for i in range(2):
                nid=tid+'-branch-'+str(i);graph['nodes'].append(dict(node_id=nid,node_type='equipment',floor=1))
                graph['edges'].append(dict(edge_id=e['edge_id']+'-branch-'+str(i),start_node_id=tid,end_node_id=nid,system=system))
    for n in ag['nodes']:
        if n['node_type']=='tee':n['node_type']='physical_junction'
    main=dict(floor=1,plan_graph_sha256='P',iso_graph_sha256='A',source_sha256=dict(plan='S',iso='S'),evidence=dict(structure=dict(unique_full_floor_T_network=True,node_mapping={'T'+str(i):'T'+str(i) for i in range(4)})))
    inline=dict(source_sha256='S',graph_sha256='P',graph_mutated=False,records=[dict(edge_id=r['edge_id']) for r in plan['records']])
    return dict(plan=pg,iso=ag),main,plan,axis,inline,copy.deepcopy(ag),dict(records=gaps),dict(source_sha256='S',graph_sha256='A',edges=coverage)


class Tests(unittest.TestCase):
    def test_four_routes_require_names_destination_and_existing_T_correspondence(self):
        args=fixture();before=copy.deepcopy(args);result=match(*args)
        self.assertEqual(args,before);self.assertEqual(len(result['records']),4);self.assertEqual(result['new_connections_added'],0)
        self.assertEqual(len({r['axis_port_id'] for r in result['records']}),4)
        self.assertTrue(all(not r['external_ports_connected_to_each_other'] and r['physical_length_mm'] is None and not r['whole_edge_DN_assigned'] for r in result['records']))
    def test_matching_labels_cannot_override_wrong_T_system_extra_branch_or_gap(self):
        for case in ('T','service','source','partial','destination','new_gap','changed_route','review','degree'):
            args=list(fixture());graphs,main,plan,axis,inline,old,gaps,cov=args
            if case=='T':main['evidence']['structure']['node_mapping']['T0']='T1'
            elif case=='service':axis['records'][0]['system']='return'
            elif case=='source':axis['graph_sha256']='stale'
            elif case=='partial':axis['records'].pop()
            elif case=='destination':axis['destination']='elsewhere'
            elif case=='new_gap':cov['edges'][0]['segments'][0]['status']='no_witness_in_scoped_search'
            elif case=='changed_route':graphs['iso']['edges'][0]['device_names']=['new']
            elif case=='review':gaps['records'][0]['status']='unreviewed'
            else:graphs['plan']['edges'].pop()
            with self.subTest(case=case),self.assertRaises(ValueError):match(*args)

if __name__=='__main__':unittest.main()
