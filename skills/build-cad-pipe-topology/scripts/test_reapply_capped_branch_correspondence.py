import copy,unittest
from reapply_capped_branch_correspondence import candidates,main_support

def fixture():
    def graph(anchor,leaf,prefix):
        nodes=[dict(node_id=n,node_type='tee'if n==anchor else'virtual_equipment',floor=3,system='supply')for n in [anchor,leaf,'X','Y']]
        edges=[dict(edge_id=prefix+s,start_node_id=anchor,end_node_id=t,system='supply')for s,t in [('1','X'),('2','Y'),('B',leaf)]]
        return dict(nodes=nodes,edges=edges)
    graphs=dict(plan=graph('P','U','P'),iso=graph('A','V','A'))
    records=[dict(edge_id='A'+s,has_existing_correspondence=s!='B',correspondence_observations=[]if s=='B'else[dict(domain='ordinary_local_graph',floor=3,grouped_axis_edges=['A'+s],plan_edges=['P'+s],mapping_id='MAIN'+s)])for s in ['1','2','B']]
    provider=dict(records=records,ordinary_junction_mappings={'3':{'P':'A'}})
    cap=dict(node_id='U',edge_id='PB',system='supply',qualifier={'text':'盲板封堵'},caption={'declared_group_quantity':2})
    groups=[dict(qualifier_text='盲板封堵',declared_quantity=2,members=[dict(node_id='V',edge_id='AB',port_id='V-S',system='supply',floor=3)])]
    return provider,graphs,[cap],groups

class CappedCorrespondenceTests(unittest.TestCase):
    def test_independent_T_and_same_system_cap_select_one_drawing_scope(self):
        args=fixture();before=copy.deepcopy(args);rows,pending=candidates(*args)
        self.assertEqual(args,before);self.assertEqual(pending,[]);self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['plan_edge_id'],rows[0]['axis_edge_id']),('PB','AB'));self.assertEqual(len(rows[0]['main_correspondence_evidence']),2)
    def test_equal_caption_or_quantity_alone_does_not_match(self):
        p,g,c,a=fixture();p['ordinary_junction_mappings']['3']['P']='OTHER'
        self.assertEqual(candidates(p,g,c,a)[0],[])
    def test_other_system_port_not_transferred(self):
        p,g,c,a=fixture();a[0]['members'][0]['system']='return'
        self.assertEqual(candidates(p,g,c,a)[0],[])
    def test_floor_and_declared_quantity_both_constrain_scope(self):
        for field,value in [('floor',2),('quantity',4)]:
            p,g,c,a=fixture()
            if field=='floor':a[0]['members'][0]['floor']=value
            else:a[0]['declared_quantity']=value
            self.assertEqual(candidates(p,g,c,a)[0],[])
    def test_two_independent_main_arms_required(self):
        p,g,c,a=fixture();p['records'][1]['correspondence_observations'][0]['plan_edges']=['P1']
        self.assertEqual(candidates(p,g,c,a)[0],[])
    def test_grouped_or_ambiguous_main_is_not_single_arm_proof(self):
        for change in ['grouped','duplicate']:
            p,g,c,a=fixture();obs=p['records'][0]['correspondence_observations']
            if change=='grouped':obs[0]['grouped_axis_edges']=['A1','A2']
            else:obs.append(copy.deepcopy(obs[0]))
            self.assertEqual(candidates(p,g,c,a)[0],[])
    def test_old_branch_writer_is_not_replaced(self):
        p,g,c,a=fixture();p['records'][-1]['has_existing_correspondence']=True
        rows,held=candidates(p,g,c,a);self.assertEqual(rows,[]);self.assertIn('existing branch provider',held[0]['reason'])
    def test_multiple_marker_groups_do_not_get_first_match(self):
        p,g,c,a=fixture();a.append(copy.deepcopy(a[0]));self.assertEqual(candidates(p,g,c,a)[0],[])
    def test_duplicate_plan_claim_is_rejected(self):
        p,g,c,a=fixture();c.append(copy.deepcopy(c[0]))
        with self.assertRaisesRegex(ValueError,'competing'):candidates(p,g,c,a)

if __name__=='__main__':unittest.main()
