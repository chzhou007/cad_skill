import copy,unittest
from reviewed_uniform_subroute_DN import select

def fixture():
    def edge(e,a,b,path):return dict(edge_id=e,start_node_id=a,end_node_id=b,system='return',floor_start=2,floor_end=2,attribute_paths=[path])
    plan=dict(edges=[edge('P0','A','B',[[0,0],[1000,0]]),edge('P1','B','D',[[1000,0],[2000,0]]),edge('P2','D','Z',[[2000,0],[3000,0]])])
    axis=dict(edges=[edge('HIGH','G','J',[[0,10],[5,10]]),edge('V','J','K',[[5,10],[5,5]]),edge('H','K','L',[[5,5],[10,5]]),edge('V2','L','END',[[10,5],[10,10]])])
    scope=dict(scope_id='RANGE',floor=2,system='return',status='native_bounded_range_correspondence',views=dict(plan=dict(route=dict(edges=['P0','P1','P2'],nodes=['A','B','D','Z'])),iso=dict(route=dict(edges=['HIGH','V','H','V2'],nodes=['G','J','K','L','END']))))
    circle=dict(handle='C',center=[500,0],radius=50);member=dict(scope_id='MEMBER',system='return',floor=2,new_axis_tee='J',source_circle=circle,scoped_graph=dict(nodes=[dict(node_id='MEMBER:gate',source_node_id='A'),dict(node_id='MEMBER:departure',source_node_id='D')],edges=[dict(edge_id='MEMBER:approach',candidate_axis_edge='HIGH',attribute_paths=[[[0,0],[500,0]]],member=dict(nominal_mm=300)),dict(edge_id='MEMBER:departure',attribute_paths=[[[500,0],[1000,0]],[[1000,0],[2000,0]]],member=dict(nominal_mm=200))]))
    interval=dict(axis_edge_id='HIGH',member_scope_id='MEMBER',member_kind='approach',nominal_mm=300,endpoint_evidence=dict(axis_tee='J',plan_circle=copy.deepcopy(circle)),axis_attribute_paths=copy.deepcopy(axis['edges'][0]['attribute_paths']),plan_attribute_paths=[[[0,0],[500,0]]])
    route={e['edge_id']:dict(classification='horizontal_only'if e['edge_id']in['HIGH','H']else'vertical_only',segment_domains=[dict(path_index=0,segment_index=0,direction_class='horizontal'if e['edge_id']in['HIGH','H']else'vertical',scope_points=copy.deepcopy(e['attribute_paths'][0]),native_source_status='single_source_line_covers')])for e in axis['edges']};dn=dict(P2=dict(edge_id='P2',system='return',nominal_mm=200,scope_paths=copy.deepcopy(plan['edges'][2]['attribute_paths']),lineage=[dict(source='native plan')]))
    guard=dict(original_guard_reexecuted=True,original_thresholds_unchanged=True,F_and_other_new_DN_guards_retained=True,source_document_mutated=False)
    return [scope,member,interval,plan,axis,route,dn,guard,[]]

class UniformSubrouteTests(unittest.TestCase):
    def test_uniform_plan_DN_does_not_need_equal_internal_counts_or_assign_verticals_and_lengths(self):
        args=fixture();old=copy.deepcopy(args);r=select(*args);self.assertEqual([x['axis_edge_id']for x in r['records']],['H']);self.assertEqual(r['records'][0]['nominal_mm'],200);self.assertEqual(len(r['excluded_vertical_domains']),2)
        self.assertIsNone(r['records'][0]['physical_length_mm']);self.assertIsNone(r['records'][0]['per_axis_edge_length_allocation']);self.assertFalse(r['records'][0]['internal_node_identities_assigned']);self.assertEqual(args,old)
    def test_conflicting_or_unknown_plan_DN_wrong_member_and_held_source_block(self):
        for kind in ['conflict','unknown','prefix','circle','held','scope','guard']:
            with self.subTest(kind=kind):
                a=fixture()
                if kind in ['conflict','unknown']:a[6]['P2']['nominal_mm']=250 if kind=='conflict'else None
                elif kind=='prefix':a[0]['views']['iso']['route']['edges'][0]='OTHER'
                elif kind=='circle':a[2]['endpoint_evidence']['plan_circle']['handle']='OTHER'
                elif kind=='held':a[0]['status']='held_local_source_evidence'
                elif kind=='scope':a[1]['scoped_graph']['edges'][1]['attribute_paths'][0][0]=[501,0]
                else:a[7]['original_thresholds_unchanged']=False
                with self.assertRaises((ValueError,KeyError)):select(*a)
    def test_system_floor_mixed_path_and_stale_DN_extent_stay_unresolved(self):
        for kind in ['system','floor','mixed','DN_scope']:
            with self.subTest(kind=kind):
                a=fixture()
                if kind=='system':a[4]['edges'][2]['system']='supply'
                elif kind=='floor':a[4]['edges'][2]['floor_end']=3
                elif kind=='mixed':a[5]['H']['classification']='mixed_horizontal_vertical'
                else:a[6]['P2']['scope_paths'][0][1][0]+=1
                with self.assertRaises(ValueError):select(*a)
    def test_mixed_boundary_keeps_horizontal_domain_and_excludes_its_vertical_domain(self):
        a=fixture();edge=a[4]['edges'][1];edge['attribute_paths']=[[[5,10],[5,5],[8,5]]];a[5]['V']=dict(classification='mixed_horizontal_vertical',segment_domains=[dict(path_index=0,segment_index=i,direction_class=d,scope_points=copy.deepcopy(edge['attribute_paths'][0][i:i+2]),native_source_status='single_source_line_covers')for i,d in enumerate(['vertical','horizontal'])]);r=select(*a)
        record=next(x for x in r['records']if x['axis_edge_id']=='V');self.assertFalse(record['whole_horizontal_edge']);self.assertEqual(record['scope_paths'],[[[5,5],[8,5]]]);self.assertEqual(len(r['excluded_vertical_domains']),2)

if __name__=='__main__':unittest.main()
