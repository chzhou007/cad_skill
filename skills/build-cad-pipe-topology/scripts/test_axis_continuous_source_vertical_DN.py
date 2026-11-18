import copy,unittest
import ezdxf
from axis_attribute_source_routing import collect as routing
from axis_continuous_source_vertical_DN import collect,overlaps_pipe
from native_line_path_evidence import LAYERS,_on


def fixture(branch_system='supply',branch_DN=80,transition=None,duplicate=False):
    doc=ezdxf.new();space=doc.modelspace();sh='a'*64;gh='b'*64
    main=space.add_line((-100,0),(100,0),dxfattribs={'layer':LAYERS['supply']})
    space.add_line((100,0),(100,-100),dxfattribs={'layer':LAYERS['supply']})
    space.add_line((0,0),(0,100),dxfattribs={'layer':LAYERS[branch_system]})
    if duplicate:space.add_line((-100,0),(100,0),dxfattribs={'layer':LAYERS['supply']})
    space.add_text('DN150',dxfattribs={'insert':(-50,3),'height':10})
    if branch_DN:space.add_text('DN'+str(branch_DN),dxfattribs={'insert':(3,50),'height':10,'rotation':90})
    if transition:space.add_text(transition,dxfattribs={'insert':(50,3),'height':10})
    graph=dict(metadata=dict(source_sha256=sh),nodes=[dict(node_id=n,node_type='tee' if n=='T' else 'virtual_equipment',x=x,y=y,floor=2) for n,x,y in [('T',0,0),('L',-100,0),('E',100,-100),('B',0,100)]],edges=[])
    for eid,start,end,system,path in [('L','L','T','supply',[[-100,0],[0,0]]),('E','T','E','supply',[[0,0],[100,0],[100,-100]]),('B','T','B',branch_system,[[0,0],[0,100]])]:
        graph['edges'].append(dict(edge_id=eid,start_node_id=start,end_node_id=end,system=system,attribute_paths=[path],floor_start=2,floor_end=2))
    route=routing(graph,dict(isometric_horizontal_directions_degrees=[0,45,135],source_rule_evidence='drawing11 source fixture'))
    for r in route['records']:
        matches=[line for line in space.query('LINE') if line.dxf.layer==LAYERS[r['system']] and all(_on(p,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05) for p in r['scope_points'])]
        r.update(native_source_status='single_source_line_covers' if len(matches)==1 else 'ambiguous_native_LINE',native_witnesses=[dict(scope='modelspace',source_handle=x.dxf.handle) for x in matches])
    route['inputs']=dict(source=dict(sha256=sh),graph=dict(sha256=gh))
    prior=dict(counts=dict(current_known=0),pending=[dict(edge_id='E',path_index=0,segment_index=1,original_reason='no_qualified_axis_annotation_on_this_vertical_segment')])
    return doc,graph,route,prior,sh,gh,main


class ContinuousSourceTests(unittest.TestCase):
    def test_horizontal_caption_through_T_then_bend_inherits_without_branch_seed_or_length(self):
        args=fixture();before=copy.deepcopy(args[1:6]);result=collect(*args[:6])
        self.assertEqual(args[1:6],before)
        self.assertEqual(result['counts']['new_known'],1);row=result['records'][0]
        self.assertEqual(row['nominal_mm'],150);self.assertIsNone(row['physical_length_mm'])
        self.assertEqual(row['candidate_evidence'][0]['continuity_evidence']['source'],'same_original_LINE_through_T_and_native_two_arm_bends')
        through=row['candidate_evidence'][0]['continuity_evidence']['through']
        self.assertEqual(len(through['junctions']),1);self.assertFalse(through['branch_DN_used_as_main_seed'])
        self.assertEqual(result['horizontal_final_values_assigned'],0)

    def test_explicit_downstream_change_overrides_upstream_and_compound_remains_a_barrier(self):
        result=collect(*fixture(transition='DN100')[:6]);self.assertEqual(result['records'][0]['nominal_mm'],100)
        result=collect(*fixture(transition='DN100/DN200')[:6]);self.assertEqual(result['records'],[])

    def test_mixed_T_duplicate_source_and_branch_only_seed_do_not_fill_main(self):
        self.assertEqual(collect(*fixture(branch_system='return')[:6])['records'],[])
        self.assertEqual(collect(*fixture(duplicate=True)[:6])['records'],[])
        args=fixture();doc=args[0]
        for text in list(doc.modelspace().query('TEXT')):
            if text.plain_text()=='DN150':doc.modelspace().delete_entity(text)
        self.assertEqual(collect(*args[:6])['records'],[])
        args=fixture();args[0].modelspace().add_line((50,0),(50,50),dxfattribs={'layer':LAYERS['supply']})
        self.assertEqual(collect(*args[:6])['records'],[])

    def test_overlap_requires_collinear_positive_extent(self):
        *_,line=fixture()
        self.assertTrue(overlaps_pipe(line,[dict(scope_points=[[-50,0],[50,0]])]))
        self.assertFalse(overlaps_pipe(line,[dict(scope_points=[[0,-50],[0,50]])]))
        self.assertFalse(overlaps_pipe(line,[dict(scope_points=[[-50,10],[50,10]])]))
        self.assertFalse(overlaps_pipe(line,[dict(scope_points=[[100,0],[150,0]])]))

if __name__=='__main__':unittest.main()
