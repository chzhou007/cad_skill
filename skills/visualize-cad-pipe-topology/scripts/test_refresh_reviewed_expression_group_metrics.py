import copy,unittest
from refresh_reviewed_expression_group_metrics import adopt,delta
from reviewed_expression_metrics import MODE

def fixture():
    edge=dict(edge_id='A',system='return',start_node_id='T1',end_node_id='T2',floor_start=2,floor_end=2,attribute_paths=[[[0,0],[3,0]]])
    inputs={k:dict(path=k,sha256='a'*64)for k in ['plan_graph','plan_source','iso_source','iso_graph']}
    row=dict(scope_id='R',status='native_bounded_range_correspondence',views=dict(plan=dict(route=dict(edges=['P'])),iso=dict(route=dict(edges=['A']),source_snapshot=dict(edges=[copy.deepcopy(edge)]))))
    r=dict(scope_id='R',floor=2,system='return',axis_edges=['A'],plan_edges=['P'],per_axis_edge_length_allocation=None,per_axis_edge_DN_assignment=None,complete_group_physical_length_mm=None,human_accepted=False)
    proof=dict(mode=MODE,original_native_group_owner_reexecuted=True,original_plan_metric_reader_reused=True,per_axis_edge_values_assigned=0,physical_lengths_assigned=0,DN_values_assigned=0,human_accepted=False,inputs=dict(inputs,scope_proof=dict(sha256='b'*64)),records=[r])
    return dict(current_rendered_graph_sha256='c'*64,old={'preserved':True}),dict(edges=[edge]),proof,dict(inputs=inputs,records=[row])

class GroupAdoptionTests(unittest.TestCase):
    def test_exact_old_context_retained_and_group_metadata_does_not_assign_pipe_values(self):
        c,g,p,s=fixture();before=copy.deepcopy((c,g,p,s));new=adopt(c,g,p,s,'d'*64)
        self.assertEqual({k:v for k,v in new.items()if k!='reviewed_expression_group_metrics'},c);self.assertEqual((c,g,p,s),before)
        row=new['reviewed_expression_group_metrics']['records'][0];self.assertIsNone(row['per_axis_edge_length_allocation']);self.assertEqual(row['axis_members'][0]['attribute_paths'],g['edges'][0]['attribute_paths'])
    def test_other_source_geometry_floor_and_held_scope_block(self):
        for kind in ['source','geometry','floor','held','allocation']:
            with self.subTest(kind=kind):
                c,g,p,s=fixture()
                if kind=='source':p['inputs']['plan_source']=dict(path='other',sha256='e'*64)
                elif kind=='geometry':g['edges'][0]['attribute_paths'][0][1][0]+=1
                elif kind=='floor':g['edges'][0]['floor_start']=3
                elif kind=='held':s['records'][0]['status']='held_local_source_evidence'
                else:p['records'][0]['per_axis_edge_length_allocation']=0
                with self.assertRaises(ValueError):adopt(c,g,p,s,'d'*64)
    def test_delta_protects_all_old_numeric_values_and_unrelated_edges(self):
        c,g,p,s=fixture();context=adopt(c,g,p,s,'d'*64);before=[dict(edge_id='A',values=dict(old=10)),dict(edge_id='B',values={})];after=copy.deepcopy(before)
        after[0]['values'].update(shared_plan_metric_scope_ids='R',shared_plan_metric_scopes_json='[]',shared_plan_metric_source_sha256='a'*64)
        self.assertEqual(delta(before,after,context)['new_per_axis_edge_length_values'],0)
        after[0]['values']['old']=11
        with self.assertRaises(ValueError):delta(before,after,context)

if __name__=='__main__':unittest.main()
