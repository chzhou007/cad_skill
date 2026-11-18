import copy,unittest
from test_attach_lower_floor_plan_attributes import fixture as lower_fixture
from attach_network_named_lower_plan_attributes import append,ROOT,FIELD,SCOPE_MODE,MAPPING_MODE


def fixture():
    parent,local,plan,mapping,scope,*_=lower_fixture()
    mapping['mode']=MAPPING_MODE;mapping['graph_sha256']={'plan':'plan-graph','iso':'iso-graph'};mapping['source_sha256']={'plan':'plan','iso':'iso'}
    mapping['records']=[r for r in mapping['records'] if r['kind'].endswith('_approach')]
    scope.update(mode=SCOPE_MODE,mapping_sha256='b'*64,graph_sha256=mapping['graph_sha256'],source_sha256=mapping['source_sha256'],hil_ready=False)
    scope['records']=[r for r in scope['records'] if r['kind'].endswith('_approach')]
    for record,row in zip(mapping['records'],scope['records']):
        eid=record['iso_edges'][0];edge=next(e for e in parent['edges'] if e['edge_id']==eid);v=edge['axis_riser_attributes'][0]
        v.update(edge_id=eid,source_line_handle='native-vertical-'+record['system'])
        record.update(kind='network_anchored_named_lower_floor_approach',axis_network_T=record['iso_network_T'],independent_adjoining_main_mapping_id='MAIN-'+record['system'],retained_vertical_scope=copy.deepcopy(v))
        row.update(kind=record['kind'],identifier=record['identifier'],axis_network_T=record['axis_network_T'],plan_riser_interface=record['plan_riser_interface'],plan_network_T=record['plan_network_T'],
                   whole_axis_DN_assigned=False,installed_whole_edge_length_mm=None,plan_glyph_radius_added_to_length=False)
    # Additional-main evidence is an old field on an unrelated main.
    next(e for e in parent['edges'] if e['edge_id'].endswith('BRIDGE'))['anchored_floor_main_attributes']={'preserved':True}
    return parent,local,plan,mapping,scope,dict(parent='a'*64,mapping='b'*64,attributes='c'*64)


class Tests(unittest.TestCase):
    def test_two_horizontal_prefixes_preserve_all_old_attributes_and_vertical450(self):
        args=fixture();before=copy.deepcopy(args);graph,proof=append(*args)
        self.assertEqual(args,before);self.assertEqual(graph['nodes'],args[0]['nodes']);self.assertEqual(proof['added_prefix_scopes'],2)
        old={e['edge_id']:e for e in args[0]['edges']}
        for edge in graph['edges']:
            self.assertEqual({k:v for k,v in edge.items() if k!=FIELD},old[edge['edge_id']])
            if FIELD in edge:
                item=edge[FIELD];self.assertEqual(item['nominal_mm'],200);self.assertEqual(item['segment_indices'],[0])
                self.assertEqual(edge['axis_riser_attributes'][0]['nominal_mm'],450);self.assertIsNone(item['whole_edge_nominal_mm']);self.assertIsNone(item['whole_edge_physical_length_mm'])
        self.assertEqual(graph[ROOT],proof);self.assertFalse(graph['metadata']['hil_ready'])

    def test_scope_version_geometry_service_length_and_vertical_changes_block(self):
        for case in ('mapping','scope','duplicate','system','vertical','vertical_source','overlap','whole','metric','installed','radius','old_geometry','old_writer'):
            args=list(fixture());row=args[4]['records'][0];eid=row['iso_edges'][0];edge=next(e for e in args[0]['edges'] if e['edge_id']==eid)
            if case=='mapping':args[4]['mapping_sha256']='d'*64
            elif case=='scope':row['iso_segment_scopes'][0]['segment_indices']=[1]
            elif case=='duplicate':args[4]['records'][1]=copy.deepcopy(row)
            elif case=='system':row['system']='wrong'
            elif case=='vertical':edge['axis_riser_attributes'][0]['floor_pair']=[2,3]
            elif case=='vertical_source':edge['axis_riser_attributes'][0]['source_line_handle']='changed'
            elif case=='overlap':edge['axis_riser_attributes'][0]['segment_index']=0
            elif case=='whole':row['iso_segment_scopes'][0]['whole_local_edge']=True
            elif case=='metric':row['horizontal_projection']['pieces'][0]['length_mm']+=1
            elif case=='installed':row['installed_whole_edge_length_mm']=10
            elif case=='radius':row['plan_glyph_radius_added_to_length']=True
            elif case=='old_geometry':edge['device_names']=[]
            else:edge['plan_segment_attributes']=[{}]
            with self.subTest(case=case),self.assertRaises(ValueError):append(*args)

if __name__=='__main__':unittest.main()
