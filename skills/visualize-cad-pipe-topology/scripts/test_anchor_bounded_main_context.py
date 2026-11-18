import copy,unittest
from anchor_bounded_main_context import collect
def fixture():
    axis=dict(edge_id='A',system='supply',start_node_id='T1',end_node_id='T2',start_floor=2,end_floor=2,attribute_paths=[[[0,0],[100,0]]])
    plan=dict(edge_id='P',system='supply',attribute_paths=[[[0,0],[200,0]]])
    row=dict(mapping_id='M',floor=2,system='supply',plan_edges=['P'],iso_edges=['A'],plan_start='P1',plan_end='P2',iso_start='T1',iso_end='T2',source_group_ids=['G'])
    metric=dict(mapping_id='M',projection=dict(value_mm=200,pieces=[dict(plan_edge='P',length_mm=200,points=[[0,0],[200,0]])],installed_whole_edge_length_mm=None),reader='inherited_native_plan_projection')
    proof=dict(local_topology_changed=False,axis_graph_changed=False,component_assignments_changed=False,DN_used_for_mapping=False,source_hashes=dict(axis_graph='I',axis_source='S',plan_source_2='P',plan_graph_2='G'),floors={'2':dict(records=[row],groups=[dict(mapping_id='G',native=dict(iso=dict(snapshot=dict(edges=[copy.deepcopy(axis)])),plan=dict(snapshot=dict(edges=[plan]))))],metrics=[metric])})
    graph=dict(edges=[axis],sourceFullPlanBatchAttributes=dict(source_hashes=dict(identity_graph='I',axis_source='S')));rendered=copy.deepcopy(graph)
    DN={'2':{'P':dict(nominal_mm=300,system='supply',scope_paths=copy.deepcopy(plan['attribute_paths']),human_accepted=False,lineage=[])}}
    return graph,rendered,proof,DN
class Tests(unittest.TestCase):
    def test_current_native_child_and_qualified_local_DN_leave_installed_length_unknown(self):
        g,v,p,d=fixture();before=copy.deepcopy((g,v,p,d));r=collect(g,v,p,d,{'axis_graph':'R','rendered_graph':'V'})
        self.assertEqual(r['axis_edges'],1);row=r['records'][0];self.assertEqual(row['nominal_mm'],300);self.assertEqual(row['plan_horizontal_projection']['value_mm'],200);self.assertTrue(row['whole_axis_DN_selected']);self.assertIsNone(row['whole_axis_physical_length_mm']);self.assertEqual((g,v,p,d),before)
    def test_changed_geometry_floor_prior_owner_and_DN_scope_are_rejected(self):
        for mode in('geometry','floor','owner','DN_scope','nominal_bool'):
            g,v,p,d=fixture()
            if mode=='geometry':v['edges'][0]['attribute_paths'][0][1][0]=99
            elif mode=='floor':g['edges'][0]['end_floor']=3
            elif mode=='owner':g['edges'][0]['cross_view_attributes']={'old':True}
            elif mode=='DN_scope':d['2']['P']['scope_paths']=[[[0,0],[99,0]]]
            else:d['2']['P']['nominal_mm']=True
            with self.assertRaises(ValueError,msg=mode):collect(g,v,p,d,{})
    def test_missing_metric_does_not_invent_zero_or_lose_mapping(self):
        g,v,p,d=fixture();p['floors']['2']['metrics'][0]['projection']=None;d['2']['P']['nominal_mm']=None
        row=collect(g,v,p,d,{})['records'][0];self.assertIsNone(row['plan_horizontal_projection']);self.assertIsNone(row['nominal_mm']);self.assertFalse(row['whole_axis_DN_selected']);self.assertEqual(row['mapping_id'],'M')
    def test_duplicate_source_interval_writer_is_rejected(self):
        g,v,p,d=fixture();p['floors']['2']['records']*=2
        with self.assertRaisesRegex(ValueError,'geometry changed'):collect(g,v,p,d,{})
if __name__=='__main__':unittest.main()
