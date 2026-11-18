import copy,math,unittest
import ezdxf
from native_balancing_valve_recovery import recover,ports
from native_line_path_evidence import LAYERS

def fixture(rotation=0,mirror=1,extrusion=(0,0,1)):
    d=ezdxf.new();b=d.blocks.new('平衡阀');offset=(50,70)
    for a,c in[((-1,-2),(1,-2)),((-1,2),(1,2)),((-1,-2),(1,2)),((1,-2),(-1,2)),((.5,-1),(1.1,-1)),((.5,1),(1.1,1))]:
        b.add_line((a[0]+offset[0],a[1]+offset[1]),(c[0]+offset[0],c[1]+offset[1]))
    ins=d.modelspace().add_blockref('平衡阀',(1000,2000),dxfattribs=dict(rotation=rotation,xscale=mirror,extrusion=extrusion,layer='COMPONENT'))
    geo=ports(ins);p,q=geo['ports_WCS'];v=[q[i]-p[i]for i in range(3)];a=[p[i]-4*v[i]for i in range(3)];z=[q[i]+4*v[i]for i in range(3)]
    line=d.modelspace().add_line(a,z,dxfattribs={'layer':LAYERS['return']})
    edge=dict(edge_id='E1',system='return',connection_mode='continuous_original_cad_pipe',attribute_paths=[[a[:2],z[:2]]],source_handles=[line.dxf.handle])
    return d,dict(edges=[edge]),ins,line

class Tests(unittest.TestCase):
    def test_wcs_ports_handle_offsets_rotation_mirror_and_negative_OCS(self):
        for rot in(0,45,90,180):
            for mirror in(-1,1):
                for extrusion in((0,0,1),(0,0,-1)):
                    d,g,ins,line=fixture(rot,mirror,extrusion);before=copy.deepcopy(g);old=[dict(device_name='old',edge_id='E0',source_top_handle='OLD')];r=recover(d,g,old)
                    with self.subTest(rot=rot,mirror=mirror,extrusion=extrusion):
                        self.assertEqual(r['counts']['added_components'],1);self.assertEqual(r['components'][0],old[0]);self.assertEqual(g,before)
                        x=r['records'][0];self.assertEqual(x['system'],'return');self.assertTrue(x['source_layer_differs_from_pipe']);self.assertGreater(math.dist(x['geometry']['center'],list(ins.dxf.insert)[:2]),1)
    def test_crossing_pipe_does_not_own_two_ports_and_foreign_Z_is_excluded(self):
        d,g,ins,line=fixture();x,y=ports(ins)['center'];d.modelspace().add_line((x-20,y,1),(x+20,y,1),dxfattribs={'layer':LAYERS['supply']});d.modelspace().add_line((x-20,y,0),(x+20,y,0),dxfattribs={'layer':LAYERS['supply']})
        self.assertEqual(recover(d,g,[])['counts']['added_components'],1)
    def test_duplicate_native_line_or_graph_scope_is_unresolved(self):
        for kind in('source','graph'):
            d,g,ins,line=fixture()
            if kind=='source':d.modelspace().add_line(line.dxf.start,line.dxf.end,dxfattribs={'layer':line.dxf.layer})
            else:g['edges'].append(dict(g['edges'][0],edge_id='E2'))
            r=recover(d,g,[])
            with self.subTest(kind=kind):self.assertEqual(r['counts']['added_components'],0);self.assertEqual(len(r['records']),1)
    def test_prior_claims_preserved_and_second_application_adds_nothing(self):
        d,g,ins,line=fixture();r=recover(d,g,[]);self.assertEqual(r['added_components'][0]['equipment_type'],'balancing_valve');r2=recover(d,g,r['components']);self.assertEqual(r2['counts']['added_components'],0);self.assertEqual(r2['components'],r['components']);self.assertEqual(r2['records'][0]['status'],'already_in_inventory')
    def test_family_name_and_full_signature_required(self):
        d,g,ins,line=fixture();d.blocks['平衡阀'].delete_entity(list(d.blocks['平衡阀'])[-1]);self.assertEqual(recover(d,g,[])['records'][0]['status'],'unsupported_native_family_geometry')
        d,g,ins,line=fixture();d.blocks.rename_block('平衡阀','OTHER');ins.dxf.name='OTHER';self.assertEqual(recover(d,g,[])['counts']['native_population'],0)
    def test_source_handle_and_system_constraints_are_preserved(self):
        for kind in('handle','system','connection'):
            d,g,ins,line=fixture();e=g['edges'][0]
            if kind=='handle':e['source_handles']=['OTHER']
            elif kind=='system':e['system']='supply'
            else:e['connection_mode']='unproven_gap'
            with self.subTest(kind=kind):self.assertEqual(recover(d,g,[])['counts']['added_components'],0)
if __name__=='__main__':unittest.main()
