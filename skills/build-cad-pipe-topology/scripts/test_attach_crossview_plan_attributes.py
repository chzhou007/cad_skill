import copy,math,unittest
from confirm_crossview_paths import snapshot
from attach_crossview_plan_attributes import attach
from test_native_plan_projection_lengths import fixture
from native_plan_projection_lengths import unit_evidence

class CrossviewAttributeAttachmentTests(unittest.TestCase):
    def fixture(self,many=False):
        doc,plan,policy,coverage,_=fixture();axis=dict(nodes=[dict(node_id='T',node_type='tee',floor=2,x=0,y=0),dict(node_id='EQ',node_type='equipment',floor=2,x=0,y=10)],edges=[dict(edge_id='I',start_node_id='T',end_node_id='EQ',system='supply',path_points=[[0,0],[0,10]],attribute_paths=[[[0,0],[0,10]]],path_length=10)],sourceFloorLabelRepair={'kept':True},metadata={'hil_ready':False})
        ids=['I']
        if many:
            axis['nodes'].append(dict(node_id='J',node_type='tee',floor=2,x=0,y=5))
            axis['edges'][0].update(end_node_id='J',path_points=[[0,0],[0,5]],attribute_paths=[[[0,0],[0,5]]],path_length=5)
            axis['edges'].append(dict(edge_id='I2',start_node_id='J',end_node_id='EQ',system='supply',path_points=[[0,5],[0,10]],attribute_paths=[[[0,5],[0,10]]],path_length=5));ids.append('I2')
        rec=dict(system='supply',equipment_id='EQ',floor=2,plan_edges=['P'],iso_edges=ids,iso_snapshot=copy.deepcopy(snapshot(axis,ids)))
        mapping=dict(records=[rec],evidence=dict(local=dict(plan=dict(coverage=coverage),iso=dict(coverage=dict(edges=[dict(edge_id=e['edge_id'],segments=[dict(index=0,start=e['path_points'][0],end=e['path_points'][1],drawing_length=e['path_length'])]) for e in axis['edges']])))))
        return axis,mapping,plan,unit_evidence(doc,policy),{'supply':dict(nominal_mm=None,status='candidate_disagreement_unresolved')},dict(plan='P',isometric='I')
    def test_known_horizontal_projection_does_not_overwrite_axis_length_or_old_repairs(self):
        args=self.fixture();before=copy.deepcopy(args[0]);out,records=attach(*args)
        self.assertEqual(out['nodes'],before['nodes']);self.assertEqual(out['sourceFloorLabelRepair'],before['sourceFloorLabelRepair']);self.assertEqual(args[0],before)
        edge=out['edges'][0];attrs=edge.pop('cross_view_attributes');self.assertEqual(edge,before['edges'][0])
        self.assertEqual(attrs['horizontal_projection']['edge_value_mm'],800);self.assertIsNone(attrs['whole_edge_physical_length_mm']);self.assertIsNone(attrs['diameter']['nominal_mm'])
        self.assertFalse(attrs['axis_vertical_drawing_strokes'][0]['inter_floor']);self.assertIsNone(attrs['axis_vertical_drawing_strokes'][0]['physical_length_mm'])
    def test_one_to_many_does_not_copy_route_total_into_each_axis_edge(self):
        out,records=attach(*self.fixture(True))
        self.assertEqual(records[0]['plan_horizontal_projection_mm'],800)
        self.assertTrue(all(e['cross_view_attributes']['horizontal_projection']['edge_value_mm'] is None for e in out['edges']))
    def test_changed_local_topology_and_preexisting_fusion_require_reentry(self):
        for kind in ('system','point','existing'):
            args=list(self.fixture())
            if kind=='system':args[0]['edges'][0]['system']='return'
            elif kind=='point':args[0]['edges'][0]['path_points'][1][1]+=1
            else:args[0]['edges'][0]['cross_view_attributes']={}
            with self.assertRaises(ValueError):attach(*args)

if __name__=='__main__':unittest.main()
