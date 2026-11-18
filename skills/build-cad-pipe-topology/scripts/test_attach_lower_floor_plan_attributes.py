import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_named_lower_floor_plan_attributes import fixture as plan_fixture
from test_match_named_riser_lower_floor_segments import fixture as segment_fixture
from named_lower_floor_plan_attributes import MODE,attribute
from native_touching_plan_path_chunks import project
from native_path_coverage_audit import audit
from native_plan_projection_lengths import lengths
from attach_lower_floor_plan_attributes import append,ROOT,implementation_hashes


def fixture():
    doc,plan,mapping,policy=plan_fixture();local=segment_fixture()[1]['iso']
    for graph in (plan,local):
        nodes={n['node_id']:n for n in graph['nodes']}
        for edge in graph['edges']:
            edge.update(start_floor=nodes[edge['start_node_id']]['floor'],end_floor=nodes[edge['end_node_id']]['floor'])
            edge['device_names']=['component:'+edge['edge_id']]
    parent=copy.deepcopy(local);parent['sourceUpperFloorPlanSegmentAttributes']={'preserved':True}
    for edge in parent['edges']:
        if edge['edge_id'].endswith('MIX'):
            edge['axis_riser_attributes']=[dict(path_index=0,segment_index=1,scope_points=copy.deepcopy(edge['attribute_paths'][0][1:]),
                floor_pair=[1,2],nominal_mm=450,physical_length_mm=None)]
        if edge['edge_id'].endswith('EQ'):edge['cross_view_attributes']=dict(previous_DN=200,previous_length=17)
        if edge['edge_id'].endswith('LOW'):edge['plan_segment_attributes']=[dict(prior_upper=True)]
    dn,_=attribute(doc,plan,mapping,policy,'plan','plan-graph');by={r['edge_id']:r for r in dn['records']};rows=[]
    for record in mapping['records']:
        pid=record['plan_edges'][0];projection,_,locations=project(plan,[pid],1)
        coverage=audit(doc,projection,dict(source_sha256='plan',graph_sha256='projected',edges=[pid]),'plan','projected')
        metric=lengths(projection,coverage,record,dict(plan_window=[-1000,1000,-1000,1000]))
        for piece in metric['pieces']:
            p=locations[(pid,piece['segment_index'])];piece.update(path_index=p['path_index'],segment_index=p['segment_index'])
        rows.append(dict(mapping_id=record['mapping_id'],kind=record['kind'],floor=1,system=record['system'],
            plan_edges=record['plan_edges'],iso_edges=record['iso_edges'],iso_segment_scopes=copy.deepcopy(record['iso_segment_scopes']),
            diameter=by[pid],horizontal_projection=metric,whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,
            physical_port_verified=False,human_accepted=False))
    scope=dict(mode=MODE,status='source_checked_lower_floor_plan_DN_and_XY_scopes_not_fused',mapping_sha256='b'*64,
        source_sha256='plan',graph_sha256='plan-graph',records=rows,physical_values_fused=False,physical_ports_verified=False,
        local_graphs_mutated=False,human_accepted=False,whole_axis_DN_assigned=0,installed_lengths_assigned=0)
    return parent,local,plan,mapping,scope,'a'*64,'b'*64,'c'*64,[0,45,135]


class Tests(unittest.TestCase):
    def test_lower_prefix_and_full_mains_preserve_upper_vertical_and_components(self):
        args=fixture();before=copy.deepcopy(args[0]);out,proof=append(*args)
        self.assertEqual(args[0],before);self.assertEqual(out['nodes'],before['nodes'])
        self.assertEqual(out['sourceUpperFloorPlanSegmentAttributes'],before['sourceUpperFloorPlanSegmentAttributes'])
        old={e['edge_id']:e for e in before['edges']};now={e['edge_id']:e for e in out['edges']}
        selected=set(proof['added_axis_edges'])
        for eid in old:
            self.assertEqual({k:v for k,v in now[eid].items() if k!='plan_segment_attributes'} if eid in selected else now[eid],old[eid])
        for system in ('supply','return'):
            a=now[system+'MIX']['plan_segment_attributes'][0];m=now[system+'BRIDGE']['plan_segment_attributes'][0]
            self.assertEqual(a['nominal_mm'],200);self.assertEqual(a['segment_indices'],[0]);self.assertIsNone(a['whole_edge_nominal_mm'])
            self.assertIsNone(a['whole_edge_centerline_route_mm']);self.assertEqual(now[system+'MIX']['axis_riser_attributes'],old[system+'MIX']['axis_riser_attributes'])
            self.assertEqual(m['whole_edge_nominal_mm'],200);self.assertEqual(m['whole_edge_centerline_route_mm'],10)
            self.assertIsNone(m['pipe_net_cut_length_mm']);self.assertFalse(m['physical_port_verified'])
        self.assertEqual(len(out[ROOT]['records']),4);self.assertFalse(out['metadata']['hil_ready'])

    def test_changed_scope_unknown_values_and_overlapping_writers_are_rejected(self):
        for case in ('overlap','no_vertical','whole_mixed','metric','metric_path','system','mapping','installed','old_geometry','duplicate','new_writer','prior_segment','bad_direction','bad_floor','floor_pair','tail_points'):
            args=list(fixture());row=args[4]['records'][0];eid=row['iso_edges'][0];edge=next(e for e in args[0]['edges'] if e['edge_id']==eid)
            if case=='overlap':edge['axis_riser_attributes'][0]['segment_index']=0
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
            elif case=='prior_segment':edge['plan_segment_attributes']=[]
            elif case=='bad_direction':args[-1]=[0]
            elif case=='bad_floor':next(e for e in args[2]['edges'] if e['edge_id']=='supplyBRIDGE')['start_floor']=2
            elif case=='floor_pair':edge['axis_riser_attributes'][0]['floor_pair']=[2,3]
            else:edge['axis_riser_attributes'][0]['scope_points'][0][0]+=1
            with self.subTest(case=case),self.assertRaises(ValueError):append(*args)

    def test_original_multi_segment_metric_identities_and_total_survive(self):
        args=list(fixture());row=next(r for r in args[4]['records'] if r['iso_edges']==['supplyBRIDGE'])
        self.assertEqual(len(row['horizontal_projection']['pieces']),2)
        out,_=append(*args);actual=next(e for e in out['edges'] if e['edge_id']=='supplyBRIDGE')['plan_segment_attributes'][0]
        self.assertEqual(actual['horizontal_projection'],row['horizontal_projection'])
        self.assertEqual(actual['diameter_evidence'],row['diameter'])

    def test_reapplication_and_dependencies(self):
        args=list(fixture());out,_=append(*args);args[0]=out
        with self.assertRaises(ValueError):append(*args)
        for name in ('attach_upper_floor_plan_attributes.py','named_lower_floor_plan_attributes.py','diameter_tee_inheritance.py','native_replay_session.py'):
            self.assertIn(name,implementation_hashes())

    def test_each_root_rebuild_rechecks_both_child_closures_and_invalidates_changed_source(self):
        from attach_lower_floor_plan_attributes import compute
        from confirm_crossview_paths import sha
        owner=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
        if str(owner) not in sys.path:sys.path.insert(0,str(owner))
        from native_replay_session import replay_session
        args=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);stage=root/'scope';stage.mkdir();parent=root/'parent';parent.mkdir()
            def write(path,data):path.write_text(json.dumps(data),'utf8');return path
            pg=write(parent/'graph_with_edges.json',args[0]);local=write(root/'local.json',args[1]);plan=write(root/'plan.json',args[2])
            mapped=copy.deepcopy(args[3]);mapped['graph_sha256']['iso']=sha(local)
            mapping=write(root/'mapping.json',mapped);scope=copy.deepcopy(args[4]);scope['mapping_sha256']=sha(mapping)
            sp=write(stage/'lower-floor-plan-attributes.json',scope)
            receipt=write(stage/'lower-floor-plan-attribute-receipt.json',dict(inputs=dict(mapping=dict(path=str(mapping)),graph=dict(path=str(plan)))))
            devices=root/'devices.csv';devices.write_text('native components','utf8');dependency=root/'native-source.dxf';dependency.write_text('version1','utf8')
            paths=dict(parent_graph=pg,attribute_scope=sp,attribute_receipt=receipt,devices=devices)
            policy={k+'_sha256':sha(v) for k,v in paths.items()};policy['isometric_horizontal_directions_degrees']=args[-1]
            parent_proof=dict(output_graph_sha256=sha(pg),inputs=dict(devices=dict(sha256=sha(devices))),native_local_graph=dict(path=str(local),sha256=sha(local)))
            def replay_scope(directory):dependency.read_bytes();return scope
            def replay_parent(directory):pg.read_bytes();return parent_proof
            with replay_session() as session,patch('attach_lower_floor_plan_attributes.verify_scopes',side_effect=replay_scope) as scopes,patch('attach_lower_floor_plan_attributes.verify_parent',side_effect=replay_parent) as prior:
                first,_=compute(paths,policy);second,_=compute(paths,policy)
                self.assertEqual(first,second);self.assertEqual(scopes.call_count,1);self.assertEqual(prior.call_count,1)
                dependency.write_text('version2','utf8');third,_=compute(paths,policy)
                self.assertEqual(first,third);self.assertEqual(scopes.call_count,2);self.assertEqual(prior.call_count,1)
                self.assertGreaterEqual(session.statistics()['same_batch_reuses'],3)


if __name__=='__main__':unittest.main()
