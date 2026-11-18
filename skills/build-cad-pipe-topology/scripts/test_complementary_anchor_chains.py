import copy,unittest
from complementary_anchor_chains import discover,regions,inherit,MODE

def graph(prefix,intervals=3):
    ns=[dict(node_id=prefix+str(i),node_type='tee',floor=3,x=i,y=0)for i in range(intervals+1)]
    es=[dict(edge_id=prefix+'e'+str(i),start_node_id=prefix+str(i),end_node_id=prefix+str(i+1),system='supply')for i in range(intervals)]
    es.append(dict(edge_id=prefix+'bypass',start_node_id=prefix+'0',end_node_id=prefix+str(intervals),system='supply'))
    for i in range(intervals+1):
        ns.append(dict(node_id=prefix+'v'+str(i),node_type='virtual_equipment',floor=3,x=i,y=1))
        es.append(dict(edge_id=prefix+'arm'+str(i),start_node_id=prefix+str(i),end_node_id=prefix+'v'+str(i),system='supply'))
    return dict(nodes=ns,edges=es)

def provider():
    rows=[dict(edge_id='Ae'+str(i),floor=3,classification='horizontal_only',has_existing_correspondence=False,correspondence_observations=[])for i in range(3)]
    rows.append(dict(edge_id='Abypass',floor=3,classification='horizontal_only',has_existing_correspondence=True,correspondence_observations=[dict(domain='ordinary_local_graph',provider='old',mapping_id='OLD',floor=3,plan_edges=['Pbypass'],grouped_axis_edges=['Abypass'])]))
    rem=[dict(edge_id='Ae'+str(i),floor=3,next_scope='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path',complete_centerline=False,known_whole_DN=None)for i in range(3)]
    return dict(ordinary_junction_mappings={'3':{'P0':'A0','P3':'A3'}},records=rows,member_domain_observations=[dict(mapping_id='MEMBER-OLD')],current_component_inventory=dict(keep=True),remaining_horizontal_attributes=rem,counts=dict(member_domain_observations=0),current_horizontal_frontier=dict(pure_horizontal_complete=1,records=copy.deepcopy(rem)))

class Chains(unittest.TestCase):
    def test_keeps_known_cycle_and_pairs_only_unique_unknown_region(self):
        p,a=graph('P'),graph('A');before=copy.deepcopy((p,a));good,held=discover(dict(plan=p,iso=a),provider(),3)
        self.assertEqual(len(good),1);self.assertFalse(held);self.assertEqual(good[0]['plan']['edges'],['Pe0','Pe1','Pe2'])
        self.assertIn('Pbypass',good[0]['plan']['complete_region_edges']);self.assertEqual((p,a),before)

    def test_does_not_pair_different_branch_counts(self):
        p=provider();p['ordinary_junction_mappings']['3']['P3']='A4'
        p['records'][-1]['correspondence_observations'][0]['grouped_axis_edges']=['Abypass']
        good,held=discover(dict(plan=graph('P'),iso=graph('A',4)),p,3)
        self.assertFalse(good);self.assertEqual(held[0]['reason'],'unknown_native_chain_branch_counts_differ')

    def test_existing_axis_writer_and_missing_bypass_do_not_pass(self):
        p=provider();p['records'][1]['has_existing_correspondence']=True
        self.assertEqual(discover(dict(plan=graph('P'),iso=graph('A')),p,3)[1][0]['reason'],'old_axis_provider_present')
        p=provider();p['records'][-1]['correspondence_observations']=[]
        self.assertFalse(discover(dict(plan=graph('P'),iso=graph('A')),p,3)[0])

    def test_reviewed_or_wrong_system_T_interrupts_region(self):
        for mutation in('review','system'):
            a=graph('A')
            if mutation=='review':a['nodes'][1]['review_required']=True
            else:a['edges'][0]['system']='return'
            self.assertFalse(discover(dict(plan=graph('P'),iso=a),provider(),3)[0])

    def test_prior_plan_writer_and_member_identity_are_protected(self):
        p=provider();p['records'][-1]['correspondence_observations'].append(dict(domain='named_plan_horizontal_segment',provider='old-detail',mapping_id='DETAIL',floor=3,plan_edges=['Pe1']))
        self.assertEqual(discover(dict(plan=graph('P'),iso=graph('A')),p,3)[1][0]['reason'],'old_plan_scope_writer_present')
        p=provider();p['ordinary_junction_mappings']['3']['MEMBER:P']='MEMBER:A'
        with self.assertRaisesRegex(ValueError,'member identity'):discover(dict(plan=graph('P'),iso=graph('A')),p,3)

    def test_inheritance_retains_old_provider_values_members_and_detail_hold(self):
        old=provider();before=copy.deepcopy(old);records=[]
        for i in range(3):
            records.append(dict(axis_edge_id='Ae'+str(i),mapping_id='NEW'+str(i),floor=3,plan_edges=['Pe'+str(i)],iso_edges=['Ae'+str(i)],ordinary_endpoint_pairs=[['P'+str(i),'A'+str(i)],['P'+str(i+1),'A'+str(i+1)]],source_detail_difference=True,attribute_adoption_allowed=False,physical_values_assigned=0,off_chain_terminal_identity_assigned=False))
        new=inherit(old,records);self.assertEqual(old,before);self.assertEqual(new['mode'],MODE)
        self.assertEqual(new['records'][-1],old['records'][-1]);self.assertEqual(new['member_domain_observations'],old['member_domain_observations'])
        self.assertEqual(new['counts']['member_domain_observations'],1);self.assertEqual(new['counts']['existing_correspondence_edges'],4)
        self.assertEqual(new['current_horizontal_frontier']['pure_horizontal_complete'],1)
        self.assertTrue(all(r['next_scope']=='known_complementary_chain_native_detail_difference'for r in new['remaining_horizontal_attributes']))
        with self.assertRaisesRegex(ValueError,'competes with an old provider'):inherit(new,records)

if __name__=='__main__':unittest.main()
