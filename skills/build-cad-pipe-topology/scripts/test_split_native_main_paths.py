import copy,unittest
import ezdxf
from split_native_main_paths import split_main

class NativeMainSplitTests(unittest.TestCase):
    def fixture(self):
        doc=ezdxf.new();line=doc.modelspace().add_line((0,0),(1000,0))
        edge=dict(edge_id='M',start_node_id='A',end_node_id='B',system='supply',path=[[0,0],[1000,0]],attribute_paths=[[[0,0],[1000,0]]],path_length=1000,source_handles=[line.dxf.handle],equipment_names=['V1','V2','V3'])
        rows=[dict(edge_id='M',device_name='V'+str(i+1),equipment_type='valve',x=str(x),y='0') for i,x in enumerate((200,550,900))]
        cuts=[dict(source_handle='C1',point=[400,0]),dict(source_handle='C2',point=[700,0])]
        return doc,edge,rows,cuts
    def test_multiple_T_cuts_rebuild_main_and_uniquely_reassign_components(self):
        doc,edge,rows,cuts=self.fixture();before=copy.deepcopy(edge)
        children,assigned,tees=split_main(doc,edge,rows,cuts,'G')
        self.assertEqual([e['path_length'] for e in children],[400,300,300])
        self.assertEqual(len({r['edge_id'] for r in assigned}),3);self.assertEqual(len(tees),2)
        self.assertEqual(edge,before);self.assertEqual([r['edge_id'] for r in rows],['M']*3)
    def test_flex_gap_not_counted_as_native_pipe_and_symbol_is_conserved(self):
        doc=ezdxf.new();m=doc.modelspace();a=m.add_line((0,0),(300,0));b=m.add_line((700,0),(1000,0))
        e=dict(edge_id='M',start_node_id='A',end_node_id='B',system='supply',path=[[0,0],[300,0],[700,0],[1000,0]],attribute_paths=[[[0,0],[300,0]],[[700,0],[1000,0]]],path_length=600,source_handles=[a.dxf.handle,b.dxf.handle],equipment_names=[],source_flexible_joints=[dict(source_handle='J',source_contact_points=[[300,0],[700,0]],physical_length='unknown')])
        children,_,_=split_main(doc,e,[],[dict(source_handle='C1',point=[100,0]),dict(source_handle='C2',point=[900,0])],'G')
        self.assertEqual([x['path_length'] for x in children],[100,400,100])
        self.assertEqual([f['source_handle'] for c in children for f in c.get('source_flexible_joints',[])],['J'])
    def test_component_on_cut_and_parent_attributes_require_reentry(self):
        doc,e,rows,cuts=self.fixture();rows[0]['x']='400'
        with self.assertRaisesRegex(ValueError,'ownership'):split_main(doc,e,rows,cuts,'G')
        doc,e,rows,cuts=self.fixture();e['pipe_diameter_mm']=200
        with self.assertRaisesRegex(ValueError,'remapping'):split_main(doc,e,rows,cuts,'G')
    def test_endpoint_and_repeated_cuts_are_not_physical_Ts(self):
        for points in ([[0,0]],[[400,0],[400,0]]):
            doc,e,rows,cuts=self.fixture();cuts=[dict(source_handle=str(i),point=p) for i,p in enumerate(points)]
            with self.assertRaises(ValueError):split_main(doc,e,rows,cuts,'G')

if __name__=='__main__':unittest.main()
