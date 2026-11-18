import copy,json,unittest
from pathlib import Path
from test_native_balancing_valve_recovery import fixture as native_fixture
from native_balancing_valve_recovery import recover
from recovered_component_graph_bridge import build,restore,edge_bases
POLICY=json.loads((Path(__file__).resolve().parents[1]/'assets/native-balancing-display-type.json').read_text(encoding='utf8'))
class Tests(unittest.TestCase):
    def fixture(self,rotation=0,mirror=1,extrusion=(0,0,1),second=False):
        doc,native,insert,line=native_fixture(rotation,mirror,extrusion)
        if second:doc.modelspace().add_blockref('平衡阀',(1000,2008),dxfattribs={'layer':'COMPONENT'})
        native['edges'][0].update(start_node_id='A',end_node_id='B',floor_start=1,floor_end=1)
        old=dict(device_name='old',edge_id='E1',source_top_handle='OLD');proof=recover(doc,native,[old]);parent=copy.deepcopy(native);parent.update(nodes=[dict(node_id='A'),dict(node_id='B')],transform=dict(originX=0,originY=0,scale=1),symbols={'OLD':{'markup':'old native symbol'}},types=[dict(code='OLD',label='Old')],instances=[dict(id='I0001',name='Old Valve',source_device_name='old',edge_id='E1',type='OLD',source_top_handle='OLD')])
        parent['edges'][0]['equipment_inventory']=[dict(type='OLD',label='Old',count=1,device_names=['Old Valve'])]
        return parent,native,proof,doc
    def test_native_offsets_rotation_mirror_negative_OCS_and_old_identity_preserved(self):
        for rot,mirror,ocs in((0,1,(0,0,1)),(45,-1,(0,0,1)),(90,1,(0,0,-1)),(180,-1,(0,0,-1))):
            args=self.fixture(rot,mirror,ocs);before=copy.deepcopy(args[:3]);g,a=build(*args,POLICY,'a'*64,'b'*64)
            self.assertEqual(g['instances'][0],args[0]['instances'][0]);self.assertEqual(g['instances'][1]['display_source_chain'],[args[2]['added_components'][0]['source_top_handle']]);self.assertTrue(g['instances'][1]['sourceGeometry']);self.assertEqual(restore(g,a),args[0]);self.assertEqual(args[:3],before);self.assertEqual(edge_bases(g),edge_bases(args[0]));self.assertEqual(a['unknown_physical_parameters_assigned'],0)
    def test_two_valves_on_one_edge_have_distinct_stable_ids_and_combined_inventory(self):
        args=self.fixture(second=True);g,a=build(*args,POLICY,'a'*64,'b'*64);self.assertEqual(len(g['instances']),3);self.assertEqual(g['edges'][0]['equipment_inventory'][-1]['count'],2);self.assertEqual(len(set(a['added_instance_ids'])),2);self.assertEqual(restore(g,a),args[0])
    def test_wrong_source_owner_extent_position_prior_claim_and_type_collision_fail(self):
        for mode in('owner','extent','position','claim','type','replayed','old_owner'):
            args=list(self.fixture())
            if mode=='owner':args[2]['records'][0]['system']='supply'
            elif mode=='extent':args[0]['edges'][0]['attribute_paths'][0][0][0]+=1
            elif mode=='position':args[2]['added_components'][0]['x']='0';args[2]['components'][-1]['x']='0'
            elif mode=='claim':args[0]['instances'][0]['source_top_handle']=args[2]['added_components'][0]['source_top_handle']
            elif mode=='type':args[0]['symbols'][POLICY['code']]={}
            elif mode=='replayed':args[2]['prior_components_unchanged']=False
            else:args[0]['instances'][0]['edge_id']='other'
            with self.subTest(mode=mode),self.assertRaises(ValueError):build(*args,POLICY,'a'*64,'b'*64)
if __name__=='__main__':unittest.main()
