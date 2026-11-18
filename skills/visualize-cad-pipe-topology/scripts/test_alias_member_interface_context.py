import copy,unittest
from alias_member_interface_context import collect,SOURCE_MODE

def fixture(mixed=False):
    h={k:c*64 for k,c in zip(('axis_graph','rendered_graph','native_proof','plan_graph','axis_local_graph','plan_source','axis_source'),'abcdefg')}
    path=[[0,0],[10,0]]+([[10,20]]if mixed else[])
    edge=dict(edge_id='E',start_node_id='A',end_node_id='B',system='supply',floor_start=2,floor_end=2,attribute_paths=[path]);raw=dict(edges=[edge]);rendered=copy.deepcopy(raw)
    spans=[dict(path_index=0,segment_index=i,scope_points=[a,b],direction_class='horizontal'if i==0 else'vertical',source_line_coverage_checked=True,DN_source_route='corresponding_floor_plan_horizontal'if i==0 else'axis_11_native_vertical',length_source_route='corresponding_floor_plan_horizontal'if i==0 else'axis_11_native_vertical')for i,(a,b)in enumerate(zip(path,path[1:]))]
    domains=dict(records=spans,horizontal_nominal_mm=200,horizontal_complete_centerline_mm=800,whole_edge_nominal_mm=None if mixed else 200,whole_edge_complete_centerline_mm=None if mixed else 800)
    row=dict(mapping_id='M',axis_edge_id='E',kind='lower_member_approach_with_local_rise'if mixed else'primary_member_main',floor=2,system='supply',nominal_mm=200,source_alias_group_id='G',original_plan_graph_sha256=h['plan_graph'],reading_projection_sha256='1'*64,plan_LINE='P',plan_member_edge_id='MEMBER:P',member_scope_id='MEMBER:S',literal_level_key='3',axis_nodes=['A','B'],axis_attribute_paths=[path],plan_attribute_paths=[[[0,0],[800,0]]],plan_projection=dict(value_mm=800),attribute_source_domains=domains)
    p=dict(mode=SOURCE_MODE,original_local_graphs_mutated=False,ordinary_junction_mapping_extended=False,vertical_attributes_assigned_from_plan=0,human_accepted=False,pending=[],inputs={k:dict(sha256=v,path='09-中文.dxf')for k,v in [('raw_axis_graph',h['axis_graph']),('plan_graph',h['plan_graph']),('axis_graph',h['axis_local_graph']),('plan_source',h['plan_source']),('axis_source',h['axis_source'])]},records=[row]);prior=dict(source_graph_sha256=h['axis_graph'],rendered_graph_sha256=h['rendered_graph']);return raw,rendered,p,h,prior

class Tests(unittest.TestCase):
    def test_valid_pure_and_mixed_scopes_preserve_prior_and_original_graphs(self):
        for mixed in(False,True):
            args=fixture(mixed);before=copy.deepcopy(args);r=collect(*args);self.assertEqual(len(r['records']),1);self.assertEqual(args,before);self.assertFalse(r['human_accepted']);self.assertEqual(r['vertical_attributes_assigned_from_plan'],0)
    def test_wrong_vertical_source_stale_paths_and_existing_writer_rejected(self):
        for case in('vertical','geometry','existing','whole','floor'):
            args=fixture(True);row=args[2]['records'][0]
            if case=='vertical':row['attribute_source_domains']['records'][1]['DN_source_route']='corresponding_floor_plan_horizontal'
            elif case=='geometry':row['axis_attribute_paths']=[[[0,0],[11,0]]]
            elif case=='existing':args[4]['existing_owner']=dict(records=[dict(axis_edge_id='E')])
            elif case=='whole':row['attribute_source_domains']['whole_edge_nominal_mm']=200
            else:row['floor']=3
            with self.assertRaises(ValueError):collect(*args)
if __name__=='__main__':unittest.main()
