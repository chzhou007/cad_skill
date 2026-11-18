import copy,unittest
import ezdxf
from native_typed_inline_body_DN import qualify_templates,partition,historical_types
from native_nested_direct_caption_DN import projection,neutral_guard
from native_inline_anchors import block_signature
from native_line_path_evidence import LAYERS
from ezdxf.disassemble import recursive_decompose

class InheritedTypedBodyTests(unittest.TestCase):
    def fixture(self,rotation=0,mirror=1):
        doc=ezdxf.new('R2013');body=doc.blocks.new('KNOWN-YS')
        for a,b in [((-.5,0),(2.5,0)),((-.5,-.5),(-.5,.5)),((2.5,-.5),(2.5,.5)),((0,0),(1,-1)),((1,-1),(2,-.5))]:body.add_line(a,b,dxfattribs={'color':2})
        block=doc.blocks.new('UNIT');pipe=block.add_line((0,-10),(0,10),dxfattribs={'layer':LAYERS['supply']});component=block.add_blockref('KNOWN-YS',(0,0),dxfattribs={'rotation':90});root=doc.modelspace().add_blockref('UNIT',(100,100),dxfattribs={'rotation':rotation,'xscale':mirror});native=[e for e in recursive_decompose([root])if e.dxftype()=='LINE'and e.dxf.layer==LAYERS['supply']][0];child=next(e for e in root.virtual_entities()if e.dxftype()=='INSERT');xy=list(child.ocs().to_wcs(child.dxf.insert));edge=dict(edge_id='E',system='supply',source_insert_handle=root.dxf.handle,attribute_paths=[[list(native.dxf.start)[:2],list(native.dxf.end)[:2]]]);graph=dict(edges=[edge]);row=dict(source_top_handle=root.dxf.handle,source_block_name='KNOWN-YS',type_code='YS',equipment_type='Y型汽/水过滤器',assignment_status='assigned',edge_id='E',device_name='DEVICE/YS1',x=str(xy[0]),y=str(xy[1]));catalogue=[dict(legend_equipment_type='Y型汽/水过滤器',matched_source_symbols='KNOWN-YS',used_in_sh16_edge_graph='yes',graph_role='edge_attribute_only')];spec=dict(block_name='KNOWN-YS',equipment_type='Y型汽/水过滤器',type_code='YS',block_signature_sha256=block_signature(doc,'KNOWN-YS'));templates=qualify_templates(doc,doc,catalogue,{'KNOWN-YS':('Y型汽/水过滤器','YS')},[spec]);neutral=projection(doc,graph,'a'*64)[-1];return doc,graph,[row],neutral,templates,spec,catalogue
    def test_complete_native_identity_partitions_only_known_body(self):
        d,g,rows,n,t,_,_=self.fixture();before=copy.deepcopy((g,rows));kept,p=partition(d,g,rows,n,t);self.assertEqual(len(kept),0);self.assertEqual(len(p['excluded_known_body_primitives']),5);self.assertEqual((g,rows),before);self.assertFalse(p['physical_ports_inferred']);self.assertFalse(p['unknown_neutral_geometry_excluded'])
    def test_rotation_and_mirror_preserve_exact_source_instance_identity(self):
        for angle,mirror in[(30,1),(90,-1),(180,-1)]:
            d,g,r,n,t,_,_=self.fixture(angle,mirror);kept,p=partition(d,g,r,n,t)
            with self.subTest(angle=angle,mirror=mirror):self.assertFalse(kept);self.assertEqual(len(p['qualified_typed_instances']),1)
    def test_missing_wrong_or_duplicate_inventory_never_excludes_geometry(self):
        for mutate in(lambda r:r.clear(),lambda r:r[0].update(edge_id='OTHER'),lambda r:r.append(copy.deepcopy(r[0]))):
            d,g,r,n,t,_,_=self.fixture();mutate(r);kept,p=partition(d,g,r,n,t);self.assertEqual(kept,n);self.assertFalse(p['excluded_known_body_primitives'])
    def test_symbol_name_or_partial_geometry_cannot_establish_type(self):
        d,g,r,n,t,s,c=self.fixture();bad=copy.deepcopy(s);bad['block_signature_sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'geometry or catalogue'):qualify_templates(d,d,c,{'KNOWN-YS':('Y型汽/水过滤器','YS')},[bad])
        c[0]['graph_role']='physical_node'
        with self.assertRaises(ValueError):qualify_templates(d,d,c,{'KNOWN-YS':('Y型汽/水过滤器','YS')},[s])
    def test_unknown_neutral_competitor_keeps_original_half_text_height_guard(self):
        d,g,r,n,t,_,_=self.fixture();unknown=dict(root_handle='UNKNOWN',child_handle='REAL-LAYER0',XYZ=[[98.5,99,0],[98.5,104,0]],layer='0');kept,p=partition(d,g,r,[*n,unknown],t);self.assertEqual(kept,[unknown]);text=dict(rotation=90,position=[98,102],height=2);item=dict(XYZ=[[100,90,0],[100,110,0]])
        with self.assertRaisesRegex(ValueError,'neutral layer0'):neutral_guard(text,item,kept)
    def test_original_type_declaration_is_read_as_data(self):
        self.assertEqual(historical_types("COMPONENT_BLOCK_TYPES={'KNOWN-YS':('Y型汽/水过滤器','YS')}"),{'KNOWN-YS':('Y型汽/水过滤器','YS')})
        with self.assertRaises(ValueError):historical_types('OTHER = {}')

if __name__=='__main__':unittest.main()
