import copy,unittest
from unittest.mock import patch
import ezdxf
from native_nested_direct_caption_DN import collect,neutral_guard
from native_line_path_evidence import LAYERS

def scene(rotation=0,mirror=False):
    doc=ezdxf.new('R2013');block=doc.blocks.new('direct_native_pipe');line=block.add_line((0,0),(0,2000),dxfattribs={'layer':LAYERS['return']});root=doc.modelspace().add_blockref(block.name,(10000,10000),dxfattribs={'rotation':rotation,'xscale':-1 if mirror else 1});matrix=root.matrix44();points=[list(matrix.transform(p))[:2]for p in(line.dxf.start,line.dxf.end)]
    # The reflected native drawing is re-annotated in WCS, retaining its direct
    # scalar text transform and the same original geometric separation.
    mid=[sum(p[i]for p in points)/2 for i in(0,1)];text=doc.modelspace().add_text('DN80',dxfattribs={'insert':(mid[0]-50,mid[1]),'height':100,'rotation':90+rotation})
    sh='a'*64;gh='b'*64;graph=dict(metadata=dict(source_sha256=sh),nodes=[],edges=[dict(edge_id='E',system='return',source_insert_handle=root.dxf.handle,attribute_paths=[points],floor_start=1,floor_end=1)])
    route=dict(inputs=dict(source=dict(sha256=sh),graph=dict(sha256=gh)),records=[dict(edge_id='E',path_index=0,segment_index=0,system='return',scope_points=points,direction_class='vertical',floor_start=1,floor_end=1,native_source_status='single_source_line_covers',native_witnesses=[dict(scope='decomposed_selected_insert',source_handle=root.dxf.handle,layer=LAYERS['return'],start=points[0],end=points[1])])])
    return doc,graph,route,[text.dxf.handle],sh,gh

class NativeNestedDirectTests(unittest.TestCase):
    def test_single_native_pipe_does_not_require_repeated_block_name_controls(self):
        for rotation,mirror in[(0,False),(180,False),(0,True)]:
            with self.subTest(rotation=rotation,mirror=mirror):
                args=scene(rotation,mirror);before=copy.deepcopy(args[1:]);result=collect(*args);self.assertEqual(args[1:],before);self.assertEqual(len(result['records']),1);r=result['records'][0];self.assertEqual(r['nominal_mm'],80);self.assertIsNone(r['physical_length_mm']);self.assertFalse(r['whole_edge_DN_assigned']);self.assertTrue(result['original_direct_reader_and_margin_unchanged'])

    def test_complete_modelspace_and_nested_competitors_not_just_target(self):
        for kind in('modelspace','same_root','other_root'):
            args=scene();doc=args[0]
            if kind=='modelspace':doc.modelspace().add_line((9990,10000),(9990,12000),dxfattribs={'layer':LAYERS['supply']})
            elif kind=='same_root':doc.blocks['direct_native_pipe'].add_line((-10,0),(-10,2000),dxfattribs={'layer':LAYERS['supply']})
            else:
                b=doc.blocks.new('competitor');b.add_line((-10,0),(-10,2000),dxfattribs={'layer':LAYERS['supply']});root=doc.modelspace().add_blockref(b.name,(10000,10000));args[1]['edges'].append(dict(edge_id='OTHER',system='supply',source_insert_handle=root.dxf.handle,attribute_paths=[[[9990,10000],[9990,12000]]]))
            self.assertFalse(collect(*args)['records'],kind)

    def test_neutral_layer_zero_keeps_original_competitor_margin(self):
        args=scene();args[0].blocks['direct_native_pipe'].add_line((-10,0),(-10,2000),dxfattribs={'layer':'0'});r=collect(*args);self.assertFalse(r['records']);self.assertIn('neutral layer0',r['held'][0]['reason'])
        args=scene();args[0].blocks['direct_native_pipe'].add_line((1000,0),(1000,2000),dxfattribs={'layer':'0'});self.assertEqual(len(collect(*args)['records']),1)

    def test_source_Z_and_exact_current_owner_are_required(self):
        args=scene();root=args[0].entitydb[args[1]['edges'][0]['source_insert_handle']];root.dxf.insert=(10000,10000,10);self.assertFalse(collect(*args)['records'])
        args=scene();args[1]['edges'].append(dict(args[1]['edges'][0],edge_id='duplicate'));self.assertFalse(collect(*args)['records'])

    def test_F_claim_and_invalid_source_hash_are_never_bypassed(self):
        args=scene()
        with patch('native_nested_direct_caption_DN.leader_claims',return_value={args[3][0]:['reserved']}):self.assertIn('F reader',collect(*args)['held'][0]['reason'])
        args[2]['inputs']['graph']['sha256']='changed'
        with self.assertRaisesRegex(ValueError,'identities'):collect(*args)

    def test_competing_label_values_need_transition_scope(self):
        args=scene();other=args[0].modelspace().add_text('DN65',dxfattribs={'insert':(9950,10700),'height':100,'rotation':90});args[3].append(other.dxf.handle)
        with self.assertRaisesRegex(ValueError,'transition'):collect(*args)

if __name__=='__main__':unittest.main()
