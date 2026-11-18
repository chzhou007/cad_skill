import copy,unittest
from test_axis_floor_elevation_texts import scene
from axis_attribute_source_routing import collect as routing
from axis_continuous_source_vertical_DN import modelspace_seeds
from axis_unbranched_vertical_DN import native_items
from axis_direct_endpoint_level_evidence import collect
from native_line_path_evidence import LAYERS,_on


def fixture(same_floor=False,upper='3.200'):
    doc=scene();space=doc.modelspace();sh='a'*64;gh='b'*64;layer=LAYERS['supply']
    space.add_line((18000,12000),(22000,12000),dxfattribs={'layer':layer})
    space.add_line((20000,12000),(20000,22000),dxfattribs={'layer':layer})
    space.add_line((20000,22000),(22000,22000),dxfattribs={'layer':layer})
    space.add_text('DN300(3.200)',dxfattribs={'insert':(18500,12015),'height':10})
    space.add_text('DN200('+upper+')',dxfattribs={'insert':(20500,22015),'height':10})
    graph=dict(metadata=dict(source_sha256=sh),nodes=[dict(node_id=n,node_type='tee' if n=='T' else 'virtual_equipment',x=x,y=y,floor=f) for n,x,y,f in [('T',20000,12000,2),('L',18000,12000,2),('B',22000,12000,2),('E',22000,22000,2 if same_floor else 3)]],edges=[])
    for eid,start,end,path in [('L','L','T',[[18000,12000],[20000,12000]]),('B','T','B',[[20000,12000],[22000,12000]]),('E','T','E',[[20000,12000],[20000,22000],[22000,22000]])]:
        graph['edges'].append(dict(edge_id=eid,start_node_id=start,end_node_id=end,system='supply',attribute_paths=[path],floor_start=2,floor_end=2 if same_floor or eid!='E' else 3))
    route=routing(graph,dict(isometric_horizontal_directions_degrees=[0,45,135],source_rule_evidence='native source fixture'))
    for row in route['records']:
        hits=[e for e in space.query('LINE') if e.dxf.layer==layer and all(_on(p,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05) for p in row['scope_points'])]
        row.update(native_source_status='single_source_line_covers' if len(hits)==1 else 'ambiguous',native_witnesses=[dict(scope='modelspace',source_handle=e.dxf.handle) for e in hits])
    route['inputs']=dict(source=dict(sha256=sh),graph=dict(sha256=gh))
    seeds=modelspace_seeds(doc,graph,route,sh,gh)
    return doc,graph,route,seeds,native_items(doc,graph),sh,gh


class EndpointLevelEvidenceTests(unittest.TestCase):
    def test_same_offsets_on_different_floors_do_not_produce_zero_or_drawing_Y_length(self):
        a=fixture();before=copy.deepcopy(a[1:]);r=collect(*a)
        self.assertEqual(a[1:],before);self.assertEqual(len(r['records']),1)
        row=r['records'][0];self.assertEqual(row['candidate_difference_in_source_level_units'],'5.000')
        self.assertEqual([e['floor'] for e in row['endpoints']],[2,3]);self.assertIsNone(row['physical_length_mm'])
        self.assertFalse(r['unit_selected']);self.assertFalse(r['pipe_level_reference_confirmed']);self.assertEqual(r['physical_lengths_assigned'],0)
        self.assertEqual([e['connection_evidence'][0]['kind'] for e in row['endpoints']],['original_native_T','original_native_two_arm_bend'])

    def test_same_floor_offset_difference_and_unproved_third_arm(self):
        r=collect(*fixture(same_floor=True,upper='2.600'));self.assertEqual(r['records'][0]['candidate_difference_in_source_level_units'],'0.600')
        a=list(fixture());a[0].modelspace().add_line((20000,22000),(20000,22100),dxfattribs={'layer':LAYERS['supply']});a[4]=native_items(a[0],a[1])
        r=collect(*a);self.assertEqual(r['records'],[]);self.assertIn('another source arm',r['pending'][0]['reason'])

if __name__=='__main__':unittest.main()
