import copy
import math
import unittest
import ezdxf
from native_ball_contact_reapplication import footprint,reapply
from native_line_path_evidence import LAYERS

def fixture(rotation=0,mirror=1,extrusion=(0,0,1)):
    doc=ezdxf.new();block=doc.blocks.new('H-PICPNT-91')
    block.add_lwpolyline([(49.5,70.1,1),(50.5,70.1,1)],format='xyb',close=True)
    for a,b in [((48,67),(48,73)),((52,67),(52,73)),((48,68),(52,72))]:block.add_line(a,b)
    insert=doc.modelspace().add_blockref('H-PICPNT-91',(1000,2000),dxfattribs=dict(rotation=rotation,xscale=mirror,extrusion=extrusion))
    geometry=footprint(insert);p,q=geometry['ports_WCS'];v=[q[i]-p[i]for i in range(3)];length=math.hypot(*v[:2]);normal=[-v[1]/length,v[0]/length,0]
    a=[p[i]-4*v[i]+.2*normal[i]for i in range(3)];b=[q[i]+4*v[i]+.2*normal[i]for i in range(3)]
    real=doc.modelspace().add_line(a,b,dxfattribs={'layer':LAYERS['supply']})
    centre=geometry['center_WCS'];c=[centre[i]-10*normal[i]for i in range(3)];d=[centre[i]+10*normal[i]for i in range(3)]
    crossing=doc.modelspace().add_line(c,d,dxfattribs={'layer':LAYERS['supply']})
    edge=lambda eid,line:dict(edge_id=eid,system='supply',connection_mode='continuous_original_cad_pipe',attribute_paths=[[list(line.dxf.start)[:2],list(line.dxf.end)[:2]]],source_handles=[line.dxf.handle])
    graph=dict(edges=[edge('MAIN',real),edge('BRANCH',crossing)])
    row=dict(device_name='DEVICE/VALVE-03',equipment_type='球阀',source_top_handle=insert.dxf.handle,owner_equipment='DEVICE',edge_id='BRANCH',x=str(centre[0]),y=str(centre[1]),assignment_x=str(centre[0]),assignment_y=str(centre[1]),edge_distance='0',assignment_status='assigned',assignment_basis='old_nearest_position',original_edge_id='',resistance=None)
    return doc,graph,insert,real,row

class Tests(unittest.TestCase):
    def test_actual_both_flange_contacts_override_nearer_crossing_keep_equipment_and_geometry(self):
        for rotation in (0,45,90,180):
            for mirror in (-1,1):
                for extrusion in ((0,0,1),(0,0,-1)):
                    with self.subTest(rotation=rotation,mirror=mirror,extrusion=extrusion):
                        doc,graph,insert,pipe,row=fixture(rotation,mirror,extrusion);before=copy.deepcopy(graph);origin=list(insert.dxf.insert)
                        result=reapply(doc,graph,[row]);new=result['components'][0]
                        self.assertEqual(new['edge_id'],'MAIN');self.assertEqual(new['owner_equipment'],'DEVICE')
                        self.assertEqual(new['device_name'],row['device_name']);self.assertIsNone(new['resistance'])
                        self.assertEqual((new['x'],new['y']),(row['x'],row['y']));self.assertEqual(new['original_edge_id'],'BRANCH')
                        self.assertEqual(result['counts']['reassigned_components'],1);self.assertEqual(graph,before);self.assertEqual(list(insert.dxf.insert),origin)
                        self.assertFalse(result['related_mapping_confirmations_inherited'])

    def test_reapplication_is_idempotent_and_never_adds_unclaimed_components(self):
        doc,graph,insert,pipe,row=fixture();result=reapply(doc,graph,[row]);again=reapply(doc,graph,result['components'])
        self.assertEqual(again['components'],result['components']);self.assertEqual(again['counts']['reassigned_components'],0)
        unclaimed=reapply(doc,graph,[]);self.assertEqual(unclaimed['components'],[]);self.assertEqual(unclaimed['records'][0]['status'],'unclaimed_source_instance')

    def test_duplicate_source_graph_or_prior_claim_keeps_current_inventory(self):
        for kind in ('source','graph','claim'):
            doc,graph,insert,pipe,row=fixture();rows=[row]
            if kind=='source':doc.modelspace().add_line(pipe.dxf.start,pipe.dxf.end,dxfattribs={'layer':pipe.dxf.layer})
            elif kind=='graph':graph['edges'].append(dict(graph['edges'][0],edge_id='ANOTHER'))
            else:rows.append(dict(row,device_name='OTHER'))
            with self.subTest(kind=kind):self.assertEqual(reapply(doc,graph,rows)['components'],rows)

    def test_foreign_Z_incomplete_signature_or_old_system_conflict_is_not_reassigned(self):
        for kind in ('Z','signature','system'):
            doc,graph,insert,pipe,row=fixture()
            if kind=='Z':
                a=list(pipe.dxf.start);b=list(pipe.dxf.end);a[2]=b[2]=1;pipe.dxf.start=a;pipe.dxf.end=b
            elif kind=='signature':doc.blocks['H-PICPNT-91'].delete_entity(list(doc.blocks['H-PICPNT-91'])[-1])
            else:graph['edges'][1]['system']='return'
            with self.subTest(kind=kind):self.assertEqual(reapply(doc,graph,[row])['components'],[row])

if __name__=='__main__':unittest.main()
