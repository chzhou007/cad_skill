import copy,unittest
import ezdxf
from axis_unbranched_vertical_DN import collect,chain_evidence,annotation_guard,annotation_index,native_items,ANNOTATION_MODE
from axis_attribute_source_routing import collect as routing
from pipe_annotation_attributes import source_texts
from native_line_path_evidence import LAYERS

def fixture(rotation=0,mirror=False):
    doc=ezdxf.new();block=doc.blocks.new('PIPE');path=[[100,200],[100,150],[50,100],[50,0]]
    for a,b in zip(path,path[1:]):block.add_line(a,b,dxfattribs=dict(layer=LAYERS['supply']))
    root=doc.modelspace().add_blockref('PIPE',(0,0),dxfattribs=dict(rotation=rotation,xscale=-1 if mirror else 1))
    path=[list(root.matrix44().transform(p))[:2]for p in path]
    source='a'*64;gh='b'*64;edge=dict(edge_id='E',system='supply',source_insert_handle=root.dxf.handle,attribute_paths=[path],floor_start=2,floor_end=2)
    graph=dict(metadata=dict(source_sha256=source),nodes=[],edges=[edge]);route=routing(graph,dict(isometric_horizontal_directions_degrees=[0,45,135],source_rule_evidence='all vertical uses axis11'))
    for s in route['records']:s.update(native_source_status='single_source_line_covers',native_witnesses=[dict(scope='decomposed_selected_insert',source_handle=root.dxf.handle)])
    doc.modelspace().add_text('DN80',dxfattribs=dict(insert=(path[2][0]+3,(path[2][1]+path[3][1])/2),height=10,rotation=90))
    text=source_texts(doc,'axis',source)[0]
    seed=dict(edge_id='E',path_index=0,segment_index=2,system='supply',scope_points=path[2:4],nominal_mm=80,observations=[dict(source_text=text,nominal_mm=80)])
    annotations=dict(mode=ANNOTATION_MODE,source_sha256=source,graph_sha256=gh,graph_mutated=False,human_accepted=False,records=[seed],pending=[dict(edge_id='E',path_index=0,segment_index=0,reason='no_qualified_axis_annotation_on_this_vertical_segment')])
    return doc,graph,dict(edges=[]),route,annotations,source,gh

class Tests(unittest.TestCase):
    def test_same_floor_vertical_chain_inherits_axis_annotation_without_horizontal_or_whole_values(self):
        for rotation,mirror in[(0,False),(180,False),(0,True),(180,True)]:
            with self.subTest(rotation=rotation,mirror=mirror):
                a=fixture(rotation,mirror);before=copy.deepcopy(a[1:]);r=collect(*a)
                self.assertEqual(a[1:],before);self.assertEqual(r['counts']['new_inherited_vertical_domains'],1);self.assertEqual(r['records'][0]['nominal_mm'],80)
                self.assertEqual(r['records'][0]['segment_index'],0);self.assertFalse(r['records'][0]['whole_edge_DN_assigned']);self.assertIsNone(r['records'][0]['physical_length_mm'])
                self.assertEqual(r['crossed_physical_Ts'],0);self.assertFalse(r['horizontal_plan_attributes_changed']);self.assertFalse(r['crossview_values_used_as_seeds'])
    def test_real_third_arm_duplicate_native_child_and_Z_disagreement_block(self):
        for kind in('T','duplicate','Z'):
            a=list(fixture());doc=a[0];block=doc.blocks['PIPE']
            if kind=='T':doc.modelspace().add_line((100,150),(120,150),dxfattribs=dict(layer=LAYERS['supply']))
            elif kind=='duplicate':block.add_line((100,200),(100,150),dxfattribs=dict(layer=LAYERS['supply']))
            else:
                e=list(block.query('LINE'))[1];e.dxf.start=(100,150,1);e.dxf.end=(50,100,1)
            with self.subTest(kind=kind):r=collect(*a);self.assertEqual(r['records'],[]);self.assertEqual(r['counts']['remaining_unknown_vertical_domains'],1)
    def test_opposite_system_crossing_does_not_connect_or_change_pipe_DN(self):
        a=fixture();a[0].modelspace().add_line((100,150),(120,150),dxfattribs=dict(layer=LAYERS['return']));r=collect(*a);self.assertEqual(len(r['records']),1);self.assertEqual(r['records'][0]['system'],'supply')
    def test_unowned_new_DN_unparsed_compound_and_nested_DN_are_scope_barriers(self):
        for text in('DN65','DN80','DN300/DN200'):
            a=fixture();a[0].modelspace().add_text(text,dxfattribs=dict(insert=(103,180),height=10,rotation=90));r=collect(*a)
            self.assertEqual(r['records'],[]);self.assertIn('another in-scope',r['pending'][0]['reason'])
        a=fixture();a[0].blocks['PIPE'].add_text('DN80',dxfattribs=dict(insert=(103,180),height=10,rotation=90));r=collect(*a);self.assertEqual(r['records'],[]);self.assertIn('nested',r['pending'][0]['reason'])
    def test_F_stem_and_F_owned_seed_require_the_existing_ordered_reader(self):
        a=fixture();index=annotation_index(a[0],a[1],a[5]);scopes=a[3]['records'];seeds=a[4]['records']
        index['F_strokes']=[([90,180],[110,180])]
        with self.assertRaisesRegex(ValueError,'F leader'):annotation_guard(a[0],seeds,scopes,index,a[5],a[1]['edges'][0]['source_insert_handle'])
        index['F_strokes']=[];index['claims']={seeds[0]['observations'][0]['source_text']['handle']:[]}
        with self.assertRaisesRegex(ValueError,'F-owned'):annotation_guard(a[0],seeds,scopes,index,a[5],a[1]['edges'][0]['source_insert_handle'])
    def test_different_path_unwitnessed_or_ambiguous_domains_remain_unknown(self):
        for kind in('path','witness','annotation'):
            a=list(fixture())
            if kind=='path':a[4]['records'][0]['path_index']=1;a[3]['records'][2]['path_index']=1
            elif kind=='witness':a[3]['records'][1]['native_source_status']='no_witness_in_scoped_search'
            else:a[4]['pending'][0]['reason']='ambiguous_native_text_projection_requires_ownership_rule'
            r=collect(*a);self.assertEqual(r['records'],[])
    def test_collinear_subdivision_uses_one_original_LINE_not_a_fake_T(self):
        items=[dict(root_handle=None,child_handle='L',layer=LAYERS['supply'],XYZ=[[0,0,0],[0,100,0]])]
        scopes=[dict(path_index=0,segment_index=i,system='supply',scope_points=p,native_source_status='single_source_line_covers')for i,p in enumerate([[[0,0],[0,30]],[[0,30],[0,100]]])]
        r=chain_evidence(scopes,None,items);self.assertEqual(r['bends'][0]['source_arms'],2);self.assertFalse(r['bends'][0]['physical_T_crossed'])
    def test_zero_boolean_and_stale_seed_values_are_rejected(self):
        for bad in(0,True,float('nan')):
            a=list(fixture());a[4]['records'][0]['nominal_mm']=bad
            with self.assertRaises(ValueError):collect(*a)
        a=list(fixture());a[4]['records'][0]['observations'][0]['source_text']['text']='DN65';r=collect(*a);self.assertFalse(r['records']);self.assertIn('seed annotation changed',r['pending'][0]['reason'])
if __name__=='__main__':unittest.main()
