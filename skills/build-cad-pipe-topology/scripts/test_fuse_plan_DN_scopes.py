import copy,unittest
from fuse_plan_DN_scopes import apply


class PlanDNScopeFusionTests(unittest.TestCase):
    def fixture(self):
        nodes=[dict(node_id=n,node_type='tee',floor=1,review_required=False) for n in ('A','B')]
        edge=dict(edge_id='I',start_node_id='A',end_node_id='B',system='supply',floor_start=1,floor_end=1,attribute_paths=[[[0,0],[20,20]]])
        record=dict(mapping_id='G01-SC1',kind='main_between_equipment_branches',iso_edges=['I'],plan_edges=['P'],floor=1,system='supply')
        attr=dict(mapping_id=record['mapping_id'],plan_edges=['P'],iso_edges=['I'],system='supply',human_accepted=False,diameter=dict(nominal_mm=None,plan_candidate={'text':'old'}),horizontal_projection=dict(edge_value_mm=1500),whole_edge_physical_length_mm=None)
        edge['cross_view_attributes']=attr
        axis=dict(nodes=nodes,edges=[edge],sourceCheckedCrossViewAttributeFusion={})
        pe=dict(edge,edge_id='P',attribute_paths=[[[100,100],[1600,100]]]);pe.pop('cross_view_attributes')
        plan=dict(nodes=copy.deepcopy(nodes),edges=[pe])
        row=dict(edge_id='P',system='supply',scope_paths=copy.deepcopy(pe['attribute_paths']),scope='native_plan_drawn_pipe_paths_only',human_accepted=False,nominal_mm=80,lineage=[{'evidence':'native-T'}])
        return axis,dict(records=[record]),plan,dict(records=[row])

    def run_case(self,inputs,angles=(0,45,135)):
        return apply(*inputs,'a'*64,angles)

    def test_complete_horizontal_main_uses_plan_dn_and_route_length_not_cut_length(self):
        inputs=self.fixture();before=copy.deepcopy(inputs);out,proof=self.run_case(inputs)
        self.assertEqual(inputs,before)
        a=out['edges'][0]['cross_view_attributes'];self.assertEqual(a['diameter']['nominal_mm'],80)
        self.assertEqual(a['whole_edge_physical_length_mm'],1500);self.assertIsNone(a['pipe_net_cut_length_mm'])
        self.assertEqual(a['whole_edge_length_kind'],'floor_plan_horizontal_main_centerline_route')
        self.assertEqual(a['diameter']['plan_candidate'],{'text':'old'});self.assertFalse(a['human_accepted']);self.assertTrue(proof[0]['whole_main_DN_and_centerline_route'])

    def test_plan_floor_schema_alias_is_checked_and_conflicting_aliases_fail_closed(self):
        x=self.fixture();e=x[2]['edges'][0];e['start_floor']=e.pop('floor_start');e['end_floor']=e.pop('floor_end')
        out,_=self.run_case(x);self.assertEqual(out['edges'][0]['cross_view_attributes']['diameter']['nominal_mm'],80)
        e['floor_start']=2
        out,_=self.run_case(x);self.assertIsNone(out['edges'][0]['cross_view_attributes']['diameter']['nominal_mm'])

    def test_branch_and_unproved_extents_keep_only_drawn_plan_dn(self):
        for variant in ('branch','no_horizontal_axes','vertical','floor','review','nontee','split','system','bent'):
            x=self.fixture();axis,mapping,plan,_=x;angles=(0,45,135)
            if variant=='branch':mapping['records'][0]['kind']='equipment_branch'
            elif variant=='no_horizontal_axes':angles=()
            elif variant=='vertical':axis['edges'][0]['attribute_paths']=[[[0,0],[0,20]]]
            elif variant=='floor':plan['edges'][0]['floor_end']=2
            elif variant=='review':plan['nodes'][0]['review_required']=True
            elif variant=='nontee':axis['nodes'][0]['node_type']='interface'
            elif variant=='split':axis['edges'][0]['attribute_paths']=[[[0,0],[5,5]],[[10,10],[20,20]]]
            elif variant=='system':axis['edges'][0]['system']='return'
            else:axis['edges'][0]['attribute_paths']=[[[0,0],[10,10],[20,20]]]
            out,_=self.run_case(x,angles);a=out['edges'][0]['cross_view_attributes']
            self.assertEqual(a['diameter']['plan_drawn_nominal_mm'],80,variant);self.assertIsNone(a['diameter']['nominal_mm'],variant);self.assertIsNone(a['whole_edge_physical_length_mm'],variant)

    def test_source_scopes_and_correspondence_cannot_drift(self):
        for variant in ('hash','path','scope','system','accepted','mapping','missing','duplicate','zero','bool','nonfinite','negative','axes'):
            x=self.fixture();axis,mapping,plan,e=x;row=e['records'][0];hash_value='a'*64;angles=(45,)
            if variant=='hash':hash_value='unbound'
            elif variant=='path':row['scope_paths']=[[[0,0],[1,0]]]
            elif variant=='scope':row['scope']='whole_installed_pipe'
            elif variant=='system':row['system']='return'
            elif variant=='accepted':row['human_accepted']=True
            elif variant=='mapping':axis['edges'][0]['cross_view_attributes']['iso_edges']=['OTHER']
            elif variant=='missing':e['records']=[]
            elif variant=='duplicate':e['records'].append(copy.deepcopy(row))
            elif variant=='zero':row['nominal_mm']=0
            elif variant=='bool':row['nominal_mm']=True
            elif variant=='nonfinite':row['nominal_mm']=float('nan')
            elif variant=='negative':row['nominal_mm']=-1
            else:angles=(90,)
            with self.assertRaises(ValueError,msg=variant):apply(*x,hash_value,angles)

    def test_unknown_dn_is_retained_and_many_to_one_does_not_invent_allocation(self):
        x=self.fixture();x[3]['records'][0]['nominal_mm']=None
        out,_=self.run_case(x);self.assertIsNone(out['edges'][0]['cross_view_attributes']['diameter']['nominal_mm'])
        x=self.fixture();x[1]['records'][0]['iso_edges'].append('I2')
        e=copy.deepcopy(x[0]['edges'][0]);e['edge_id']='I2';x[0]['edges'].append(e)
        for edge in x[0]['edges']:edge['cross_view_attributes']['iso_edges']=['I','I2'];edge['cross_view_attributes']['horizontal_projection']['edge_value_mm']=None
        out,_=self.run_case(x)
        self.assertTrue(all(e['cross_view_attributes']['whole_edge_physical_length_mm'] is None for e in out['edges']))


if __name__=='__main__':unittest.main()
