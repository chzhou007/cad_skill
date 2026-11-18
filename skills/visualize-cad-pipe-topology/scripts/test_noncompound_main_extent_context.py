import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from noncompound_main_extent_context import collect
from native_main_endpoint_extent import qualify
from test_native_main_endpoint_extent import fixture

def data():
    plan,axis,row,metric=fixture(True,False);r=qualify(plan,axis,row,250.,metric,[0,45,135]);h='a'*64
    scope=dict(mapping_id='M',plan_edges=['E'],plan_drawn_nominal_mm=250.,source_sha256=dict(plan=h,iso=h),graph_sha256=dict(plan=h,iso=h))
    axis['edges'][0]['batch_plan_attribute_scopes']=scope
    r.update(old_scope=scope,native_source_evidence=dict(plan=dict(snapshot=dict(edges=copy.deepcopy(plan['edges'])))),plan_DN_record=dict(nominal_mm=250.,scope_paths=plan['edges'][0]['attribute_paths']),DN_status='retained_qualified_plan_DN',source_hashes={v:dict(source_sha256=h,graph_sha256=h)for v in('plan','iso')},metric_reader='native_plan_projection')
    proof=dict(mode='native_noncompound_undirected_main_extents_v1',compound_parent_replayed=True,local_topology_changed=False,source_paths_mutated=False,human_accepted=False,installed_lengths_assigned=0,existing_correspondences_unchanged=True,source_hashes=dict(raw_axis_graph=h,member_proof=h),records=[r],counts=dict(requalified_main_edges=1),retained_member_axis_edges=[])
    prior=dict(compound_member_mains=dict(source_bindings=dict(native_proof=h),records=[]))
    return axis,copy.deepcopy(axis),proof,dict(axis_graph=h,rendered_graph=h,native_proof=h,member_proof=h),prior

class Tests(unittest.TestCase):
    def test_adds_complete_length_without_promoting_net_cut_or_installed_length(self):
        args=data();before=copy.deepcopy(args);result=collect(*args);r=result['records'][0]
        self.assertEqual((r['nominal_mm'],r['complete_horizontal_centerline_route_mm']),(250.,10.));self.assertEqual(args,before)
        self.assertIsNone(r['whole_installed_length_mm']);self.assertIsNone(r['net_pipe_cut_length_mm']);self.assertFalse(r['related_HIL_confirmation_inherited'])
    def test_native_identity_change_or_prior_member_ownership_fails(self):
        args=list(data());args[1]['edges'][0]['end_node_id']='OTHER'
        with self.assertRaisesRegex(ValueError,'raw identity'):collect(*args)
        args=list(data());args[4]['ordered_anchor_branches']=dict(records=[dict(axis_edge_id='E')])
        with self.assertRaisesRegex(ValueError,'existing attribute owner'):collect(*args)
    def test_altered_plan_DN_missing_parent_and_fake_installed_value_fail(self):
        args=list(data());args[2]['records'][0]['nominal_mm']=300
        with self.assertRaisesRegex(ValueError,'plan DN'):collect(*args)
        args=list(data());args[4]['compound_member_mains']['source_bindings']['native_proof']='b'*64
        with self.assertRaisesRegex(ValueError,'parent differs'):collect(*args)
        args=list(data());args[2]['records'][0]['whole_installed_length_mm']=0
        with self.assertRaisesRegex(ValueError,'promoted'):collect(*args)
    def test_localized_component_names_require_same_original_instance_and_edge_owner(self):
        args=list(data());args[0]['edges'][0]['equipment_inventory']=[dict(count=1,device_names=['球阀-BV1'])]
        args[1]['edges'][0]['equipment_inventory']=[dict(count=1,device_names=['Ball Valve-BV1'])]
        args[1]['instances']=[dict(id='I1',edge_id='E',source_device_name='球阀-BV1',name='Ball Valve-BV1',source_top_handle='H1')]
        r=collect(*args);self.assertEqual(r['records'][0]['component_instance_identities'][0]['instance_id'],'I1')
        args[1]['instances'][0]['source_device_name']='球阀-BV2'
        with self.assertRaisesRegex(ValueError,'identities or edge ownership'):collect(*args)
if __name__=='__main__':unittest.main()
