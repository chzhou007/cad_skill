import copy, unittest
from test_reconstruct_native_block_branches import fixture
from reconstruct_native_block_branches import reconstruct
from axis_unbranched_vertical_DN import native_items
from axis_omission_vertical_DN import omission_corridor
from axis_omission_vertical_DN import owned_annotation_guard
from pipe_annotation_attributes import source_texts
from native_line_path_evidence import LAYERS
import ezdxf


def case(mirror=False):
    doc,g,inventory,policy,hashes=fixture(True,mirror)
    rebuilt=reconstruct(doc,g,inventory,policy,hashes);edge=rebuilt['edges'][0]
    rows={}
    for pi,path in enumerate(edge['attribute_paths']):
        for si in range(len(path)-1):
            rows['E',pi,si]=dict(edge_id='E',path_index=pi,segment_index=si,system='supply',scope_points=path[si:si+2],native_source_status='single_source_line_covers')
    return doc,rebuilt,edge,rows


class OmissionInheritanceTests(unittest.TestCase):
    def test_opposite_system_owned_caption_does_not_hide_same_system_transition_or_F(self):
        doc=ezdxf.new();doc.modelspace().add_text('DN80',dxfattribs={'insert':(50,5),'height':10})
        doc.modelspace().add_text('DN100',dxfattribs={'insert':(50,10),'height':10})
        texts=source_texts(doc,'axis','S');seed=dict(nominal_mm=80,observations=[dict(source_text=texts[0])])
        index=dict(probes=[dict(t,text='DN1') for t in texts],claims={},F_strokes=[],nested_DN={})
        edge=dict(edge_id='A',system='supply');other=dict(edge_id='B',system='return');edges={'A':edge,'B':other}
        proof=dict(current_edge_id='B',source_text=texts[1],native_binding=dict(layer=LAYERS['return'],current_graph_owners=['B']))
        corridor=[dict(scope_points=[[0,0],[100,0]])]
        with self.assertRaisesRegex(ValueError,'another in-scope'):
            owned_annotation_guard(doc,[seed],corridor,index,'S',edge,edges,{})
        result=owned_annotation_guard(doc,[seed],corridor,index,'S',edge,edges,{texts[1]['handle']:proof})
        self.assertEqual(len(result['independently_replayed_opposite_system_annotations']),1)
        other['system']='supply';proof['native_binding']['layer']=LAYERS['supply']
        with self.assertRaisesRegex(ValueError,'another in-scope'):
            owned_annotation_guard(doc,[seed],corridor,index,'S',edge,edges,{texts[1]['handle']:proof})
        other['system']='return';proof['native_binding']['layer']=LAYERS['return'];index['F_strokes']=[([40,-10],[40,20])]
        with self.assertRaisesRegex(ValueError,'F leader'):
            owned_annotation_guard(doc,[seed],corridor,index,'S',edge,edges,{texts[1]['handle']:proof})

    def check_case(self,doc,g,edge,rows):
        return omission_corridor(doc,g,edge,rows['E',0,0],rows['E',1,0],rows,native_items(doc,g),'S')

    def test_native_pair_replayed_with_mirror_without_length_or_topology_mutation(self):
        for mirror in (False,True):
            doc,g,e,rows=case(mirror);before=copy.deepcopy(g)
            result=self.check_case(doc,g,e,rows)
            self.assertEqual(len(result['markers']),2)
            self.assertIsNone(result['physical_length_mm'])
            self.assertFalse(result['physical_T_crossed'])
            self.assertFalse(result['inline_joint_crossed'])
            self.assertEqual(g,before)

    def test_same_edge_does_not_override_moved_glyph_or_stale_path_or_system(self):
        for variant in ('glyph','snapshot','system','third_marker','wrong_path'):
            with self.subTest(variant=variant):
                doc,g,e,rows=case();root=doc.entitydb[e['source_insert_handle']]
                if variant=='glyph':
                    marker=next(x for x in doc.blocks[root.dxf.name] if x.dxftype()=='LWPOLYLINE' and x.dxf.layer=='DIM_SYMB')
                    marker.translate(0,2,0)
                elif variant=='snapshot':e['source_native_block_branch']['endpoint_snapshot']['start_node_id']='OTHER'
                elif variant=='system':e['system']='return'
                elif variant=='third_marker':doc.blocks[root.dxf.name].add_lwpolyline([(i,i%2) for i in range(6)],dxfattribs={'layer':'DIM_SYMB'})
                else:rows['E',1,0]=rows['E',2,0]
                with self.assertRaises(ValueError):self.check_case(doc,g,e,rows)

if __name__=='__main__':unittest.main()
