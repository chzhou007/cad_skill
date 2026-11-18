import copy,unittest
from rebuild_qualified_plan_scope_extension import match_current,PROVIDER_MODE
from match_source_checked_crossview_paths import selected_snapshot
def fixture():
    def graph(eid,a,b):return dict(nodes=[dict(node_id=a,node_type='tee',x=0,y=0,floor=3),dict(node_id=b,node_type='tee',x=10,y=0,floor=3)],edges=[dict(edge_id=eid,start_node_id=a,end_node_id=b,start_floor=3,end_floor=3,system='supply',attribute_paths=[[[0,0],[10,0]]])])
    plan,axis=graph('P','PA','PB'),graph('E','A','B');current=dict(kind='same_floor_T_to_T_main',floor=3,system='supply',plan_edges=['P'],iso_edges=['E'],plan_start='PA',plan_end='PB',iso_start='A',iso_end='B',mapping_id='BATCH-STABLE')
    old=dict(current,kind='main_between_equipment_branches',mapping_id='HISTORICAL-PROVIDER',plan_snapshot=selected_snapshot(plan,['P']),iso_snapshot=selected_snapshot(axis,['E']))
    scope=dict(mapping_id='BATCH-STABLE',plan_drawn_nominal_mm=None,plan_DN_records=[dict(status='source_scope_unverified')])
    raw=copy.deepcopy(axis);raw['sourceFullPlanBatchAttributes']=dict(records=[scope]);raw['edges'][0]['batch_plan_attribute_scopes']=scope
    metric=dict(status='native_plan_horizontal_projection_partial_length',value_mm=10,pieces=[dict(plan_edge='P',path_index=0,segment_index=0,source_line_handle='L',length_mm=10)],installed_whole_edge_length_mm=None)
    value=dict(mapping_id='HISTORICAL-PROVIDER',kind='main_between_equipment_branches',floor=3,system='supply',plan_edges=['P'],iso_edges=['E'],diameter=dict(nominal_mm=150,lineage=[dict(evidence=[dict(evidence_id='source:T')])]),horizontal_projection=metric,physical_source_identity_resolved=False,whole_axis_physical_length_mm=None,group_id='G')
    provider=dict(mode=PROVIDER_MODE,records=[value],physical_values_fused=False,local_graphs_mutated=False,human_accepted=False)
    return provider,dict(records=[old]),[current],plan,axis,raw,[0,45,135]
class Tests(unittest.TestCase):
    def test_specific_native_provider_over_unknown_preserves_current_and_historical_IDs(self):
        a=fixture();before=copy.deepcopy(a);records,pending=match_current(*a);self.assertEqual(a,before);self.assertFalse(pending);self.assertEqual(records[0]['mapping_id'],'BATCH-STABLE');self.assertEqual(records[0]['provider_mapping_id'],'HISTORICAL-PROVIDER');self.assertEqual(records[0]['complete_horizontal_centerline_route_mm'],10);self.assertFalse(records[0]['physical_source_identity_resolved'])
    def test_conflicts_and_known_values_are_not_overwritten(self):
        a=fixture();a[5]['sourceFullPlanBatchAttributes']['records'][0]['plan_DN_records'][0]['status']='conflict';self.assertEqual(match_current(*a)[0],[])
        a=fixture();a[5]['sourceFullPlanBatchAttributes']['records'][0]['plan_drawn_nominal_mm']=150;self.assertEqual(match_current(*a)[0],[])
        a=fixture();a[5]['sourceFullPlanBatchAttributes']['records'][0]['plan_drawn_nominal_mm']=200
        with self.assertRaises(ValueError):match_current(*a)
    def test_changed_source_scope_or_physical_identity_promotion_is_rejected(self):
        for kind in('snapshot','identity'):
            a=fixture()
            if kind=='snapshot':a[1]['records'][0]['plan_snapshot']['edges'][0]['attribute_paths'][0][1][0]=11
            else:a[0]['records'][0]['physical_source_identity_resolved']=True
            with self.assertRaises(ValueError):match_current(*a)
if __name__=='__main__':unittest.main()
