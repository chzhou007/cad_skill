import copy
import unittest
from fragment_component_index import classify, build, restore
from native_fragment_ball_contacts import collect
from test_native_fragment_ball_contacts import scene


class Tests(unittest.TestCase):
    def test_compare_complete_existing_profiles_without_rematching_or_hiding_conflicts(self):
        inventory=dict(added_components=[dict(edge_id='A',source_top_handle='H')],
            components=[dict(edge_id='A',equipment_type='球阀')])
        provider=dict(records=[dict(edge_id='A',correspondence_observations=[dict(
            domain='separate_named_external_port',floor=1,grouped_axis_edges=['A'],
            plan_edges=['P'],mapping_id='M')])],plan_exploded_component_reading_inventories={
            '1':dict(rows=[dict(edge_id='P',equipment_type='ball_valve')])})
        before=copy.deepcopy(provider)
        self.assertTrue(classify(provider,inventory)[0]['adopted'])
        inventory['components'].append(dict(edge_id='A',equipment_type='球阀'))
        result=classify(provider,inventory)[0]
        self.assertFalse(result['adopted']);self.assertEqual(result['status'],'source_detail_profile_difference')
        self.assertEqual(provider,before)

    def test_build_original_source_geometry_existing_type_and_exact_restoration(self):
        doc,native,insert,pipe,old,routing=scene(45,-1,(0,0,-1))
        inventory=collect(doc,native,[old],routing)
        parent=dict(edges=copy.deepcopy(native['edges']),nodes=[],
            instances=[dict(id='OLD',name='original',source_device_name=old['device_name'],edge_id=old['edge_id'],source_top_handle='UNRELATED')],
            types=[dict(code='BALL',label='Ball Valve',block='H-PICPNT-91')],symbols={'BALL':dict(paths=[])},
            transform=dict(originX=0,originY=0,scale=1))
        for e in parent['edges']:e['equipment_inventory']=[]
        before=copy.deepcopy(parent)
        records=[dict(source_handle=insert.dxf.handle,adopted=True)]
        result,audit=build(parent,native,inventory,records,doc,'a'*64,'b'*64)
        self.assertEqual(restore(result),before);self.assertEqual(parent,before)
        self.assertEqual(result['instances'][0],parent['instances'][0]);self.assertEqual(result['symbols'],parent['symbols'])
        self.assertEqual(result['instances'][-1]['type'],'BALL');self.assertTrue(result['instances'][-1]['sourceGeometry'])
        self.assertEqual(audit['added_count'],1)
        with self.assertRaises(ValueError):build(parent,native,inventory,[],doc,'a'*64,'b'*64)


if __name__=='__main__':unittest.main()
