import copy,unittest
from test_named_riser_plan_attributes import fixture as plan_fixture
from test_match_named_riser_floor_paths import fixture as mapping_fixture
from attach_named_riser_plan_attributes import append,ROOT,BASIS,implementation_hashes
from named_riser_plan_attributes import MODE
from native_path_coverage_audit import audit
from native_plan_projection_lengths import lengths


def fixture():
    doc,plan,mapping=plan_fixture();local=copy.deepcopy(mapping_fixture()[1]['iso'])
    for edge in local['edges']:edge['device_names']=['valve-'+edge['edge_id']]
    parent=copy.deepcopy(local);parent['sourceCheckedCrossViewAttributeFusion']=dict(records=[dict(mapping_id='OLD')])
    parent['old_normalization_audit']=dict(preserved=True)
    next(e for e in parent['edges'] if e['edge_id']=='supplyMAIN')['cross_view_attributes']=dict(prior_value=200,old_length=17)
    next(e for e in parent['edges'] if e['edge_id']=='supplyLOW')['axis_riser_attributes']=[dict(prior_vertical_DN=450,physical_length_mm=None)]
    ids=[r['plan_edges'][0] for r in mapping['records']]
    coverage=audit(doc,plan,dict(source_sha256='plan',graph_sha256='plan-graph',edges=ids),'plan','plan-graph')
    units=dict(plan_window=[-100,500,-100,500]);rows=[];diameters={}
    for record in mapping['records']:
        eid=record['plan_edges'][0];edge=next(e for e in plan['edges'] if e['edge_id']==eid)
        diameter=dict(edge_id=eid,system=record['system'],nominal_mm=300,status='direct_plan_DN',
            lineage=[dict(nominal_mm=300,evidence=[dict(evidence_id='source:'+eid,edge_path=[eid])])],
            scope_paths=edge['attribute_paths'],scope='native_plan_drawn_pipe_paths_only',human_accepted=False)
        rows.append(dict(mapping_id=record['mapping_id'],plan_edges=record['plan_edges'],iso_edges=record['iso_edges'],
            system=record['system'],floor=record['floor'],plan_riser_interface=record['plan_riser_interface'],iso_riser_junction=record['iso_riser_junction'],
            diameter=diameter,horizontal_projection=lengths(plan,coverage,record,units),plan_glyph_radius_added_to_length=False,
            physical_port_verified=False,installed_whole_edge_length_mm=None,human_accepted=False))
        diameters[record['mapping_id']]=dict(nominal_mm=None,status='plan_diameter_scope_unresolved',plan_candidate=None,plan_observations=[],axis_observation=None,selected_physical_diameter=False)
    scope=dict(mode=MODE,physical_values_fused=False,local_graphs_mutated=False,physical_ports_verified=False,human_accepted=False,
        installed_lengths_assigned=0,mapping_sha256='m'*64,records=rows,source_sha256='plan',graph_sha256='plan-graph')
    return parent,local,plan,mapping,scope,coverage,units,diameters,'d'*64,'m'*64,'p'*64


class Tests(unittest.TestCase):
    def test_composition_preserves_prior_plan_vertical_and_component_assets(self):
        args=fixture();before=copy.deepcopy(args[0]);out,proof=append(*args)
        self.assertEqual(args[0],before);self.assertEqual(out['sourceCheckedCrossViewAttributeFusion'],before['sourceCheckedCrossViewAttributeFusion'])
        self.assertEqual(out['old_normalization_audit'],before['old_normalization_audit']);self.assertEqual(out['nodes'],before['nodes'])
        old={e['edge_id']:e for e in before['edges']};now={e['edge_id']:e for e in out['edges']}
        for eid in old:
            if eid not in ('supplyRIF','returnRIF'):self.assertEqual(old[eid],now[eid])
        for eid in ('supplyRIF','returnRIF'):
            c=now[eid]['cross_view_attributes'];self.assertEqual(c['mapping_basis'],BASIS)
            self.assertEqual(c['diameter']['plan_drawn_nominal_mm'],300);self.assertIsNone(c['diameter']['nominal_mm'])
            self.assertEqual(c['horizontal_projection']['edge_value_mm'],9);self.assertIsNone(c['whole_edge_physical_length_mm'])
            self.assertFalse(c['named_riser_interface_context']['graphic_circle_radius_added_to_length'])
        self.assertEqual(len(out[ROOT]['records']),2);self.assertTrue(proof['prior_edges_and_vertical_attributes_preserved'])
        self.assertFalse(out['metadata']['hil_ready'])

    def test_wrong_scope_metrics_or_selected_geometry_cannot_reuse_mapping(self):
        for case in ('radius','installed','floor','system','scope_hash','parent_path','local_node','new_writer'):
            args=list(fixture());row=args[4]['records'][0]
            if case=='radius':row['plan_glyph_radius_added_to_length']=True
            elif case=='installed':row['installed_whole_edge_length_mm']=10
            elif case=='floor':row['floor']=3
            elif case=='system':row['system']='return'
            elif case=='scope_hash':args[4]['mapping_sha256']='changed'
            elif case=='parent_path':next(e for e in args[0]['edges'] if e['edge_id']=='supplyRIF')['attribute_paths'][0][0][0]+=1
            elif case=='local_node':args[1]['nodes'][0]['x']+=1
            else:next(e for e in args[0]['edges'] if e['edge_id']=='supplyRIF')['cross_view_attributes']={}
            with self.subTest(case=case),self.assertRaises(ValueError):append(*args)

    def test_empty_or_repeated_scopes_and_double_application_block(self):
        args=list(fixture());args[4]['records'].append(copy.deepcopy(args[4]['records'][0]))
        with self.assertRaises(ValueError):append(*args)
        args=list(fixture());out,_=append(*args);args[0]=out
        with self.assertRaises(ValueError):append(*args)

    def test_implementation_closure_contains_both_parent_and_new_source_stages(self):
        hashes=implementation_hashes()
        for name in ('attach_axis_riser_segment_attributes.py','named_riser_plan_attributes.py','attach_source_checked_plan_attributes.py','fuse_plan_DN_scopes.py'):
            self.assertIn(name,hashes)


if __name__=='__main__':unittest.main()
