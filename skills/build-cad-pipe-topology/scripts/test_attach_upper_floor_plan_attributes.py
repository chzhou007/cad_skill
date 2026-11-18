import copy,unittest
from test_named_upper_floor_plan_attributes import fixture as plan_fixture
from test_match_named_riser_floor_segments import fixture as segment_fixture
from named_upper_floor_plan_attributes import MODE,attribute
from native_touching_plan_path_chunks import project
from native_path_coverage_audit import audit
from native_plan_projection_lengths import lengths
from attach_upper_floor_plan_attributes import append,ROOT,implementation_hashes


def fixture():
    doc,plan,mapping,policy,_=plan_fixture();local=segment_fixture()[1]['iso']
    for graph in (plan,local):
        nodes={n['node_id']:n for n in graph['nodes']}
        for edge in graph['edges']:
            edge.update(start_floor=nodes[edge['start_node_id']]['floor'],end_floor=nodes[edge['end_node_id']]['floor'])
            edge['device_names']=['component:'+edge['edge_id']]
    parent=copy.deepcopy(local);parent['old_attribute_audit']=dict(preserved=True)
    for edge in parent['edges']:
        if edge['edge_id'].endswith('MIX'):
            edge['axis_riser_attributes']=[dict(path_index=0,segment_index=0,nominal_mm=450,physical_length_mm=None)]
        if edge['edge_id'].endswith('EQ'):edge['cross_view_attributes']=dict(previous_DN=250,previous_length=17)
    dn,_=attribute(doc,plan,mapping,policy,'plan','plan-graph');by={r['edge_id']:r for r in dn['records']};rows=[]
    for record in mapping['records']:
        pid=record['plan_edges'][0];projection,_,locations=project(plan,[pid],3)
        coverage=audit(doc,projection,dict(source_sha256='plan',graph_sha256='projected',edges=[pid]),'plan','projected')
        metric=lengths(projection,coverage,record,dict(plan_window=[-1000,1000,-1000,1000]))
        for piece in metric['pieces']:
            p=locations[(pid,piece['segment_index'])];piece.update(path_index=p['path_index'],segment_index=p['segment_index'])
        rows.append(dict(mapping_id=record['mapping_id'],kind=record['kind'],floor=3,system=record['system'],
            plan_edges=record['plan_edges'],iso_edges=record['iso_edges'],iso_segment_scopes=copy.deepcopy(record['iso_segment_scopes']),
            diameter=by[pid],horizontal_projection=metric,whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,
            physical_port_verified=False,human_accepted=False))
    scope=dict(mode=MODE,status='source_checked_upper_floor_plan_DN_and_XY_scopes_not_fused',mapping_sha256='b'*64,
        source_sha256='plan',graph_sha256='plan-graph',records=rows,physical_values_fused=False,physical_ports_verified=False,
        local_graphs_mutated=False,human_accepted=False,whole_axis_DN_assigned=0,installed_lengths_assigned=0)
    return parent,local,plan,mapping,scope,'a'*64,'b'*64,'c'*64,[0,45,135]


class Tests(unittest.TestCase):
    def test_preserves_old_plan_vertical_components_and_assigns_only_proven_domains(self):
        args=fixture();before=copy.deepcopy(args[0]);out,proof=append(*args)
        self.assertEqual(args[0],before);self.assertEqual(out['nodes'],before['nodes']);self.assertEqual(out['old_attribute_audit'],before['old_attribute_audit'])
        old={e['edge_id']:e for e in before['edges']};now={e['edge_id']:e for e in out['edges']}
        for eid in old:self.assertEqual({k:v for k,v in now[eid].items() if k!='plan_segment_attributes'},old[eid])
        for system in ('supply','return'):
            a=now[system+'MIX']['plan_segment_attributes'][0];m=now[system+'BRIDGE']['plan_segment_attributes'][0]
            self.assertEqual(a['nominal_mm'],300);self.assertEqual(a['segment_indices'],[1]);self.assertIsNone(a['whole_edge_nominal_mm'])
            self.assertIsNone(a['whole_edge_centerline_route_mm']);self.assertEqual(now[system+'MIX']['axis_riser_attributes'][0]['nominal_mm'],450)
            self.assertEqual(m['whole_edge_nominal_mm'],250);self.assertEqual(m['whole_edge_centerline_route_mm'],10)
            self.assertIsNone(m['pipe_net_cut_length_mm']);self.assertFalse(m['physical_port_verified'])
        self.assertEqual(len(out[ROOT]['records']),4);self.assertEqual(len(proof['complete_main_centerline_route_edges']),2)
        self.assertFalse(out['metadata']['hil_ready'])

    def test_mixed_scope_overlap_source_metric_wrong_service_and_duplicate_writer_block(self):
        for case in ('overlap','no_vertical','whole_mixed','metric','metric_path','system','mapping','installed','old_geometry','duplicate','new_writer','bad_direction','bad_floor'):
            args=list(fixture());row=args[4]['records'][0];eid=row['iso_edges'][0];edge=next(e for e in args[0]['edges'] if e['edge_id']==eid)
            if case=='overlap':edge['axis_riser_attributes'][0]['segment_index']=1
            elif case=='no_vertical':edge.pop('axis_riser_attributes')
            elif case=='whole_mixed':row['whole_axis_DN_selected']=True
            elif case=='metric':row['horizontal_projection']['value_mm']+=1
            elif case=='metric_path':row['horizontal_projection']['pieces'][0]['path_index']=99
            elif case=='system':row['diameter']['system']='return'
            elif case=='mapping':row['iso_segment_scopes'][0]['scope_paths'][0][0][0]+=1
            elif case=='installed':row['horizontal_projection']['unshown_connection_length_mm']=0
            elif case=='old_geometry':edge['attribute_paths'][0][0][0]+=1
            elif case=='duplicate':args[4]['records'][1]=copy.deepcopy(row)
            elif case=='new_writer':edge['cross_view_attributes']={}
            elif case=='bad_direction':args[-1]=[0]
            else:next(e for e in args[2]['edges'] if e['edge_id']=='supplyBRIDGE')['start_floor']=2
            with self.subTest(case=case),self.assertRaises(ValueError):append(*args)

    def test_exact_touching_bent_plan_and_bent_axis_main_keep_one_route_total(self):
        args=list(fixture());plan=args[2];mapping=args[3];scope=args[4];local=args[1];parent=args[0]
        pe=next(e for e in plan['edges'] if e['edge_id']=='supplyBRIDGE')
        pe['attribute_paths']=[[[10,0],[12,0],[12,10]],[[12,10],[10,10]]]
        record=next(r for r in mapping['records'] if r['iso_edges']==['supplyBRIDGE']);row=next(r for r in scope['records'] if r['iso_edges']==['supplyBRIDGE'])
        row['diameter']['scope_paths']=copy.deepcopy(pe['attribute_paths']);row['horizontal_projection']['pieces']=[]
        for pi,path in enumerate(pe['attribute_paths']):
            for si,(a,b) in enumerate(zip(path,path[1:])):
                import math
                row['horizontal_projection']['pieces'].append(dict(plan_edge='supplyBRIDGE',path_index=pi,segment_index=si,points=[a,b],length_mm=math.dist(a,b),source_line_handle='native:'+str((pi,si))))
        row['horizontal_projection']['value_mm']=14
        for graph in (local,parent):next(e for e in graph['edges'] if e['edge_id']=='supplyBRIDGE')['attribute_paths']=[[[110,40],[115,45],[120,45],[120,50]]]
        record['iso_segment_scopes'][0].update(segment_indices=[0,1,2],scope_paths=[[[110,40],[115,45],[120,45],[120,50]]])
        row['iso_segment_scopes']=copy.deepcopy(record['iso_segment_scopes'])
        with self.assertRaises(ValueError):append(*args)  # plumb final segment is not a horizontal axis
        for graph in (local,parent):next(e for e in graph['edges'] if e['edge_id']=='supplyBRIDGE')['attribute_paths']=[[[110,40],[115,45],[120,50]]]
        record['iso_segment_scopes'][0].update(segment_indices=[0,1],scope_paths=[[[110,40],[115,45],[120,50]]]);row['iso_segment_scopes']=copy.deepcopy(record['iso_segment_scopes'])
        out,_=append(*args);item=next(e for e in out['edges'] if e['edge_id']=='supplyBRIDGE')['plan_segment_attributes'][0]
        self.assertEqual(item['whole_edge_centerline_route_mm'],14);self.assertEqual(len(item['horizontal_projection']['pieces']),3)

    def test_double_application_and_changed_dependency_closure(self):
        args=list(fixture());out,_=append(*args);args[0]=out
        with self.assertRaises(ValueError):append(*args)
        hashes=implementation_hashes()
        for name in ('attach_named_riser_plan_attributes.py','named_upper_floor_plan_attributes.py','native_touching_plan_path_chunks.py'):
            self.assertIn(name,hashes)


if __name__=='__main__':unittest.main()
