import copy,unittest
from test_native_main_endpoint_extent import fixture
from rebuild_bounded_main_complete_extents import scope

def case():
    p,a,row,metric=fixture();value=dict(mapping_id='M',floor=3,system='supply',
        plan_edges=['E'],axis_edge_id='E',plan_Ts=['A','B'],axis_Ts=['A','B'],nominal_mm=300,
        DN_status='exact_qualified_local_plan_DN_retained_not_fresh_global_DN_rebuild',whole_axis_DN_selected=True,
        plan_DN_record=dict(nominal_mm=300,scope_paths=copy.deepcopy(p['edges'][0]['attribute_paths'])),plan_horizontal_projection=metric)
    return [p,a,value,[0,45,135]]

class Tests(unittest.TestCase):
    def test_existing_bounded_metric_completes_without_changing_DN_graph_or_ID(self):
        args=case();before=copy.deepcopy(args);row,r,b=scope(*args)
        self.assertEqual(args,before);self.assertEqual(r['complete_horizontal_centerline_route_mm'],10)
        self.assertEqual(row['mapping_id'],'M');self.assertIsNone(r['whole_installed_length_mm']);self.assertIsNone(b)
    def test_wrong_ends_unknown_DN_inline_interiors_or_vertical_axis_cannot_complete(self):
        for mode in('ends','DN','inline','vertical','omission'):
            args=case();p,a,v,_=args
            if mode=='ends':p['edges'][0]['attribute_paths'][0][-1]=[9,0];v['plan_DN_record']['scope_paths']=copy.deepcopy(p['edges'][0]['attribute_paths'])
            elif mode=='DN':v['whole_axis_DN_selected']=False
            elif mode=='inline':p['edges'][0]['source_flexible_joints']=[{'length':None}]
            elif mode=='vertical':a['nodes'][1].update(x=0,y=10);a['edges'][0]['attribute_paths'][0][-1]=[0,10]
            else:p['edges'][0]['attribute_paths']=[[[0,0],[4,0]],[[6,0],[10,0]]];v['plan_DN_record']['scope_paths']=copy.deepcopy(p['edges'][0]['attribute_paths'])
            with self.subTest(mode=mode),self.assertRaises(ValueError):scope(*args)
    def test_reversed_native_source_paths_remain_unchanged(self):
        args=case()
        for g in args[:2]:g['edges'][0]['attribute_paths'][0].reverse()
        args[2]['plan_DN_record']['scope_paths']=copy.deepcopy(args[0]['edges'][0]['attribute_paths'])
        r=scope(*args)[1];self.assertEqual(r['endpoint_relations']['plan']['path_orientation'],'end_to_start')
        self.assertEqual(r['complete_horizontal_centerline_route_mm'],10)
if __name__=='__main__':unittest.main()
