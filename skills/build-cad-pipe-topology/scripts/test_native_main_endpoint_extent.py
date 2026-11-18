import copy,math,unittest
from native_main_endpoint_extent import endpoint_relation,qualify

def fixture(reverse_plan=False,reverse_axis=False):
    def graph(reverse):
        path=[[0.,0.],[10.,0.]]
        return dict(nodes=[dict(node_id='A',node_type='tee',floor=3,system='supply',x=0.,y=0.),dict(node_id='B',node_type='tee',floor=3,system='supply',x=10.,y=0.)],edges=[dict(edge_id='E',system='supply',start_node_id='A',end_node_id='B',start_floor=3,end_floor=3,attribute_paths=[list(reversed(path))if reverse else path])])
    row=dict(mapping_id='M',kind='same_floor_T_to_T_main',floor=3,system='supply',plan_edges=['E'],iso_edges=['E'],plan_start='A',plan_end='B',iso_start='A',iso_end='B')
    projection=dict(status='native_plan_horizontal_projection_partial_length',value_mm=10.,pieces=[dict(length_mm=10.)],installed_whole_edge_length_mm=None)
    return graph(reverse_plan),graph(reverse_axis),row,projection

class Tests(unittest.TestCase):
    def test_all_undirected_endpoint_orders_equal_without_mutating_inputs(self):
        for p in(False,True):
            for a in(False,True):
                plan,axis,row,metric=fixture(p,a);before=copy.deepcopy((plan,axis));r=qualify(plan,axis,row,300.,metric,[0,45,135])
                self.assertEqual(r['nominal_mm'],300.);self.assertEqual(r['complete_horizontal_centerline_route_mm'],10.);self.assertEqual((plan,axis),before)
                self.assertEqual(r['endpoint_relations']['plan']['path_orientation'],'end_to_start'if p else'start_to_end');self.assertFalse(r['endpoint_relations']['plan']['flow_direction_inferred'])

    def test_rotation_mirror_and_axis_vertical_guard(self):
        for angle in(0,45,135,180,225,315):
            for mirror in(1,-1):
                plan,axis,row,metric=fixture(True,True)
                for g in(plan,axis):
                    x=mirror*10*math.cos(math.radians(angle));y=10*math.sin(math.radians(angle));g['nodes'][1].update(x=x,y=y);g['edges'][0]['attribute_paths'][0][0]=[x,y]
                self.assertEqual(qualify(plan,axis,row,300.,metric,[0,45,135])['complete_horizontal_centerline_route_mm'],10.)
        plan,axis,row,metric=fixture();axis['nodes'][1].update(x=0.,y=10.);axis['edges'][0]['attribute_paths'][0][-1]=[0.,10.]
        with self.assertRaisesRegex(ValueError,'unproved horizontal'):qualify(plan,axis,row,300.,metric,[0,45,135])

    def test_real_missing_ends_wrong_system_floor_interface_and_multi_path_rejected(self):
        for mode in('gap','service','floor','interface','multi','coincident','review','detail'):
            plan,axis,row,metric=fixture();edge=plan['edges'][0]
            if mode=='gap':edge['attribute_paths'][0][-1]=[9.,0.]
            if mode=='service':edge['system']='return'
            if mode=='floor':edge['end_floor']=2
            if mode=='interface':plan['nodes'][1]['node_type']='virtual_equipment'
            if mode=='multi':edge['attribute_paths']=[[[0.,0.],[4.,0.]],[[6.,0.],[10.,0.]]]
            if mode=='coincident':plan['nodes'][1].update(x=0.,y=0.)
            if mode=='review':plan['nodes'][1]['review_required']=True
            if mode=='detail':edge['source_view_context']={'kind':'confirmed_detail_view'}
            with self.assertRaises(ValueError,msg=mode):qualify(plan,axis,row,300.,metric,[0,45,135])

    def test_missing_metric_does_not_erase_source_DN_or_become_zero(self):
        plan,axis,row,_=fixture(True);r=qualify(plan,axis,row,300.,None,[0,45,135]);self.assertEqual(r['nominal_mm'],300.);self.assertIsNone(r['complete_horizontal_centerline_route_mm']);self.assertIsNone(r['whole_installed_length_mm'])
        for value in(None,True,0,float('nan')):
            with self.assertRaises(ValueError):qualify(plan,axis,row,value,None,[0,45,135])

if __name__=='__main__':unittest.main()
