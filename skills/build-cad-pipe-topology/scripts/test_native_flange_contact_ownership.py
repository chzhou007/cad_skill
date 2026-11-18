import copy
import math
import unittest

from native_balancing_valve_recovery import ports, recover as centre_recovery
from native_flange_contact_ownership import footprint, flange_contacts, recover
from native_line_path_evidence import LAYERS
from test_native_balancing_valve_recovery import fixture


def offset_fixture(rotation=0, mirror=1, extrusion=(0,0,1), offset=.2):
    doc, graph, insert, pipe = fixture(rotation,mirror,extrusion)
    p,q=ports(insert)['ports_WCS'];v=[q[i]-p[i]for i in range(3)];length=math.hypot(*v[:2]);normal=[-v[1]/length,v[0]/length,0]
    a=[pipe.dxf.start[i]+offset*normal[i]for i in range(3)]
    b=[pipe.dxf.end[i]+offset*normal[i]for i in range(3)]
    pipe.dxf.start=a;pipe.dxf.end=b;graph['edges'][0]['attribute_paths']=[[a[:2],b[:2]]]
    return doc,graph,insert,pipe


class Tests(unittest.TestCase):
    def test_offset_native_contacts_rotation_mirror_negative_OCS_and_preservation(self):
        for rotation in (0,45,90,180):
            for mirror in (-1,1):
                for extrusion in ((0,0,1),(0,0,-1)):
                    with self.subTest(rotation=rotation,mirror=mirror,extrusion=extrusion):
                        doc,graph,insert,pipe=offset_fixture(rotation,mirror,extrusion)
                        old=[dict(device_name='OLD',edge_id='OTHER',source_top_handle='OLD',unknown_resistance=None)]
                        before=copy.deepcopy(graph);centre=ports(insert)['center'];origin=list(insert.dxf.insert)
                        self.assertEqual(centre_recovery(doc,graph,old)['counts']['added_components'],0)
                        result=recover(doc,graph,old,[insert.dxf.handle]);row=result['records'][0]
                        self.assertEqual(result['counts']['added_components'],1)
                        self.assertEqual(row['assigned_edge_id'],'E1');self.assertEqual(row['system'],'return')
                        self.assertAlmostEqual(row['symbol_centre_offset_mm'],.2)
                        self.assertEqual(len(row['native_pipe_candidates'][0]['flange_contacts']),2)
                        self.assertEqual(result['components'][0],old[0]);self.assertEqual(graph,before)
                        self.assertEqual(ports(insert)['center'],centre);self.assertEqual(list(insert.dxf.insert),origin)
                        self.assertEqual(result['unknown_physical_parameters_filled'],0)
                        self.assertFalse(row['physical_connector_length_assigned'])

    def test_nearby_parallel_line_outside_actual_flanges_is_not_assigned(self):
        doc,graph,insert,pipe=offset_fixture(offset=1.2)
        self.assertEqual(recover(doc,graph,[],[insert.dxf.handle])['counts']['added_components'],0)

    def test_crossing_body_and_single_flange_contacts_are_not_assignments(self):
        for kind in ('cross','one_flange'):
            doc,graph,insert,pipe=offset_fixture();geo=footprint(insert)
            if kind=='cross':
                x,y,z=geo['center_WCS'];a=[x-20,y,z];b=[x+20,y,z]
            else:
                p,q=geo['ports_WCS'];a=list(pipe.dxf.start);b=[(p[i]+q[i])/2 for i in range(3)]
            pipe.dxf.start=a;pipe.dxf.end=b;graph['edges'][0]['attribute_paths']=[[a[:2],b[:2]]]
            with self.subTest(kind=kind):self.assertEqual(recover(doc,graph,[],[insert.dxf.handle])['counts']['added_components'],0)

    def test_foreign_Z_and_sloping_Z_do_not_pass_XY_contact(self):
        for kind in ('foreign','slope'):
            doc,graph,insert,pipe=offset_fixture();a=list(pipe.dxf.start);b=list(pipe.dxf.end)
            a[2]=1 if kind=='foreign'else 0;b[2]=1
            pipe.dxf.start=a;pipe.dxf.end=b
            with self.subTest(kind=kind):self.assertEqual(recover(doc,graph,[],[insert.dxf.handle])['counts']['added_components'],0)

    def test_source_or_graph_duplicates_and_wrong_service_are_unresolved(self):
        for kind in ('source_duplicate','graph_duplicate','service','handle','mode'):
            doc,graph,insert,pipe=offset_fixture();edge=graph['edges'][0]
            if kind=='source_duplicate':doc.modelspace().add_line(pipe.dxf.start,pipe.dxf.end,dxfattribs={'layer':pipe.dxf.layer})
            elif kind=='graph_duplicate':graph['edges'].append(dict(edge,edge_id='E2'))
            elif kind=='service':edge['system']='supply'
            elif kind=='handle':edge['source_handles']=['OTHER']
            else:edge['connection_mode']='unproven_gap'
            with self.subTest(kind=kind):self.assertEqual(recover(doc,graph,[],[insert.dxf.handle])['counts']['added_components'],0)

    def test_incomplete_signature_prior_claims_and_unknown_handles_fail_closed(self):
        doc,graph,insert,pipe=offset_fixture();old=[dict(device_name='existing',source_top_handle=insert.dxf.handle)]
        with self.assertRaises(ValueError):recover(doc,graph,old,[insert.dxf.handle])
        with self.assertRaises(ValueError):recover(doc,graph,[],['MISSING'])
        doc.blocks['平衡阀'].delete_entity(list(doc.blocks['平衡阀'])[-1])
        self.assertEqual(recover(doc,graph,[],[insert.dxf.handle])['counts']['added_components'],0)

    def test_nonfinite_and_invalid_tolerance_are_rejected(self):
        doc,graph,insert,pipe=offset_fixture()
        for tol in (0,-1,float('nan'),float('inf')):
            with self.subTest(tol=tol),self.assertRaises(ValueError):recover(doc,graph,[],[],tol)
        with self.assertRaises(ValueError):flange_contacts(footprint(insert),[float('nan'),0,0],[1,0,0])

if __name__=='__main__':unittest.main()
