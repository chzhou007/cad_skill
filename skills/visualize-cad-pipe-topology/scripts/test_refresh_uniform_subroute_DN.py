import copy,unittest
from refresh_uniform_subroute_DN import adopt,delta,SOURCE_MODE

def fixture():
    paths=[[[0,0],[3,0]]]
    e=dict(edge_id='A',system='return',floor_start=2,floor_end=2,start_node_id='T1',end_node_id='T2',attribute_paths=paths)
    r=dict(axis_edge_id='A',system='return',floor=2,axis_nodes=['T1','T2'],axis_attribute_paths=copy.deepcopy(paths),physical_length_mm=None,per_axis_edge_length_allocation=None,human_accepted=False,whole_horizontal_edge=True,nominal_mm=200,horizontal_segment_domains=[dict(path_index=0,segment_index=0,scope_points=copy.deepcopy(paths[0]),direction_class='horizontal',native_source_status='single_source_line_covers')])
    p=dict(mode=SOURCE_MODE,original_native_group_member_gate_and_caption_owners_reexecuted=True,selected_prefix_mapping_freshly_requalified_by_native_group_boundaries_member_roles_and_caption_owners=True,graph_mutated=False,components_changed=False,physical_lengths_assigned=0,vertical_values_assigned=0,human_accepted=False,records=[r],groups=[dict(excluded_vertical_domains=[])])
    return dict(current_rendered_graph_sha256='a'*64,old={'keep':True}),dict(edges=[e]),p,dict(plan_source='b'*64)

class AdoptionTests(unittest.TestCase):
    def test_old_context_and_source_geometry_immutable(self):
        c,g,p,b=fixture();old=copy.deepcopy((c,g,p,b));new=adopt(c,g,p,b)
        self.assertEqual({k:v for k,v in new.items()if k!='reviewed_uniform_subroute_DN'},c);self.assertEqual((c,g,p,b),old)
        self.assertEqual(new['reviewed_uniform_subroute_DN']['vertical_values_assigned'],0)
    def test_changed_geometry_system_floor_and_length_block(self):
        for kind in ['geometry','system','floor','length','unqualified','duplicate']:
            with self.subTest(kind=kind):
                c,g,p,b=fixture()
                if kind=='geometry':g['edges'][0]['attribute_paths'][0][1][0]=4
                elif kind=='system':g['edges'][0]['system']='supply'
                elif kind=='floor':g['edges'][0]['floor_end']=3
                elif kind=='length':p['records'][0]['physical_length_mm']=0
                elif kind=='unqualified':p['original_native_group_member_gate_and_caption_owners_reexecuted']=False
                else:p['records'].append(copy.deepcopy(p['records'][0]))
                with self.assertRaises(ValueError):adopt(c,g,p,b)
    def test_delta_only_fills_unknown_whole_DN_and_preserves_lengths(self):
        _,_,p,_=fixture();before=[dict(edge_id='A',values=dict(diameter_nominal_mm=None,diameter_text='',diameter_status='unknown',length=7,vertical=300))];after=copy.deepcopy(before)
        after[0]['values'].update(diameter_nominal_mm=200,diameter_text='DN200',diameter_status='native_plan_uniform_lower_subroute_DN',uniform_subroute_DN_scope_id='R',uniform_subroute_DN_domains_json='[]',uniform_subroute_DN_plan_source_sha256='b'*64)
        self.assertEqual(delta(before,after,p['records'])['new_whole_horizontal_DN_edges'],['A'])
        for field,value in [('length',8),('vertical',200)]:
            broken=copy.deepcopy(after);broken[0]['values'][field]=value
            with self.assertRaises(ValueError):delta(before,broken,p['records'])
        before[0]['values']['diameter_nominal_mm']=300
        with self.assertRaises(ValueError):delta(before,after,p['records'])
    def test_mixed_domain_never_gets_whole_DN(self):
        _,_,p,_=fixture();p['records'][0]['whole_horizontal_edge']=False;before=[dict(edge_id='A',values=dict(diameter_nominal_mm=None,length=None))];after=copy.deepcopy(before);after[0]['values'].update(uniform_subroute_DN_scope_id='R',uniform_subroute_DN_domains_json='[]',uniform_subroute_DN_plan_source_sha256='b'*64)
        self.assertEqual(delta(before,after,p['records'])['new_whole_horizontal_DN_edges'],[])
        after[0]['values']['diameter_nominal_mm']=200
        with self.assertRaises(ValueError):delta(before,after,p['records'])

if __name__=='__main__':unittest.main()
