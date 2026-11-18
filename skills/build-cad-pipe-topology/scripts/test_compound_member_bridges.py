import copy,math,unittest
import ezdxf
from compound_member_bridges import clip_chain,annotation_barrier,component_order,match_components
from test_native_inline_joint_path_coverage import fixture
from native_inline_joint_path_coverage import collect
class Tests(unittest.TestCase):
    def test_native_inline_clipping_rotated_mirrored_and_reversed_keeps_joint_lengths_unknown(self):
        for rotation,mirror in[(0,False),(90,False),(180,True),(270,True)]:
            args=fixture(rotation,mirror);doc,graph=args[:2];source=collect(*args)['records'][0];edge=graph['edges'][0];nodes={n['node_id']:n for n in graph['nodes']};a,b=[[nodes[edge[k]]['x'],nodes[edge[k]]['y']]for k in('start_node_id','end_node_id')];size=math.dist(a,b);u=[(b[i]-a[i])/size for i in(0,1)];start=[a[i]+2*u[i]for i in(0,1)];end=[b[i]-2*u[i]for i in(0,1)]
            for ends in[(start,end),(end,start)]:
                pieces=clip_chain(source,*ends);self.assertAlmostEqual(sum(p['measured_plan_pipe_projection_mm']or 0 for p in pieces),36);self.assertEqual(len(pieces),3);self.assertTrue(all(p['physical_inline_length_mm']is None for p in pieces))
    def test_unwitnessed_gap_duplicate_span_and_partial_joint_are_rejected(self):
        source=dict(private_ordered_pieces=[dict(kind='native_pipe',points=[[0,0],[10,0]],source_line_handle='L1'),dict(kind='native_inline_joint',points=[[10,0],[20,0]],source_handle='J'),dict(kind='native_pipe',points=[[20,0],[30,0]],source_line_handle='L2')])
        with self.assertRaisesRegex(ValueError,'cuts an inline'):clip_chain(source,[15,0],[28,0])
        bad=copy.deepcopy(source);bad['private_ordered_pieces'][1]['points'][0]=[12,0]
        with self.assertRaisesRegex(ValueError,'gap or overlap'):clip_chain(bad,[2,0],[28,0])
        bad=copy.deepcopy(source);bad['private_ordered_pieces'].append(copy.deepcopy(bad['private_ordered_pieces'][0]))
        with self.assertRaisesRegex(ValueError,'gap or overlap'):clip_chain(bad,[2,0],[28,0])
    def test_native_component_identity_duplicate_source_and_order_profile_are_not_counts(self):
        args=fixture();doc,graph,rows=args[:3];edge=graph['edges'][0];nodes={n['node_id']:n for n in graph['nodes']};ends=[[nodes[edge[k]]['x'],nodes[edge[k]]['y']]for k in('start_node_id','end_node_id')];ordered=component_order(doc,rows,edge,*ends);self.assertEqual(len(ordered),1);self.assertEqual(len(match_components(ordered,ordered,[ordered[0]['source_handle']])),1)
        with self.assertRaisesRegex(ValueError,'duplicate'):component_order(doc,rows+copy.deepcopy(rows),edge,*ends)
        other=copy.deepcopy(ordered);other[0]['block_profile_sha256']='different'
        with self.assertRaisesRegex(ValueError,'profile'):match_components(ordered,other,[ordered[0]['source_handle']])
    def test_external_supported_text_direction_does_not_create_false_scope(self):
        doc=ezdxf.new();m=doc.modelspace();m.add_text('DN300(3.600)/DN200(3.000)',dxfattribs=dict(insert=(100,0),height=10,rotation=0));annotation_barrier(doc,[0,0],[50,0])
        m.add_text('DN150',dxfattribs=dict(insert=(25,0),height=2))
        with self.assertRaisesRegex(ValueError,'native plan DN'):annotation_barrier(doc,[0,0],[50,0])
    def test_rotated_mirrored_and_nested_annotation_barriers(self):
        for rotation in(0,90,180,270):
            doc=ezdxf.new();u=[math.cos(math.radians(rotation)),math.sin(math.radians(rotation))];doc.modelspace().add_text('DN150',dxfattribs=dict(insert=(25*u[0],25*u[1]),height=2,rotation=rotation))
            with self.assertRaises(ValueError):annotation_barrier(doc,[0,0],[50*u[0],50*u[1]])
        doc=ezdxf.new();block=doc.blocks.new('NEST');block.add_text('DN150',dxfattribs=dict(insert=(0,0),height=2));doc.modelspace().add_blockref('NEST',(25,0))
        with self.assertRaisesRegex(ValueError,'nested'):annotation_barrier(doc,[0,0],[50,0])
        doc=ezdxf.new();doc.modelspace().add_text('DN150',dxfattribs=dict(insert=(25,0),height=2,text_generation_flag=2))
        with self.assertRaises(ValueError):annotation_barrier(doc,[0,0],[50,0])
if __name__=='__main__':unittest.main()
