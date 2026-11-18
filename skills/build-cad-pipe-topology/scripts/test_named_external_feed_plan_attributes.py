import copy,unittest
from test_native_inline_joint_path_coverage import fixture as inline_fixture
from native_inline_joint_path_coverage import collect
from named_external_feed_plan_attributes import build_records,preserve_inheritance,MAPPING_MODE


def fixture():
    args=inline_fixture();graph=args[1];proof=collect(*args)['records'][0];eid=proof['edge_id'];edge=next(e for e in graph['edges'] if e['edge_id']==eid)
    coverage=dict(segments=[dict(index=i,status='no_witness_in_scoped_search' if i in (0,2) else 'single_source_line_covers') for i in range(5)])
    record=dict(mapping_id='M',kind='named_external_port_to_matched_main_T',floor=1,system=edge['system'],identifier='CHWS1',destination='station',plan_edges=[eid],iso_edges=['AXIS'],plan_boundary_node='UT',axis_boundary_node='V',axis_port_id='S1',
        native_plan_inline_path=proof,native_axis_path_coverage=coverage,axis_display_only_segment_index=0,native_axis_confirmed_gap=[dict(gap_segment_index=2)],native_axis_destination=dict(nominal_mm_observed=450),
        external_ports_connected_to_each_other=False,physical_external_connection_verified=False,physical_port_verified=False,physical_length_mm=None,whole_edge_DN_assigned=False,human_accepted=False)
    mapping=dict(mode=MAPPING_MODE,records=[record],local_graphs_mutated=False,physical_values_assigned=0,human_accepted=False,hil_ready=False,source_sha256=dict(plan='S'*64),graph_sha256=dict(plan='G'*64))
    inherited=dict(source_sha256='S'*64,graph_sha256='G'*64,records=[dict(edge_id=eid,system=edge['system'],nominal_mm=450,status='direct_plan_DN',scope_paths=copy.deepcopy(edge['attribute_paths']),human_accepted=False,lineage=[dict(nominal_mm=450)])])
    return graph,mapping,inherited,dict(plan_window=[0,500,0,500])


class Tests(unittest.TestCase):
    def test_pipe_DN_and_XY_exclude_joint_and_display_without_whole_length(self):
        args=fixture();before=copy.deepcopy(args);rows=build_records(*args);self.assertEqual(args,before);r=rows[0]
        self.assertEqual(r['diameter']['nominal_mm'],450);self.assertEqual(r['horizontal_projection']['value_mm'],40)
        self.assertIsNone(r['installed_whole_edge_length_mm']);self.assertIsNone(r['complete_horizontal_centerline_route_mm']);self.assertEqual(r['axis_pipe_segment_indices'],[1,3,4]);self.assertFalse(r['axis_named_DN_used_as_plan_seed'])
    def test_unknown_plan_DN_never_copies_known_axis_name_DN(self):
        args=fixture();args[2]['records'][0].update(nominal_mm=None,status='unresolved',lineage=[]);r=build_records(*args)[0]
        self.assertIsNone(r['diameter']['nominal_mm']);self.assertEqual(r['axis_named_DN_observation_mm'],450);self.assertEqual(r['axis_DN_consistency'],'plan_unknown')
    def test_old_known_and_conflicting_main_values_and_observations_are_protected(self):
        seeds=[dict(evidence_id='source:DN',edge_id='MAIN',nominal_mm=200)];old=dict(direct_observations=seeds,records=[dict(plan_edges=['MAIN'],diameter=dict(system='supply',nominal_mm=200,status='direct_plan_DN')),dict(plan_edges=['OTHER'],diameter=dict(system='supply',nominal_mm=None,status='conflict'))])
        inherited=dict(records=[dict(edge_id='MAIN',system='supply',nominal_mm=200,status='direct_plan_DN'),dict(edge_id='OTHER',system='supply',nominal_mm=None,status='conflict')])
        self.assertEqual(len(preserve_inheritance(old,seeds,inherited,{'FEED'})),2)
        for case in ('seed','value','conflict'):
            obs=copy.deepcopy(seeds);now=copy.deepcopy(inherited)
            if case=='seed':obs[0]['nominal_mm']=450
            elif case=='value':now['records'][0]['nominal_mm']=450
            else:now['records'][1].update(nominal_mm=450,status='T_inherited_plan_DN')
            with self.subTest(case=case),self.assertRaises(ValueError):preserve_inheritance(old,obs,now,{'FEED'})
    def test_wrong_scope_duplicate_edge_or_physical_claim_fails(self):
        for case in ('scope','source','DN','status','physical','gap','duplicate'):
            args=list(fixture());row=args[1]['records'][0];dn=args[2]['records'][0]
            if case=='scope':dn['scope_paths']=[]
            elif case=='source':args[2]['graph_sha256']='stale'
            elif case=='DN':dn['nominal_mm']=0
            elif case=='status':dn['status']='conflict'
            elif case=='physical':row['physical_external_connection_verified']=True
            elif case=='gap':row['native_axis_path_coverage']['segments'][1]['status']='no_witness_in_scoped_search'
            else:args[1]['records'].append(copy.deepcopy(row))
            with self.subTest(case=case),self.assertRaises(ValueError):build_records(*args)

if __name__=='__main__':unittest.main()
