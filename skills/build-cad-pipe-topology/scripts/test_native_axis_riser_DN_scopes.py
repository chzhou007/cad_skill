import copy,hashlib,unittest
import ezdxf
from confirm_crossview_paths import encode
from native_line_path_evidence import LAYERS,collect as lines
from native_axis_riser_DN_scopes import attribute,project,implementation_hashes


def fixture():
    doc=ezdxf.new();m=doc.modelspace();g=dict(metadata=dict(source_sha256='S'),nodes=[],edges=[]);choices=[];corridors=[];seeds=[]
    for system,x in [('supply',0),('return',40)]:
        for tag,p,floor in [('A',[x-10,0],1),('T',[x,10],2),('B',[x+10,20],3),('C',[x+5,10],2)]:
            g['nodes'].append(dict(node_id=system+tag,node_type='physical_junction' if tag=='T' else 'interface',x=p[0],y=p[1],floor=floor))
        vertical=m.add_line((x,0),(x,20),dxfattribs=dict(layer=LAYERS[system])).dxf.handle
        low=m.add_line((x-10,0),(x,0),dxfattribs=dict(layer=LAYERS[system])).dxf.handle
        high=m.add_line((x,20),(x+10,20),dxfattribs=dict(layer=LAYERS[system])).dxf.handle
        branch=m.add_line((x,10),(x+5,10),dxfattribs=dict(layer=LAYERS[system])).dxf.handle
        for tag,start,end,path,hs in [('L','A','T',[[x-10,0],[x,0],[x,10]],[low,vertical]),('U','T','B',[[x,10],[x,20],[x+10,20]],[vertical,high]),('F','T','C',[[x,10],[x+5,10]],[branch])]:
            g['edges'].append(dict(edge_id=system+tag,start_node_id=system+start,end_node_id=system+end,system=system,attribute_paths=[path],connection_mode='continuous_original_cad_pipe',source_handles=hs))
            if tag!='F':choices.append(dict(edge_id=system+tag,line_handles=hs))
        v=m.add_text('DN450',dxfattribs=dict(layer='AN',height=.3,rotation=90,insert=(x+.4,15)))
        h=m.add_text('DN300(3.200)',dxfattribs=dict(layer='AN',height=.3,insert=(x+4,20.4)))
        m.add_text('DN200(2.900)',dxfattribs=dict(layer='AN',height=.3,insert=(x-7,.4)))
        m.add_text('DN150',dxfattribs=dict(layer='AN',height=.3,insert=(x+2,10.4)))
        seeds.extend([dict(text_handle=v.dxf.handle,edge_id=system+'U',segment_index=0,expected_text='DN450'),dict(text_handle=h.dxf.handle,edge_id=system+'U',segment_index=1,expected_text='DN300(3.200)')])
        corridors.append(dict(corridor_id=system,system=system,junction=system+'T',source_line_handle=vertical,branch_frontier_edge=system+'F',
            lower=dict(edge_id=system+'L',segment_index=1,floor_pair=[1,2]),upper=dict(edge_id=system+'U',segment_index=0,floor_pair=[2,3])))
    m.add_text('二层',dxfattribs=dict(layer='AN',height=.3,insert=(80,10)))
    evidence=lines(doc,g,dict(source_sha256='S',graph_sha256='G',selections=choices),'S','G')
    sp=dict(source_sha256='S',graph_sha256='G',line_evidence_sha256=hashlib.sha256(encode(evidence)).hexdigest(),text_layers=['AN'],selections=seeds)
    return doc,g,evidence,sp,dict(scope_id='native-two-corridor-test',corridors=corridors)


class Tests(unittest.TestCase):
    def test_two_services_inherit450_through_actual_T_only_and_preserve_every_local_field(self):
        doc,g,ev,sp,p=fixture();before=copy.deepcopy(g);out=attribute(doc,g,ev,sp,p,'S','G')
        self.assertEqual(g,before);self.assertEqual(len(out['records']),4)
        for r in out['records']:
            self.assertEqual(r['nominal_mm'],450);self.assertFalse(r['whole_local_edge_DN_assigned']);self.assertIsNone(r['physical_length_mm'])
            self.assertEqual(r['segment_index'],1 if r['edge_id'].endswith('L') else 0)
            self.assertIn('inherited' if r['edge_id'].endswith('L') else 'direct',r['status'])
        self.assertEqual(out['checked_DN_scope']['non_through_branch_frontiers_excluded_from_main_inheritance'],['returnF','supplyF'])
        self.assertFalse(out['floor_interface_correspondence_confirmed']);self.assertFalse(out['physical_values_fused'])
    def test_new_change_annotation_prevents_hidden_inheritance(self):
        doc,g,ev,sp,p=fixture();doc.modelspace().add_text('DN400',dxfattribs=dict(layer='AN',height=.3,rotation=90,insert=(.4,5)))
        out=attribute(doc,g,ev,sp,p,'S','G');rows={r['edge_id']:r for r in out['records']}
        self.assertEqual(rows['supplyL']['nominal_mm'],400);self.assertEqual(rows['supplyU']['nominal_mm'],450)
        self.assertEqual(rows['returnL']['nominal_mm'],450)
    def test_compound_DN_and_duplicate_change_on_one_segment_fail_closed(self):
        for text in ['DN400/DN450','DN400']:
            doc,g,ev,sp,p=fixture();m=doc.modelspace()
            m.add_text(text,dxfattribs=dict(layer='AN',height=.3,rotation=90,insert=(.4,5)))
            if text=='DN400':m.add_text('DN350',dxfattribs=dict(layer='AN',height=.3,rotation=90,insert=(.4,7)))
            with self.subTest(text=text),self.assertRaises(ValueError):attribute(doc,g,ev,sp,p,'S','G')
    def test_branch_wrong_system_wrong_through_LINE_floor_and_pending_T_block(self):
        for case in ['branch_system','through','floor','pending','duplicate','horizontal','witness']:
            doc,g,ev,sp,p=fixture()
            if case=='branch_system':g['edges'][2]['system']='return'
            elif case=='through':p['corridors'][0]['source_line_handle']='OTHER'
            elif case=='floor':p['corridors'][0]['lower']['floor_pair']=[2,3]
            elif case=='pending':g['nodes'][1]['review_required']=True
            elif case=='duplicate':p['corridors'].append(copy.deepcopy(p['corridors'][0]))
            elif case=='horizontal':p['corridors'][0]['lower']['segment_index']=0
            else:ev['edges'][0]['segments'][1]['source_handle']='OTHER'
            with self.subTest(case=case),self.assertRaises(ValueError):project(doc,g,ev,p['corridors'],'S','G')
    def test_isolated_LEADER_allowed_but_long_connected_annotation_reaching_scope_blocks(self):
        doc,g,ev,sp,p=fixture();m=doc.modelspace();leader=m.add_leader([(100,0),(110,0),(110,10)],dxfattribs=dict(layer='AN'))
        out=attribute(doc,g,ev,sp,p,'S','G');self.assertEqual(out['source_annotation_inventory']['native_LEADER_isolation']['isolated_leader_handles'],[leader.dxf.handle])
        m.add_line((0,5),(110,5),dxfattribs=dict(layer='AN'))
        with self.assertRaisesRegex(ValueError,'LEADER component reaches'):attribute(doc,g,ev,sp,p,'S','G')
    def test_hash_closure_includes_inherited_catalog_DN_and_all_new_readers(self):
        hs=implementation_hashes()
        for name in ['native_scope_leader_isolation.py','native_axis_riser_DN_scopes.py','checked_plan_DN_scope_attributes.py','diameter_tee_inheritance.py','native_segment_dn_candidates_v2.py','plan_pipe_diameter_scopes.py']:
            self.assertIn(name,hs)


if __name__=='__main__':unittest.main()
