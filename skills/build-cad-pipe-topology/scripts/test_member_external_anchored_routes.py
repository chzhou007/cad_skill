import copy,unittest
from member_external_anchored_routes import station,clipped_fragments,omission_evidence,outward_candidates,discover,scoped_components,ordered_components
from rebuild_member_external_routes import inherit

class Tests(unittest.TestCase):
    def fixture(self):
        node=lambda n,x,y:dict(node_id=n,node_type='tee',floor=3,x=x,y=y)
        edge=lambda e,a,b,points:dict(edge_id=e,start_node_id=a,end_node_id=b,system='return',attribute_paths=[points],path_points=points,source_handles=['L'])
        plan=dict(nodes=[node('P',0,0),node('Q',6,0),node('Z',0,5),node('U',0,-5)],edges=[edge('carrier','P','Q',[[0,0],[6,0]]),edge('pz','P','Z',[[0,0],[0,5]]),edge('pu','P','U',[[0,0],[0,-5]])])
        axis=dict(nodes=[node('A',20,0),node('M',25,0),node('AZ',20,5),node('AU',20,-5)],edges=[edge('external','M','A',[[25,0],[20,0]]),edge('az','A','AZ',[[20,0],[20,5]]),edge('au','A','AU',[[20,0],[20,-5]])])
        port=dict(member_node_id='MEMBER:C1',axis_node_id='M',other_axis_node='A',axis_edge_id='external',system='return')
        nodes=[dict(node('MEMBER:C1',5,0),member_scope_id='UPPER'),dict(node('MEMBER:C2',8,0),member_scope_id='UPPER')]
        parent=dict(records=[],original_external_ports=[port],member_local_graph=dict(nodes=nodes,edges=[],external_ports=[port],global_topology_complete=False))
        interfaces=dict(groups=[dict(plan_LINE='L',primary_member_scope_id='UPPER',interfaces=[dict(member_primary_node_id='MEMBER:C1',axis_primary_T='M',plan_circle=dict(point=[5,0])),dict(member_primary_node_id='MEMBER:C2',axis_primary_T='M2',plan_circle=dict(point=[8,0]))])])
        provider=dict(ordinary_junction_mappings={'3':{'Z':'AZ'}},records=[dict(edge_id='external',classification='mixed_horizontal_vertical',has_existing_correspondence=False,correspondence_observations=[]),dict(edge_id='az',classification='horizontal_only',has_existing_correspondence=False,correspondence_observations=[])],remaining_horizontal_attributes=[dict(edge_id='az',next_scope='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path')],current_horizontal_frontier={},member_domain_observations=[],current_component_inventory={'count':42},counts={})
        return plan,axis,parent,interfaces,provider

    def test_two_independent_endpoint_scopes_discover_without_DN_or_distance(self):
        plan,axis,parent,interfaces,provider=self.fixture();before=copy.deepcopy((plan,axis,parent,interfaces,provider))
        rows,held=discover(plan,axis,parent,interfaces,provider,3)
        self.assertEqual(len(rows),1);self.assertFalse(held);self.assertEqual(rows[0]['plan_remote'],'P');self.assertEqual(rows[0]['independent_adjacent_anchors'][0]['axis_edge_id'],'az')
        self.assertEqual(rows[0]['attribute_paths'],[[[5.,0.],[0.,0.]]]);self.assertEqual((plan,axis,parent,interfaces,provider),before)
        provider['ordinary_junction_mappings']['3']['P']='A'
        self.assertTrue(discover(plan,axis,parent,interfaces,provider,3)[0][0]['direct_existing_ordinary_anchor'])

    def test_source_boundary_remote_anchor_and_old_writer_are_not_promoted(self):
        for change,reason in [('boundary','remote_source_endpoint_is_not_a_proved_T'),('anchor','existing_remote_anchor_conflicts'),('old','external_member_edge_already_mapped'),('floor','remote_T_floor_system_or_degree_not_qualified')]:
            plan,axis,parent,interfaces,provider=self.fixture()
            if change=='boundary':plan['nodes'][0]['node_type']='virtual_equipment'
            if change=='anchor':provider['ordinary_junction_mappings']['3']['P']='OTHER'
            if change=='old':provider['records'][0]['has_existing_correspondence']=True
            if change=='floor':plan['nodes'][0]['floor']=2
            rows,held=discover(plan,axis,parent,interfaces,provider,3)
            self.assertFalse(rows);self.assertEqual(held[0]['reason'],reason)

    def test_bridged_ports_not_rediscovered_and_no_nearest_member_merge(self):
        plan,axis,parent,interfaces,provider=self.fixture();parent['records']=[dict(axis_edge_id='external')]
        self.assertEqual(discover(plan,axis,parent,interfaces,provider,3),([],[]))
        parent['records']=[];plan['edges'][0]['source_handles']=['UNRELATED_AT_SAME_XY']
        self.assertFalse(outward_candidates(plan,parent,interfaces,parent['original_external_ports'][0]))

    def test_gaps_remain_unknown_and_require_exact_prior_continuity_evidence(self):
        edge=dict(attribute_paths=[[[0,0],[0,3]],[[0,4],[5,4]]]);logical=[[5,4],[0,4],[0,0]]
        paths,gaps=clipped_fragments(edge,logical)
        self.assertEqual(paths,[[[5.,4.],[0.,4.]],[[0.,3.],[0.,0.]]]);self.assertEqual(gaps,[[[0.,4.],[0.,3.]]])
        with self.assertRaises(ValueError):omission_evidence(edge,gaps,'return')
        evidence=dict(rule_scope='explicit_project_known_issue_only',source_endpoints=[[0,3],[0,4]],physical_length='unknown')
        edge['source_drafting_erratum']=evidence
        result=omission_evidence(edge,gaps,'return');self.assertEqual(result[0]['evidence']['physical_length'],'unknown')
        evidence['source_endpoints']=[[0,3],[0,4.2]]
        with self.assertRaises(ValueError):omission_evidence(edge,gaps,'return')

    def test_retraced_station_and_duplicate_fragments_rejected(self):
        with self.assertRaises(ValueError):station([2,0],[[0,0],[5,0],[0,0]])
        with self.assertRaises(ValueError):clipped_fragments(dict(attribute_paths=[[[0,0],[5,0]],[[0,0],[5,0]]]),[[0,0],[5,0]])

    def test_component_cut_is_not_silently_excluded(self):
        row=dict(edge_id='carrier',native_contact=dict(flange_contacts=[dict(point_WCS=[4,0,0]),dict(point_WCS=[6,0,0])]))
        with self.assertRaises(ValueError):scoped_components(dict(records=[row]),[[[0,0],[5,0]]],'carrier')

    def test_ordered_signature_mismatch_blocks_even_when_counts_match(self):
        def scope(handle,signature):return dict(selected=[dict(source_handle=handle,edge_id='E',geometry=dict(signature=signature),native_contact=dict(flange_contacts=[dict(point_WCS=[1,0,0]),dict(point_WCS=[2,0,0])]))])
        with self.assertRaises(ValueError):ordered_components(dict(plan=scope('P','BALL'),axis=scope('A','OTHER')),dict(plan=[[0,0],[3,0]],axis=[[0,0],[3,0]]))

    def test_inherit_separates_member_namespace_and_preserves_old_values(self):
        plan,axis,parent,interfaces,provider=self.fixture();old=copy.deepcopy(provider)
        common=dict(floor=3,system='return',physical_values_assigned=0,attribute_adoption_allowed=False,human_accepted=False)
        external=dict(common,mapping_id='X',kind='member_to_ordinary_external_route',axis_edge_id='external',plan_member_edge_id='MEMBER-EXTERNAL:X',plan_source_edge_id='carrier',member_node_id='MEMBER:C1',plan_remote='P',axis_remote='A',plan_attribute_paths=[[[5,0],[0,0]]])
        ordinary=dict(common,mapping_id='Y',kind='ordinary_anchored_neighbor',axis_edge_id='az',plan_edge_id='pz',ordinary_endpoint_pairs=[['P','A'],['Z','AZ']])
        result,local=inherit(provider,[external,ordinary],parent,plan)
        self.assertEqual(provider,old);self.assertEqual(result['counts']['existing_correspondence_edges'],2);self.assertEqual(result['DN_or_length_values_assigned'],0)
        self.assertEqual(result['current_component_inventory'],old['current_component_inventory']);self.assertNotIn('MEMBER:C1',result['ordinary_junction_mappings']['3'])
        self.assertEqual(local['edges'][0]['installed_whole_length_mm'],None);self.assertEqual(local['external_ports'],[])
        self.assertEqual(local['nodes'][:2],parent['member_local_graph']['nodes'])
        external['physical_values_assigned']=1
        with self.assertRaises(ValueError):inherit(provider,[external],parent,plan)

if __name__=='__main__':unittest.main()
