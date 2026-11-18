import copy,unittest
import ezdxf
from partial_uniform_main_DN import collect
from axis_unbranched_vertical_DN import native_items
from native_line_path_evidence import LAYERS
from native_paired_caption_geometry import collect as captions

def fixture():
    doc=ezdxf.new();m=doc.modelspace();layer=LAYERS['supply'];path=[[.25,100],[0,0],[100,0]]
    lines=[m.add_line(a,b,dxfattribs={'layer':layer})for a,b in zip(path,path[1:])]
    gate=[[-100,100],path[0]];m.add_line(*gate,dxfattribs={'layer':layer})
    edges=[dict(edge_id='G',system='supply',floor_start=1,floor_end=1,start_node_id='P',end_node_id='A',attribute_paths=[gate]),
        dict(edge_id='E',system='supply',floor_start=1,floor_end=1,start_node_id='A',end_node_id='B',attribute_paths=[path])]
    graph=dict(metadata=dict(source_sha256='S'),nodes=[],edges=edges)
    route=dict(inputs=dict(source=dict(sha256='S'),graph=dict(sha256='G')),records=[dict(edge_id='E',path_index=0,segment_index=i,
        scope_points=copy.deepcopy(path[i:i+2]),system='supply',floor_start=1,floor_end=1,
        direction_class='undetermined'if i==0 else'horizontal',native_source_status='single_source_line_covers',
        native_witnesses=[dict(scope='modelspace',source_handle=line.dxf.handle)])for i,line in enumerate(lines)])
    scope=dict(status='native_bounded_range_correspondence',scope_id='RANGE',floor=1,system='supply',views=dict(iso=dict(route=dict(edges=['G','E']))))
    group=dict(scope_id='RANGE',nominal_mm=200,remaining_plan_DN_regions=[dict(edge_id='P-MAIN',system='supply',nominal_mm=200,lineage=[{'native_source':'plan'}])],
        scoped_plan_caption_guard=dict(original_guard_reexecuted=True,original_thresholds_unchanged=True,F_and_other_new_DN_guards_retained=True),
        records=[dict(source_scope_id='RANGE:LOWER-UNIFORM-DN')])
    return doc,graph,route,scope,group
def run(args,existing=frozenset()):
    doc,g,route,scope,group=args
    return collect(scope,group,g,route,doc,native_items(doc,g),captions(doc),existing)

class PartialUniformMainDN(unittest.TestCase):
    def test_known_horizontal_domain_survives_other_undetermined_direction(self):
        args=fixture();before=copy.deepcopy(args[1:]);r=run(args)
        self.assertEqual(args[1:],before);self.assertEqual(len(r['records']),1);row=r['records'][0]
        self.assertEqual(row['axis_edge_id'],'E');self.assertEqual(row['nominal_mm'],200)
        self.assertEqual([x['segment_index']for x in row['horizontal_segment_domains']],[1])
        self.assertFalse(row['whole_horizontal_edge']);self.assertEqual(row['excluded_other_direction_domains'][0]['direction_class'],'undetermined')
        self.assertIsNone(row['excluded_other_direction_domains'][0]['new_DN_assigned']);self.assertIsNone(row['physical_length_mm'])
        self.assertEqual(r['unknown_directions_reclassified'],0);self.assertEqual(r['vertical_values_assigned'],0)
        self.assertFalse(run(args,{'E'})['records'])

    def test_new_DN_extra_bend_arm_and_unknown_source_are_still_held(self):
        for defect in('DN','extra','source','floor','system'):
            args=fixture();doc,g,route,scope,group=args
            if defect=='DN':doc.modelspace().add_text('DN80',dxfattribs={'insert':(50,4),'height':4})
            elif defect=='extra':doc.modelspace().add_line((0,0),(20,-20),dxfattribs={'layer':LAYERS['supply']})
            elif defect=='source':route['records'][0]['native_source_status']='no_witness_in_scoped_search'
            elif defect=='floor':route['records'][0]['floor_end']=2
            else:g['edges'][1]['system']='return'
            with self.subTest(defect=defect):self.assertFalse(run(args)['records'])

    def test_unqualified_range_source_region_or_old_guard_cannot_seed(self):
        for defect in('range','regions','guard','invalid_DN','binding'):
            args=fixture();doc,g,route,scope,group=args
            if defect=='range':scope['status']='held_local_source_evidence'
            elif defect=='regions':group['remaining_plan_DN_regions'][0]['nominal_mm']=300
            elif defect=='guard':group['scoped_plan_caption_guard']['F_and_other_new_DN_guards_retained']=False
            elif defect=='invalid_DN':group['nominal_mm']=True
            else:route['inputs']['source']['sha256']='OTHER'
            with self.subTest(defect=defect),self.assertRaises(ValueError):run(args)

if __name__=='__main__':unittest.main()
