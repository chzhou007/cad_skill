import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import refresh_inherited_branch_attribute_entries as owner

class InheritedEntryPublication(unittest.TestCase):
    def test_display_only_source_proof_change_gets_a_new_bundle_without_changing_graph_ids(self):
        old={'app.js':'a'*64,'checked-source-connection-display.js':'b'*64};new=dict(old,**{'checked-source-connection-display.js':'c'*64})
        self.assertNotEqual(owner.bundle_identity('parent','proof','implementation',10557,old),owner.bundle_identity('parent','proof','implementation',10557,new))
        self.assertEqual(old,{'app.js':'a'*64,'checked-source-connection-display.js':'b'*64})

    def test_connection_display_keeps_original_raw_status_and_requires_exact_header(self):
        app='    const connection=e.source_wave_omission?"old wave":"old raw missing";\n    header.innerHTML=`<div class="detail-eyebrow"><h2>Pipe details</h2>...`;'
        actual=owner.qualify_connection_display(app)
        self.assertIn('const rawSourceConnection=e.source_wave_omission?"old wave":"old raw missing"',actual)
        self.assertIn('localConnectionDescription(e,data.attribute_value_context,crossViewAttributeCsvValues(e,data.attribute_value_context),zh,rawSourceConnection)',actual)
        with self.assertRaises(ValueError):owner.qualify_connection_display(actual)
        with self.assertRaises(ValueError):owner.qualify_connection_display(app.replace('header.innerHTML','different.innerHTML'))

    def test_live_native_tuple_evidence_matches_the_manifest_boundary_without_losing_source_fields(self):
        h='a'*64;edge=dict(edge_id='E',system='supply',floor_start=2,floor_end=2,start_node_id='T',end_node_id='V',attribute_paths=[[[0,0],[0,-10],[20,-30],[21,-31]]])
        common=dict(edge_id='E',system='supply',path_index=0)
        horizontal=dict(common,segment_index=1,scope_points=[[0,-10],[20,-30]],direction_class='horizontal',native_source_status='single_source_line_covers')
        vertical=dict(common,segment_index=0,scope_points=[[0,0],[0,-10]],nominal_mm=200,
            source='axis11_original_native_caption_T_and_replayed_normalization',raw_source_coverage_not_promoted=True,
            physical_length_mm=None,whole_edge_DN_assigned=False,human_accepted=False,candidate_evidence=[dict(native_XYZ=((0,0,0),(0,-10,0)))])
        branch=dict(axis_edge_id='E',system='supply',floor=2,nominal_mm=200,axis_nodes=['T','V'],axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),
            horizontal_segment_domains=[horizontal],excluded_marker_display_segment=2,axis_T='T',main_arms=['L','R'],main_source_scope_id='PLAN')
        source=dict(path='plan.dxf',sha256=h);plan_graph=dict(path='plan-graph.json',sha256=h);old=[dict(edge_id='E',values={})]
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);effective=root/'old.json';effective.write_bytes(owner.encode(old))
            proof=dict(mode=owner.NATIVE_MODE,complete_current_native_viewer_and_vertical_parents_replayed=True,
                all_previous_source_branch_payloads_exact=True,source_graph_and_original_routes_unchanged=True,
                raw_normalization_gap_never_promoted_to_measured_LINE=True,vertical_values_from_axis11_only=True,
                graph_mutated=False,components_changed=False,human_accepted=False,physical_lengths_assigned=0,individual_device_mappings_assigned=0,
                inputs=dict(viewer_manifest=dict(sha256=h),current_effective=dict(path=str(effective)),received_attribute_proof=dict(path='received.json'),
                    axis_source=dict(sha256=h),axis_graph=dict(sha256=h),provider=dict(sha256=h)),
                records=[branch],new_partial_main_records=[],new_vertical_records=[vertical])
            before=copy.deepcopy(proof);manifest=dict(attributeValueContext=dict(current_rendered_graph_sha256=h))
            objects={str(root/'public/data/manifest.json'):manifest,str(root/'public/data/graph.json'):dict(edges=[edge]),
                'received.json':dict(source_inputs=dict(plan_source=source,plan_graph=plan_graph))}
            with patch.object(owner,'load',side_effect=lambda p:copy.deepcopy(objects[str(p)])),patch.object(owner,'sha',return_value=h):
                context=owner.context_from(root,proof,root/'proof.json',dict(inputs=dict(plan_source_2=source,plan_graph_2=plan_graph)),old)
            self.assertEqual(proof,before)
            self.assertEqual(context,json.loads(owner.encode(context)))
            r=context[owner.CONTEXT]['records'][0]
            self.assertEqual(r['new_axis11_vertical_domains'][0]['candidate_evidence'][0]['native_XYZ'],[[0,0,0],[0,-10,0]])
            self.assertTrue(r['whole_physical_DN_complete'])

    def fixture(self):
        branch=dict(axis_edge_id='B',kind='branch',whole_physical_DN_complete=True,nominal_mm=200,
            horizontal_segment_domains=[{'segment_index':1}],new_axis11_vertical_domains=[{'segment_index':0}])
        partial=dict(axis_edge_id='P',kind='partial_main',whole_physical_DN_complete=False,nominal_mm=200,
            horizontal_segment_domains=[{'segment_index':1}],new_axis11_vertical_domains=[])
        old=[dict(edge_id='B',values=dict(physical_length_mm=None,axis_rule_vertical_DN_segments_json='[]',mapping_id='old')),
             dict(edge_id='P',values=dict(physical_length_mm=None)),dict(edge_id='OTHER',values=dict(diameter_nominal_mm=80,physical_length_mm=7))]
        new=copy.deepcopy(old)
        for row,record in zip(new,[branch,partial]):
            row['values']['inherited_entry_DN_domains_json']=json.dumps(record)
            if record['new_axis11_vertical_domains']:
                row['values']['inherited_entry_vertical_DN_segments_json']=json.dumps(record['new_axis11_vertical_domains'])
        new[0]['values'].update(diameter_nominal_mm=200,diameter_text='DN200',diameter_status='source_verified')
        return old,new,{owner.CONTEXT:dict(records=[branch,partial])}

    def test_three_scalar_cells_are_counted_even_when_old_unknown_keys_were_absent(self):
        old,new,context=self.fixture();d=owner.delta(old,new,context)
        self.assertEqual(d['new_whole_DN_edges'],['B']);self.assertEqual(len(d['old_field_changes']),3)
        self.assertEqual(d['new_axis11_vertical_domains'],1);self.assertEqual(d['partial_main_edges'],['P'])
        self.assertTrue(all(row['before']is None for row in d['old_field_changes']))

    def test_prior_length_source_identity_known_DN_and_unrelated_rows_are_release_blockers(self):
        for index,key,value in [(0,'physical_length_mm',0),(0,'axis_rule_vertical_DN_segments_json','[{}]'),(0,'mapping_id','new'),
                                (1,'diameter_nominal_mm',200),(2,'diameter_nominal_mm',200),(2,'new_unrelated_field',1)]:
            old,new,context=self.fixture();new[index]['values'][key]=value
            with self.assertRaises(ValueError):owner.delta(old,new,context)
        old,new,context=self.fixture();old[0]['values']['diameter_nominal_mm']=80
        with self.assertRaises(ValueError):owner.delta(old,new,context)

    def test_new_vertical_rows_cannot_escape_their_independently_owned_edge(self):
        old,new,context=self.fixture();new[1]['values']['inherited_entry_vertical_DN_segments_json']='[]'
        with self.assertRaises(ValueError):owner.delta(old,new,context)
        old,new,context=self.fixture();new[0]['values']['inherited_entry_vertical_DN_segments_json']='[]'
        with self.assertRaises(ValueError):owner.delta(old,new,context)
        old,new,context=self.fixture();new[2]['values']['inherited_entry_DN_scope_id']='wrong'
        with self.assertRaises(ValueError):owner.delta(old,new,context)

if __name__=='__main__':unittest.main()
