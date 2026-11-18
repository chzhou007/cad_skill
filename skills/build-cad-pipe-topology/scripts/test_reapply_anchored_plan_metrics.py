import copy,unittest,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
from reapply_anchored_plan_metrics import overlap,joint_scope,clearable,COARSE,inventory_from,compute

class Tests(unittest.TestCase):
    def test_complete_batch_keeps_dependency_paths_through_ordered_component_stage(self):
        with tempfile.TemporaryDirectory()as temporary:
            root=Path(temporary);inputs={};sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            def put(key,value):
                p=root/(key+'.json');p.write_bytes((json.dumps(value)+'\n').encode());inputs[key]=dict(path=str(p),sha256=sha(p))
            nodes=lambda ids:[dict(node_id=n,node_type='tee',floor=3,x=i,y=0)for i,n in enumerate(ids)]
            edge=lambda eid,a,b:dict(edge_id=eid,start_node_id=a,end_node_id=b,system='return',floor_start=3,floor_end=3,attribute_paths=[[[0,0],[1,0]]],path_points=[[0,0],[1,0]])
            put('axis_graph',dict(nodes=nodes(['A','B']),edges=[edge('E','A','B')]))
            for f in(1,2,3):
                put('plan_graph_'+str(f),dict(nodes=nodes(['P','Q'])if f==3 else[],edges=[edge('PE','P','Q')]if f==3 else[]));put('plan_source_'+str(f),{});put('unit_policy_'+str(f),{})
                p=root/('plan_components_'+str(f)+'.csv');p.write_bytes(b'edge_id,equipment_type\n');inputs['plan_components_'+str(f)]=dict(path=str(p),sha256=sha(p))
            p=root/'axis_components.csv';p.write_bytes(b'edge_id,equipment_type\n');inputs['axis_components']=dict(path=str(p),sha256=sha(p))
            for key in('axis_source','current_T_source_config'):put(key,{})
            put('viewer_manifest',dict(attributeValueContext={}))
            provider=dict(original_provider_inventory_inputs={k:v for k,v in inputs.items()if k.startswith('plan_graph_')or k=='axis_graph'},ordinary_junction_mappings={str(f):({'P':'A','Q':'B'}if f==3 else{})for f in(1,2,3)},remaining_horizontal_attributes=[dict(edge_id='E',floor=3,complete_centerline=False,next_scope='known')],records=[dict(edge_id='E',correspondence_observations=[dict(domain='ordinary_local_graph',plan_edges=['PE'],grouped_axis_edges=['E'],mapping_id='M')])])
            metric=dict(mapping_id='M',axis_edge_id='E',plan_edge_id='PE',plan_nodes=['P','Q'],axis_nodes=['A','B'],complete_horizontal_centerline_mm=1)
            manifest=dict(inputs=inputs,horizontal_directions_degrees=[0]);profile=dict(records=[],profiles={})
            with patch('reapply_anchored_plan_metrics.checked_parent',return_value=provider),patch('reapply_anchored_plan_metrics.read_source',return_value=(object(),{})),patch('reapply_anchored_plan_metrics.unit_evidence',return_value={}),patch('reapply_anchored_plan_metrics.current_plan_reader',return_value=lambda *args:{}),patch('reapply_anchored_plan_metrics.native_tee',return_value={}),patch('reapply_anchored_plan_metrics.coverage',return_value={}),patch('reapply_anchored_plan_metrics.qualify',return_value=metric),patch('reapply_anchored_plan_metrics.native_component_profiles',return_value=profile):
                result=compute(manifest)
                self.assertEqual(result['counts']['complete_centerlines'],1)
                def mutate(*args):Path(inputs['plan_source_3']['path']).write_bytes(b'changed');return metric
                with patch('reapply_anchored_plan_metrics.qualify',side_effect=mutate),self.assertRaisesRegex(ValueError,'input changed'):compute(manifest)

    def test_native_joint_scope_uses_finite_extents_rotation_and_mirror(self):
        for path,joint in [([[0,0],[10,0]],[[20,0,0],[21,0,0]]),([[0,0],[0,-10]],[[0,-20,0],[0,-21,0]])]:
            edge=dict(system='supply',attribute_paths=[path]);origin=dict(system='supply',contact_points_wcs=joint,physical_length_mm=None)
            result=joint_scope(edge,[origin]);self.assertEqual(result['excluded_joint_origins'],[origin]);self.assertEqual(result['physical_joint_lengths_assigned'],0)
        self.assertFalse(overlap([0,0],[10,0],[5,-1],[5,1]));self.assertFalse(overlap([0,0],[10,0],[10,0],[11,0]))
        with self.assertRaises(ValueError):joint_scope(dict(system='supply',attribute_paths=[[[0,0],[10,0]]]),[dict(system='supply',contact_points_wcs=[[4,0,0],[5,0,0]])])

    def test_only_proven_coarse_split_hold_is_clearable(self):
        holds=[dict(reasons=[COARSE])];edge=dict(path_length_scope=COARSE,path_length_complete=False,split_source_edge=dict(edge_id='PARENT'))
        self.assertTrue(clearable(edge,holds));self.assertFalse(clearable({},[]))
        for changed in [dict(edge,path_length_scope='omission_unknown'),dict(edge,split_source_edge=None)]:
            with self.assertRaises(ValueError):clearable(changed,holds)
        with self.assertRaises(ValueError):clearable(edge,[dict(reasons=['actual_joint_inside_scope'])])

    def test_actual_metric_inventory_keeps_DN_components_and_old_member_identity(self):
        observation=dict(mapping_id='OLD',domain='ordinary_local_graph');original=dict(records=[dict(edge_id='A',correspondence_observations=[observation]),dict(edge_id='B',correspondence_observations=[observation])],remaining_horizontal_attributes=[dict(edge_id='A',floor=3,known_whole_DN=250,complete_centerline=False,next_scope='known',attributes=dict(old='kept')),dict(edge_id='B',floor=3,known_whole_DN=None,complete_centerline=False,next_scope='known',attributes={})],counts={},current_horizontal_frontier=dict(pure_horizontal_complete=5),member_domain_observations=[dict(id='MEMBER:X')],ordinary_junction_mappings={'3':{'P':'A'}},current_component_inventory={'unknown_resistance':None})
        before=copy.deepcopy(original);proof=dict(records=[dict(axis_edge_id=e,source_scope_id='METRIC:'+e,complete_horizontal_centerline_mm=100,original_observation=observation)for e in('A','B')]);effective=[dict(edge_id=e,values=dict(anchored_metric_mapping_id='METRIC:'+e,anchored_metric_complete_centerline_mm=100))for e in('A','B')]
        result=inventory_from(original,proof,effective);self.assertEqual(original,before);self.assertEqual(result['new_attribute_complete_axis_edges'],['A']);self.assertEqual(result['current_horizontal_frontier']['pure_horizontal_complete'],6);self.assertEqual(result['remaining_horizontal_attributes'][0]['known_whole_DN'],None);self.assertEqual(result['current_component_inventory']['unknown_resistance'],None)
        effective[0]['values']['anchored_metric_complete_centerline_mm']=0
        with self.assertRaises(ValueError):inventory_from(original,proof,effective)

if __name__=='__main__':unittest.main()
