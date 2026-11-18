import copy,unittest
from cycle_gate_plan_lengths import qualify

def fixture(paths=None,reverse=False):
    paths=paths or [[[0,0],[10,0]]]
    nodes=[dict(node_id=n,node_type='tee',floor=2,x=x,y=0)for n,x in [('A',0),('B',10)]]
    edge=dict(edge_id='P',system='supply',start_node_id='A',end_node_id='B',start_floor=2,end_floor=2,attribute_paths=paths)
    axis=copy.deepcopy(edge);axis['edge_id']='E';axis['attribute_paths']=[[[10,0],[0,0]]]if reverse else[[[0,0],[10,0]]]
    segments=[dict(index=i,path_index=pi,start=a,end=b,status='single_source_line_covers',drawing_length=abs(b[0]-a[0]),witnesses=[dict(scope='modelspace',source_handle='L'+str(pi)+str(i))])for pi,p in enumerate(paths)for i,(a,b)in enumerate(zip(p,p[1:]))]
    row=dict(mapping_id='M',classification='horizontal_only',floor=2,system='supply',plan_edges=['P'],iso_edges=['E'],plan_start='A',plan_end='B',iso_start='A',iso_end='B',component_profiles=dict(plan={},iso={}),native_path_evidence=dict(plan=dict(edges=[dict(edge_id='P',system='supply',segments=segments)])))
    units=dict(status='native_mm_units_corroborated_not_pipe_dimension_assignment',plan_window=[-100,100,-100,100])
    return dict(nodes=nodes,edges=[edge]),dict(nodes=copy.deepcopy(nodes),edges=[axis]),row,units,[0,45,135]

class Tests(unittest.TestCase):
    def test_length_does_not_select_DN_and_reversed_axis_is_read_only(self):
        for reverse in(False,True):
            a=fixture(reverse=reverse);before=copy.deepcopy(a);r=qualify(*a)
            self.assertEqual(r['complete_horizontal_centerline_mm'],10);self.assertIsNone(r['nominal_mm'])
            self.assertIsNone(r['physical_installed_length_mm']);self.assertIsNone(r['net_pipe_cut_length_mm']);self.assertEqual(a,before)
    def test_touching_arrays_reuse_reader_without_adding_distance(self):
        a=fixture([[[0,0],[5,0]],[[5,0],[10,0]]]);r=qualify(*a)
        self.assertEqual(r['complete_horizontal_centerline_mm'],10)
        self.assertEqual(r['metric_reader'],'original_exact_touching_projection')
        self.assertIsNotNone(r['plan_subdivision_reading_projection'])
    def test_gap_inline_detail_and_unproved_units_remain_unknown(self):
        a=fixture([[[0,0],[4,0]],[[6,0],[10,0]]])
        with self.assertRaises(ValueError):qualify(*a)
        for key,value in [('source_flexible_joints',[{}]),('source_view_context',{}),('source_wave_omission',True)]:
            a=fixture();a[0]['edges'][0][key]=value or {'kind':'detail'}
            with self.subTest(key=key),self.assertRaises(ValueError):qualify(*a)
        a=fixture();a[3]['status']='uncorroborated'
        with self.assertRaises(ValueError):qualify(*a)
    def test_same_floor_vertical_is_not_plan_length(self):
        a=fixture();a[1]['nodes'][1].update(x=0,y=10);a[1]['edges'][0]['attribute_paths']=[[[0,0],[0,10]]]
        with self.assertRaises(ValueError):qualify(*a)

if __name__=='__main__':unittest.main()
