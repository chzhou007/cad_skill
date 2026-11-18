import copy,unittest
from test_match_named_riser_floor_segments import fixture as upper_fixture
from crossview_equipment_branch_inventory import service_route
from match_named_riser_lower_floor_segments import correspond,implementation_hashes


def fixture():
    args=upper_fixture();docs,graphs,inventory,named,riser,touching,removed,policy,hashes=args
    for line in docs['iso'].modelspace().query('LINE'):
        a,b=line.dxf.start,line.dxf.end;line.dxf.start=(a.x,80-a.y,a.z);line.dxf.end=(b.x,80-b.y,b.z)
    for view,graph in graphs.items():
        for node in graph['nodes']:
            node['floor']=2 if view=='iso' and node['node_id'].endswith('M') else 1
            if view=='iso':node['y']=80-node['y']
        if view=='iso':
            for edge in graph['edges']:
                edge['attribute_paths']=[[[x,80-y] for x,y in path] for path in edge['attribute_paths']]
                if edge['edge_id'].endswith('MIX'):
                    edge['start_node_id'],edge['end_node_id']=edge['end_node_id'],edge['start_node_id']
                    edge['attribute_paths'][0].reverse()
    for row in named['plan']['records']:row['target']['floor']=1
    for contract,name in zip(riser['through_contracts'],named['iso']['records']):
        segment=contract['segments'][0];system=contract['system'];identifier=name['identifier'];handle=segment['source_line_handle']
        contract.update(corridor_id=identifier,through_source_LINE=handle)
        edge=next(e for e in graphs['iso']['edges'] if e['edge_id']==segment['edge_id']);points=edge['attribute_paths'][0]
        segment.update(side='lower',segment_index=1,floor_pair=[1,2],scope_points=copy.deepcopy(points[1:]))
        name.update(target_kind='axis_source_line',target=dict(source_line_handle=handle))
    owner=inventory['records'][0];owner['floor']=1
    for view in graphs:
        for system in ('supply','return'):owner['views'][view]['services'][system]['trace']=service_route(graphs[view],'D',system)
    policy['floor']=1
    return docs,graphs,inventory,named,riser,policy,hashes


class Tests(unittest.TestCase):
    def test_native_names_columns_and_device_services_match_only_lower_prefix(self):
        args=fixture();before=copy.deepcopy(args[1]);result=correspond(*args)
        self.assertEqual(args[1],before);self.assertEqual(len(result['records']),4);self.assertEqual(len(result['floor_interface_correspondences']),2)
        for row in result['records']:
            scope=row['iso_segment_scopes'][0]
            if row['kind'].endswith('approach'):
                self.assertEqual(scope['segment_indices'],[0]);self.assertFalse(scope['whole_local_edge'])
            self.assertFalse(row['whole_axis_DN_assigned']);self.assertIsNone(row['physical_length_mm'])
        self.assertEqual(result['DN_values_assigned'],0);self.assertEqual(result['physical_lengths_assigned'],0)
    def test_wrong_names_column_system_floor_ready_state_or_vertical_domain_block(self):
        for case in ('name','repeat','column','system','floor','unready','vertical','middle','prefix','bridge','tee'):
            args=list(fixture());docs,graphs,inventory,named,riser,policy,hashes=args
            mixed=next(e for e in graphs['iso']['edges'] if e['edge_id']=='supplyMIX')
            if case=='name':named['iso']['records'][0]['identifier']='CHWS2'
            elif case=='repeat':named['iso']['records'].append(copy.deepcopy(named['iso']['records'][0]))
            elif case=='column':named['iso']['records'][0]['target']['source_line_handle']='wrong-native-column'
            elif case=='system':named['iso']['records'][0]['system']='return'
            elif case=='floor':policy['floor']=2
            elif case=='unready':inventory['records'][0]['ready_for_mapping_comparison']=False
            elif case=='vertical':riser['through_contracts'][0]['segments'][0]['side']='upper'
            elif case=='middle':riser['through_contracts'][0]['middle_T']='other'
            elif case=='prefix':mixed['attribute_paths'][0][0][0]=mixed['attribute_paths'][0][1][0]
            elif case=='bridge':policy['services'][0]['axis_bridge_edge']='supplyLOW'
            else:next(n for n in graphs['iso']['nodes'] if n['node_id']=='supplyN')['node_type']='endpoint'
            with self.subTest(case=case),self.assertRaises(ValueError):correspond(*args)
    def test_real_plan_gap_does_not_become_exact_touching_source_path(self):
        args=fixture();edge=next(e for e in args[1]['plan']['edges'] if e['edge_id']=='supplyBRIDGE')
        edge['attribute_paths'][1][0][0]+=.001
        with self.assertRaises(ValueError):correspond(*args)
    def test_dependency_closure_inherits_source_T_XYZ_naming_and_riser_rules(self):
        for name in ('match_named_riser_floor_segments.py','native_axis_riser_DN_scopes.py','native_named_riser_evidence.py','native_touching_plan_path_chunks.py'):
            self.assertIn(name,implementation_hashes())


if __name__=='__main__':unittest.main()
