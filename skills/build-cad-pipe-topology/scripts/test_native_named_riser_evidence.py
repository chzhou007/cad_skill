import copy,importlib.util,math,sys,unittest
from pathlib import Path
import ezdxf
from ezdxf.math import Matrix44
from native_named_riser_evidence import collect,label
from native_line_path_evidence import LAYERS


class NamedRiserEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.doc=ezdxf.new('R2013');m=self.doc.modelspace();self.source='a'*64;self.hash='b'*64
        self.text=m.add_text('CHWS1 DN450',dxfattribs=dict(insert=(1,10.5),height=2,layer='ANNOT'))
        self.under=m.add_line((0,10),(10,10),dxfattribs=dict(layer='ANNOT'));self.leader=m.add_line((10,10),(20,0),dxfattribs=dict(layer='ANNOT'))
        self.circle=m.add_circle((20,0),1,dxfattribs=dict(layer=LAYERS['supply']));self.pipe=m.add_line((20,0),(30,0),dxfattribs=dict(layer=LAYERS['supply']))
        self.graph=dict(metadata=dict(source_sha256=self.source),nodes=[dict(node_id='RIF1',node_type='virtual_equipment',subtype='out_of_plane_riser',system='supply',floor=1,x=20.,y=0.,source_handle=self.circle.dxf.handle),dict(node_id='N',node_type='tee',system='supply',floor=1,x=30.,y=0.)],
            edges=[dict(edge_id='E1',start_node_id='RIF1',end_node_id='N',system='supply',attribute_paths=[[[20.,0.],[30.,0.]]])])
        self.policy=dict(source_sha256=self.source,graph_sha256=self.hash,text_layers=['ANNOT'],leader_layers=['ANNOT'],selections=[dict(text_handle=self.text.dxf.handle,expected_text='CHWS1 DN450',underline_handle=self.under.dxf.handle,leader_handle=self.leader.dxf.handle,target=dict(kind='plan_riser_circle',node_id='RIF1',circle_handle=self.circle.dxf.handle))])

    def run_collect(self):return collect(self.doc,self.graph,self.policy,self.source,self.hash)

    def test_direct_circle_binding_keeps_graph_and_physical_values_unknown(self):
        before=copy.deepcopy(self.graph);result=self.run_collect();row=result['records'][0]
        self.assertEqual(row['identifier'],'CHWS1');self.assertEqual(row['target']['node_id'],'RIF1');self.assertEqual(row['nominal_mm_observed'],450)
        self.assertEqual(self.graph,before);self.assertFalse(result['graph_mutated']);self.assertFalse(row['crossview_mapping_confirmed']);self.assertFalse(row['physical_diameter_selected']);self.assertIsNone(row['physical_length_mm'])

    def test_rotated_native_annotations(self):
        for degrees in (45,90,180,270):
            with self.subTest(degrees=degrees):
                self.setUp();matrix=Matrix44.z_rotate(math.radians(degrees))
                for entity in self.doc.modelspace():entity.transform(matrix)
                for node in self.graph['nodes']:
                    p=matrix.transform((node['x'],node['y'],0));node.update(x=p.x,y=p.y)
                for edge in self.graph['edges']:
                    edge['attribute_paths']=[[[matrix.transform((*p,0)).x,matrix.transform((*p,0)).y] for p in path] for path in edge['attribute_paths']]
                self.assertEqual(self.run_collect()['records'][0]['identifier'],'CHWS1')

    def test_return_identifier_and_layer_are_separate_from_geometry(self):
        self.text.dxf.text='CHWR2 DN300';self.policy['selections'][0]['expected_text']='CHWR2 DN300'
        for node in self.graph['nodes']:node['system']='return'
        self.graph['edges'][0]['system']='return';self.pipe.dxf.layer=LAYERS['return'];self.circle.dxf.layer=LAYERS['return']
        self.assertEqual(self.run_collect()['records'][0]['system'],'return')

    def test_stale_source_graph_or_metadata_rejected(self):
        for key in ('source_sha256','graph_sha256'):
            with self.subTest(key=key):
                old=self.policy[key];self.policy[key]='c'*64
                with self.assertRaises(ValueError):self.run_collect()
                self.policy[key]=old
        self.graph['metadata']['source_sha256']='c'*64
        with self.assertRaises(ValueError):self.run_collect()

    def test_text_mismatch_and_mirrored_flags_rejected(self):
        self.text.dxf.text='CHWS9 DN450'
        with self.assertRaises(ValueError):self.run_collect()
        self.text.dxf.text='CHWS1 DN450';self.text.dxf.text_generation_flag=2
        with self.assertRaises(ValueError):self.run_collect()

    def test_unsupported_parser_and_nonfinite_DN(self):
        for value in ('CHWS0 DN450','CHWS1 DN0','CHWS1 DN450(3.200)','CHWS1/CHWR1 DN450','金属软管 DN450','CHWS1 DN'+('9'*400)):
            with self.subTest(value=value),self.assertRaises(ValueError):label(value)
        self.assertEqual(label(' chwr 2 DN 450 ')['identifier'],'CHWR2')

    def test_duplicate_underlines_rejected(self):
        self.doc.modelspace().add_line((0,10),(10,10),dxfattribs=dict(layer='ANNOT'))
        with self.assertRaises(ValueError):self.run_collect()

    def test_text_at_native_underline_endpoint_is_supported(self):
        self.text.dxf.insert=(0,10.5);self.assertEqual(self.run_collect()['records'][0]['identifier'],'CHWS1')
        self.text.dxf.insert=(-1,10.5)
        with self.assertRaises(ValueError):self.run_collect()

    def test_shared_annotation_star_rejected(self):
        self.doc.modelspace().add_line((10,10),(25,5),dxfattribs=dict(layer='ANNOT'))
        with self.assertRaises(ValueError):self.run_collect()

    def test_underline_without_expected_layer_rejected(self):
        self.under.dxf.layer='ARCHITECTURE'
        with self.assertRaises(ValueError):self.run_collect()

    def test_circle_z_and_graph_position_changes_rejected(self):
        self.circle.dxf.center=(20,0,1)
        with self.assertRaises(ValueError):self.run_collect()
        self.circle.dxf.center=(20,0,0);self.graph['nodes'][0]['x']=21
        with self.assertRaises(ValueError):self.run_collect()

    def test_wrong_system_or_interface_incidence_rejected(self):
        self.graph['nodes'][0]['system']='return'
        with self.assertRaises(ValueError):self.run_collect()
        self.graph['nodes'][0]['system']='supply';self.graph['edges'].append(dict(self.graph['edges'][0],edge_id='E2'))
        with self.assertRaises(ValueError):self.run_collect()

    def test_nonfinite_source_circle_or_graph_position_rejected(self):
        self.circle.dxf.center=(20,0,float('nan'))
        with self.assertRaises(ValueError):self.run_collect()
        self.circle.dxf.center=(20,0,0);self.graph['nodes'][0]['x']=float('nan')
        with self.assertRaises(ValueError):self.run_collect()

    def test_repeated_identifier_is_not_merged_across_local_targets(self):
        m=self.doc.modelspace();text=m.add_text('CHWS1 DN450',dxfattribs=dict(insert=(51,10.5),height=2,layer='ANNOT'))
        under=m.add_line((50,10),(60,10),dxfattribs=dict(layer='ANNOT'));leader=m.add_line((60,10),(70,0),dxfattribs=dict(layer='ANNOT'));circle=m.add_circle((70,0),1)
        self.graph['nodes']+=[dict(node_id='RIF2',subtype='out_of_plane_riser',system='supply',floor=1,x=70.,y=0.,source_handle=circle.dxf.handle),dict(node_id='N2',system='supply',floor=1,x=80.,y=0.)]
        self.graph['edges'].append(dict(edge_id='E2',start_node_id='RIF2',end_node_id='N2',system='supply',attribute_paths=[[[70.,0.],[80.,0.]]]))
        self.policy['selections'].append(dict(text_handle=text.dxf.handle,expected_text='CHWS1 DN450',underline_handle=under.dxf.handle,leader_handle=leader.dxf.handle,target=dict(kind='plan_riser_circle',node_id='RIF2',circle_handle=circle.dxf.handle)))
        before=copy.deepcopy(self.graph);rows=self.run_collect()['records'];self.assertEqual(len(rows),2);self.assertEqual(len({r['identifier'] for r in rows}),1);self.assertEqual(self.graph,before);self.assertTrue(all(r['crossview_mapping_confirmed'] is False for r in rows))
    def axis(self):
        self.policy['selections'][0]['target']=dict(kind='axis_source_line',line_handle=self.pipe.dxf.handle)

    def test_axis_target_preserves_source_point_and_coverage(self):
        self.axis();before=copy.deepcopy(self.graph);row=self.run_collect()['records'][0]
        self.assertEqual(row['target']['source_line_handle'],self.pipe.dxf.handle);self.assertEqual(row['target']['target_graph_coverage'][0]['edge_id'],'E1');self.assertEqual(self.graph,before)

    def test_axis_competing_source_pipes_rejected_even_other_system(self):
        self.axis();self.doc.modelspace().add_line((20,0),(20,5),dxfattribs=dict(layer=LAYERS['return']))
        with self.assertRaises(ValueError):self.run_collect()

    def test_axis_uncovered_target_is_reported_without_creating_edge(self):
        self.axis();self.graph['edges'][0]['attribute_paths']=[[[22.,0.],[30.,0.]]]
        result=self.run_collect()['records'][0];self.assertEqual(result['target']['target_graph_coverage'],[]);self.assertFalse(result['crossview_mapping_confirmed'])

    def test_axis_native_contacts_expose_missing_junction_without_joining(self):
        self.axis();self.doc.modelspace().add_line((20,0),(10,0),dxfattribs=dict(layer=LAYERS['supply']))
        # The label target is strictly unique; move its tip into the source
        # line so the new endpoint contact is not an ambiguous label landing.
        self.leader.dxf.end=(25,0);row=self.run_collect()['records'][0]
        self.assertEqual(len(row['target']['native_endpoint_contacts']),1);self.assertFalse(row['target']['native_endpoint_contacts'][0]['connection_accepted'])

    def test_axis_wrong_Z_not_projected_onto_pipe(self):
        self.axis();self.pipe.dxf.start=(20,0,1);self.pipe.dxf.end=(30,0,1)
        with self.assertRaises(ValueError):self.run_collect()

    def corner(self):
        self.other=self.doc.modelspace().add_line((10,-10),(20,0),dxfattribs=dict(layer=LAYERS['supply']))
        self.policy['selections'][0]['target']=dict(kind='axis_source_corner',line_handles=[self.pipe.dxf.handle,self.other.dxf.handle])
        self.graph['edges'][0]['attribute_paths']=[[[10.,-10.],[20.,0.],[30.,0.]]];self.graph['nodes'][0].update(x=10.,y=-10.)

    def test_axis_declared_corner_requires_one_native_and_graph_bend(self):
        self.corner();row=self.run_collect()['records'][0];self.assertTrue(row['target']['one_graph_corner_not_a_new_T']);self.assertFalse(row['crossview_mapping_confirmed'])

    def test_axis_corner_does_not_allow_crossings_or_other_system(self):
        self.corner();self.other.dxf.start=(10,0);self.other.dxf.end=(40,0)
        with self.assertRaises(ValueError):self.run_collect()
        self.other.dxf.start=(10,-10);self.other.dxf.end=(20,0);self.other.dxf.layer=LAYERS['return']
        with self.assertRaises(ValueError):self.run_collect()

    def test_axis_corner_does_not_join_separate_edges_or_a_tee(self):
        self.corner();self.graph['edges'].append(dict(self.graph['edges'][0],edge_id='E2'))
        with self.assertRaises(ValueError):self.run_collect()
        self.graph['edges'].pop();self.doc.modelspace().add_line((20,0),(20,5),dxfattribs=dict(layer=LAYERS['supply']))
        with self.assertRaises(ValueError):self.run_collect()

    def test_named_T_landing_exposes_missing_graph_node_without_fixing_it(self):
        self.corner();self.other.dxf.start=(10,0);third=self.doc.modelspace().add_line((20,0),(20,5),dxfattribs=dict(layer=LAYERS['supply']))
        self.policy['selections'][0]['target']=dict(kind='axis_source_junction',line_handles=[self.pipe.dxf.handle,self.other.dxf.handle,third.dxf.handle])
        before=copy.deepcopy(self.graph);target=self.run_collect()['records'][0]['target']
        self.assertTrue(target['native_three_endpoint_T']);self.assertTrue(target['local_topology_recheck_required']);self.assertEqual(target['current_graph_nodes'],[]);self.assertFalse(target['connection_accepted']);self.assertEqual(self.graph,before)

    def test_named_T_does_not_promote_ordinary_crossing(self):
        self.corner();self.other.dxf.start=(10,0);third=self.doc.modelspace().add_line((20,-5),(20,5),dxfattribs=dict(layer=LAYERS['supply']))
        self.policy['selections'][0]['target']=dict(kind='axis_source_junction',line_handles=[self.pipe.dxf.handle,self.other.dxf.handle,third.dxf.handle])
        with self.assertRaises(ValueError):self.run_collect()

    def legacy_geometry(self):
        key='named_riser_test_legacy_geometry'
        if key not in sys.modules:
            spec=importlib.util.spec_from_file_location(key,Path(__file__).with_name('legacy_v17')/'analyze_graph.py');module=importlib.util.module_from_spec(spec);sys.modules[key]=module;spec.loader.exec_module(module)
        return sys.modules[key]

    def air_vent_fixture(self):
        self.down=self.doc.modelspace().add_line((20,-10),(20,0),dxfattribs=dict(layer=LAYERS['supply']))
        self.stub=self.doc.modelspace().add_line((20,0),(20,5),dxfattribs=dict(layer=LAYERS['supply']))
        self.leader.dxf.end=(20,2.5);self.policy['selections'][0]['target']=dict(kind='axis_source_line',line_handle=self.stub.dxf.handle)
        self.graph['edges'][0]['attribute_paths']=[[[20.,-10.],[20.,0.],[30.,0.]]];self.graph['nodes'][0].update(x=20.,y=-10.)
        legacy=self.legacy_geometry()
        segments=[legacy.Segment('supply',(20.,0.),(30.,0.)),legacy.Segment('supply',(20.,-10.),(20.,0.)),legacy.Segment('supply',(20.,0.),(20.,5.))]
        return legacy,segments

    def test_named_label_on_vent_display_leg_does_not_restore_historical_false_T(self):
        legacy,segments=self.air_vent_fixture();self.doc.modelspace().add_attdef('WHAT',insert=(20,5),text='自动排气阀')
        before=copy.deepcopy(self.graph);row=self.run_collect()['records'][0];self.assertEqual(row['target']['target_graph_coverage'],[])
        cleaned,removals=legacy.remove_auto_air_vent_display_legs(segments,legacy.collect_auto_air_vent_ports(self.doc))
        self.assertEqual(len(removals),1);self.assertEqual(len(cleaned),2);self.assertEqual(removals[0].junction,(20.,0.));self.assertEqual(self.graph,before);self.assertFalse(row['physical_diameter_selected'])

    def test_real_three_arm_source_without_vent_semantics_stays_unresolved(self):
        legacy,segments=self.air_vent_fixture();self.leader.dxf.end=(20,0)
        self.policy['selections'][0]['target']=dict(kind='axis_source_junction',line_handles=[self.pipe.dxf.handle,self.down.dxf.handle,self.stub.dxf.handle])
        _,removals=legacy.remove_auto_air_vent_display_legs(segments,legacy.collect_auto_air_vent_ports(self.doc));self.assertEqual(removals,[])
        proof=self.run_collect()['records'][0]['target'];self.assertTrue(proof['local_topology_recheck_required']);self.assertFalse(proof['connection_accepted'])

    def test_other_semantic_symbol_cannot_authorize_vent_leg_removal(self):
        legacy,segments=self.air_vent_fixture();self.doc.modelspace().add_attdef('WHAT',insert=(20,5),text='压力表')
        _,removals=legacy.remove_auto_air_vent_display_legs(segments,legacy.collect_auto_air_vent_ports(self.doc));self.assertEqual(removals,[])


if __name__=='__main__':unittest.main()
