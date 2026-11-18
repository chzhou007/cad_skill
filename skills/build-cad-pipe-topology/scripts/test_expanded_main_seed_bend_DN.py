import copy
import unittest
import ezdxf
from expanded_main_seed_bend_DN import compose
from axis_unbranched_vertical_DN import native_items
from native_line_path_evidence import LAYERS
from pipe_annotation_attributes import source_texts


def fixture():
    doc=ezdxf.new();m=doc.modelspace()
    a=m.add_line((0,0,0),(10,0,0),dxfattribs={'layer':LAYERS['supply']})
    b=m.add_line((10,0,0),(10,8,0),dxfattribs={'layer':LAYERS['supply']})
    text=m.add_text('DN300',dxfattribs={'insert':(4,.3),'height':.3})
    graph=dict(metadata=dict(source_sha256='a'*64),edges=[dict(edge_id='E',system='supply',
        attribute_paths=[[[0,0],[10,0],[10,8]]])])
    records=[]
    for si,line in enumerate([a,b]):
        records.append(dict(edge_id='E',path_index=0,segment_index=si,
            scope_points=copy.deepcopy(graph['edges'][0]['attribute_paths'][0][si:si+2]),
            direction_class='horizontal'if si==0 else'vertical',system='supply',floor_start=3,floor_end=3,
            native_source_status='single_source_line_covers',native_witnesses=[dict(scope='modelspace',source_handle=line.dxf.handle,layer=line.dxf.layer)]))
    obs=next(t for t in source_texts(doc,'axis','a'*64)if t['handle']==text.dxf.handle)
    seed=dict(records[0],nominal_mm=300,source_line_handle=a.dxf.handle,source_Z=0,
        observations=[dict(source_text=obs,nominal_mm=300)],horizontal_final_value_assigned=False,
        source_scope_expansion=dict(source_line_handle=a.dxf.handle,native_XYZ=[list(a.dxf.start),list(a.dxf.end)],scope_points=[[0,0],[10,0]],
            source='same_original_LINE_through_current_native_Ts',branch_DN_used_as_main_seed=False,physical_length_mm=None,junctions=[]))
    parent=dict(pending=[dict(edge_id='E',path_index=0,segment_index=1,original_reason='no_qualified_axis_annotation_on_this_vertical_segment')],counts=dict(current_known=0))
    return doc,graph,dict(records=records),parent,dict(seeds=dict(records=[seed]))


class Tests(unittest.TestCase):
    def test_expanded_qualified_seed_composes_original_bend_without_whole_values(self):
        args=fixture();before=copy.deepcopy(args[1:]);out=compose(*args,native_items(args[0],args[1]),'a'*64)
        self.assertEqual(out['counts']['new_known'],1);self.assertEqual(out['records'][0]['nominal_mm'],300)
        self.assertEqual(out['records'][0]['continuity_evidence']['bends'][0]['source_arms'],2)
        self.assertIsNone(out['records'][0]['physical_length_mm']);self.assertFalse(out['records'][0]['whole_edge_DN_assigned'])
        self.assertEqual(args[1:],before)

    def test_real_third_arm_duplicate_native_line_and_foreign_Z_block(self):
        for kind in ['T','duplicate','Z']:
            args=fixture();doc=args[0]
            if kind=='T':doc.modelspace().add_line((10,0),(14,0),dxfattribs={'layer':LAYERS['supply']})
            elif kind=='duplicate':doc.modelspace().add_line((10,0),(10,8),dxfattribs={'layer':LAYERS['supply']})
            else:
                line=list(doc.modelspace().query('LINE'))[1];line.dxf.start=(10,0,1);line.dxf.end=(10,8,1)
            with self.subTest(kind=kind):self.assertEqual(compose(*args,native_items(doc,args[1]),'a'*64)['records'],[])

    def test_new_caption_conflicting_seeds_and_unwitnessed_target_stay_pending(self):
        for kind in ['caption','conflict','source','branch_seed']:
            args=fixture();doc=args[0]
            if kind=='caption':doc.modelspace().add_text('DN125',dxfattribs={'insert':(10.2,3),'height':.3,'rotation':90})
            elif kind=='conflict':args[4]['seeds']['records'].append(dict(args[4]['seeds']['records'][0],nominal_mm=200))
            elif kind=='source':args[2]['records'][1]['native_source_status']='unresolved'
            else:args[4]['seeds']['records'][0]['source_scope_expansion']['branch_DN_used_as_main_seed']=True
            with self.subTest(kind=kind):self.assertEqual(compose(*args,native_items(doc,args[1]),'a'*64)['records'],[])

    def test_stale_or_partial_route_and_ambiguous_original_scope_do_not_pass(self):
        for kind in ['partial','stale']:
            args=fixture()
            if kind=='partial':args[2]['records'].pop(0)
            else:args[2]['records'][0]['scope_points'][0][0]+=1
            with self.subTest(kind=kind),self.assertRaises(ValueError):compose(*args,native_items(args[0],args[1]),'a'*64)
        args=fixture();args[3]['pending'][0]['original_reason']='native_source_LINE_not_yet_witnessed'
        self.assertEqual(compose(*args,native_items(args[0],args[1]),'a'*64)['records'],[])


if __name__=='__main__':unittest.main()
