import copy,unittest
from test_reapply_capped_branch_correspondence import fixture as cap_fixture
from reapply_nonnode_boundary_branches import discover

def fixture():
    p,g,_,_=cap_fixture();plan=g['plan'];e=plan['edges'][-1];e['end_node_id']=None;e['end_boundary_id']='B'
    plan['nodes']=[n for n in plan['nodes']if n['node_id']!='U'];e['source_handles']=['PIPE']
    plan['boundary_anchors']=[dict(boundary_id='B',kind='expert_non_node_source_boundary',source_marker_kind='two_bar',expert_issue='EXPERT',system='supply',source_pipe_handle='PIPE')]
    return p,plan,g['iso'],3

class NonNodeBoundaryTests(unittest.TestCase):
    def test_existing_non_node_role_kept_and_two_main_arms_select_branch(self):
        args=fixture();before=copy.deepcopy(args);rows,held,known=discover(*args)
        self.assertEqual(args,before);self.assertEqual((len(rows),len(held),len(known)),(1,0,0));self.assertEqual(rows[0]['boundary_id'],'B');self.assertIsNone(args[1]['edges'][-1]['end_node_id']);self.assertNotIn('B',{n['node_id']for n in args[1]['nodes']})
    def test_existing_writer_is_not_replaced(self):
        p,g,a,f=fixture();p['records'][-1]['has_existing_correspondence']=True
        rows,held,known=discover(p,g,a,f);self.assertEqual((rows,held),([],[]));self.assertEqual(len(known),1)
    def test_missing_or_competing_boundary_owner_fails_before_matching(self):
        for variant in ('missing','duplicate'):
            p,g,a,f=fixture()
            if variant=='missing':g['boundary_anchors']=[]
            else:g['edges'].append(dict(g['edges'][-1],edge_id='DUPLICATE'))
            with self.subTest(variant=variant),self.assertRaisesRegex(ValueError,'missing or competing'):discover(p,g,a,f)
    def test_boundary_cannot_be_silently_promoted_to_node(self):
        p,g,a,f=fixture();g['edges'][-1]['end_node_id']='FAKE';g['nodes'].append(dict(node_id='FAKE',node_type='virtual_equipment',floor=3,system='supply'))
        rows,held,_=discover(p,g,a,f);self.assertEqual(rows,[]);self.assertIn('explicit non-node',held[0]['reason'])
    def test_unknown_boundary_family_retained_as_specific_pending(self):
        p,g,a,f=fixture();g['boundary_anchors'][0]['source_marker_kind']='unknown'
        rows,held,_=discover(p,g,a,f);self.assertEqual(rows,[]);self.assertIn('another family',held[0]['reason'])
    def test_source_system_and_main_independence_required(self):
        for variant in ('system','main'):
            p,g,a,f=fixture()
            if variant=='system':g['boundary_anchors'][0]['system']='return'
            else:p['records'][1]['correspondence_observations']=[]
            self.assertEqual(discover(p,g,a,f)[0],[])
    def test_no_ordinary_anchor_is_specific_pending(self):
        p,g,a,f=fixture();p['ordinary_junction_mappings']['3']={}
        rows,held,_=discover(p,g,a,f);self.assertEqual(rows,[]);self.assertIn('ordinary T',held[0]['reason'])

if __name__=='__main__':unittest.main()
