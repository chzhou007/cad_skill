import copy,unittest
from test_anchored_cycle_gate_matching import fixture
from typed_cycle_riser_matching import discover

def views():
    graphs=dict(plan=fixture('p',5,{0:'A',4:'B'}),iso=fixture('a',6,{0:'A',5:'B'}));routing={}
    for view,g in graphs.items():
        peer=next(n for n in g['nodes']if n['node_id']==('pleaf1'if view=='plan'else'aleaf1'))
        if view=='plan':peer.update(subtype='out_of_plane_riser',system='supply')
        else:
            peer.update(node_type='physical_junction')
            branch=next(e for e in g['edges']if peer['node_id']in(e['start_node_id'],e['end_node_id']));routing[branch['edge_id']]=dict(classification='horizontal_only',vertical_segments=0)
            for name,floor in [('below',1),('above',3)]:
                g['nodes'].append(dict(node_id=name,node_type='physical_junction',floor=floor))
                eid='vertical-'+name;g['edges'].append(dict(edge_id=eid,start_node_id=peer['node_id'],end_node_id=name,system='supply'));routing[eid]=dict(classification='mixed_horizontal_vertical',vertical_segments=1)
    cycles={}
    for view,g in graphs.items():
        prefix='p'if view=='plan'else'a';count=5 if view=='plan'else 6
        cycles[view]=dict(cycle_nodes=[prefix+str(i)for i in range(count)],cycle_edges=[prefix+'e'+str(i)for i in range(count)])
    return graphs,{'p0':'a0','p4':'a5'},2,[dict(system='supply',**cycles)],routing

class Tests(unittest.TestCase):
    def test_unique_riser_role_with_two_known_gates_preserves_unequal_chain(self):
        args=views();before=copy.deepcopy(args);r=discover(*args)
        self.assertEqual(r['new_junction_mapping'],{'p1':'a1'});self.assertEqual(len(r['riser_port_correspondences']),1)
        self.assertEqual(len(r['bounded_routes']),1);route=r['bounded_routes'][0]
        self.assertEqual((len(route['plan']['edges']),len(route['iso']['edges'])),(3,4))
        self.assertFalse(route['individual_node_identities_assigned']);self.assertFalse(r['ordinal_identities_assigned']);self.assertEqual(args,before)
    def test_coordinates_and_DN_never_choose_identity(self):
        args=views()
        for g in args[0].values():
            for n in g['nodes']:n.update(x=-999,y=123,diameter_nominal_mm=999)
        self.assertEqual(discover(*args)['new_junction_mapping'],{'p1':'a1'})
    def test_same_floor_vertical_direction_unknown_or_cross_system_is_not_riser_proof(self):
        for kind in ('floor','direction','system','no-native-role'):
            a=views()
            if kind=='floor':next(n for n in a[0]['iso']['nodes']if n['node_id']=='above')['floor']=2
            elif kind=='direction':a[4]['vertical-above']['classification']='unresolved_direction_or_path'
            elif kind=='system':next(e for e in a[0]['iso']['edges']if e['edge_id']=='vertical-above')['system']='return'
            else:next(n for n in a[0]['plan']['nodes']if n['node_id']=='pleaf1')['subtype']='out_of_plane_interface'
            with self.subTest(kind=kind):self.assertFalse(discover(*a)['new_junction_mapping'])
    def test_duplicate_plan_riser_is_not_paired_by_proximity_or_order(self):
        a=views();next(n for n in a[0]['plan']['nodes']if n['node_id']=='pleaf2').update(subtype='out_of_plane_riser',system='supply')
        r=discover(*a);self.assertFalse(r['new_junction_mapping']);self.assertEqual(r['pending'][0]['reason'],'riser_role_missing_or_ambiguous')
    def test_missing_anchor_collapsed_identity_and_noncycle_fail_closed(self):
        for kind in ('anchor','collapse','gap','review','extra-arm'):
            a=views()
            if kind=='anchor':a[1].pop('p4')
            elif kind=='collapse':a[1]['p4']='a0'
            elif kind=='gap':a[0]['plan']['edges'].pop(0)
            elif kind=='review':a[0]['plan']['nodes'][2]['review_required']=True
            else:a[0]['plan']['edges'].append(dict(edge_id='chord',start_node_id='p1',end_node_id='p3',system='supply'))
            with self.subTest(kind=kind),self.assertRaises((ValueError,KeyError)):discover(*a)

if __name__=='__main__':unittest.main()
