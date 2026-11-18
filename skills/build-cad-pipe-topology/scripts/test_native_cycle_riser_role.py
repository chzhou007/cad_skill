import unittest
import ezdxf
from rebuild_typed_cycle_riser_batch import native_riser_circle,LAYERS

class Tests(unittest.TestCase):
    def fixture(self):
        doc=ezdxf.new();c=doc.modelspace().add_circle((10,20),225,dxfattribs={'layer':LAYERS['supply']})
        g=dict(nodes=[dict(node_id='R',subtype='out_of_plane_riser',system='supply',x=10,y=20),dict(node_id='T')],edges=[dict(edge_id='E',start_node_id='R',end_node_id='T',system='supply')]);g['nodes'][0]['source_handle']=c.dxf.handle
        return doc,g,c
    def test_original_circle_and_single_incident_branch_are_replayed(self):
        d,g,c=self.fixture();r=native_riser_circle(d,g,'R','supply');self.assertEqual(r['circle_handle'],c.dxf.handle);self.assertEqual(r['incident_edge'],'E')
    def test_wrong_layer_center_normal_and_incidence_do_not_prove_riser(self):
        for kind in('layer','center','OCS','degree','role'):
            d,g,c=self.fixture()
            if kind=='layer':c.dxf.layer=LAYERS['return']
            elif kind=='center':c.dxf.center=(100,200,0)
            elif kind=='OCS':c.dxf.extrusion=(0,0,-1)
            elif kind=='degree':g['edges'].append(dict(edge_id='E2',start_node_id='R',end_node_id='T',system='supply'))
            else:g['nodes'][0]['subtype']='out_of_plane_interface'
            with self.subTest(kind=kind),self.assertRaises(ValueError):native_riser_circle(d,g,'R','supply')

if __name__=='__main__':unittest.main()
