import copy,json,tempfile,unittest
from pathlib import Path
from refresh_plan_crossover_centrelines import delta,provider_from,context_from,NATIVE_MODE,sha,encode
class CrossoverProjectionPublicationTests(unittest.TestCase):
    def fixture(self):
        r=dict(axis_edge_id='E',complete_horizontal_centerline_projection_mm=6250,plan_source_sha256='S');c=dict(plan_crossover_centrelines=dict(records=[r]));old=[dict(edge_id='E',values=dict(diameter_nominal_mm=150,old_fragment_length=5932.6,installed_length=None)),dict(edge_id='OTHER',values={'old':'same'})];new=copy.deepcopy(old);new[0]['values'].update(plan_crossover_complete_XY_centerline_mm=6250,plan_crossover_centerline_evidence_json=json.dumps(r),plan_crossover_centerline_source_sha256='S');return old,new,c
    def test_old_DN_partial_and_installed_lengths_are_exact(self):
        old,new,c=self.fixture();r=delta(old,new,c);self.assertEqual(r['new_complete_XY_centrelines'],1);self.assertEqual(r['new_installed_lengths'],0)
        for field in('diameter_nominal_mm','old_fragment_length','installed_length'):
            a,b,c=self.fixture();b[0]['values'][field]=0
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'historical'):delta(a,b,c)
    def test_absent_or_wrong_new_projection_fails(self):
        for field,v in [('plan_crossover_complete_XY_centerline_mm',0),('plan_crossover_centerline_evidence_json','{}'),('plan_crossover_centerline_source_sha256','other')]:
            a,b,c=self.fixture();b[0]['values'][field]=v
            with self.subTest(field=field),self.assertRaises(ValueError):delta(a,b,c)
    def test_native_tuple_profiles_use_actual_JSON_transport_before_export_comparison(self):
        with tempfile.TemporaryDirectory()as tmp:
            parent=Path(tmp);data=parent/'public/data';data.mkdir(parents=True);edge=dict(edge_id='E',system='return',start_node_id='T1',end_node_id='T2',floor_start=3,floor_end=3,attribute_paths=[[[0,0],[1,1]]]);gp=data/'graph.json';gp.write_bytes(encode(dict(edges=[edge])));mp=data/'manifest.json';mp.write_bytes(encode(dict(bundleId='CURRENT',attributeValueContext=dict(current_rendered_graph_sha256=sha(gp)))));source=parent/'source.json';source.write_text('{}',encoding='utf8');metric=dict(complete_horizontal_centerline_projection_mm=6250,crossover_projections=[dict(horizontal_projection_mm=350)],measurement_kind='floor_plan_complete_XY_centerline_projection_not_installed_length');row=dict(axis_edge_id='E',system='return',axis_nodes=['T1','T2'],axis_attribute_paths=edge['attribute_paths'],floor=3,complete_horizontal_centerline_projection_mm=6250,metric=metric,installed_length_mm=None,net_pipe_cut_length_mm=None,related_HIL_confirmation_inherited=False,DN_changed=False,component_profiles=dict(plan=[('ball_valve',2)],axis=[('ball_valve',2)]));proof=dict(mode=NATIVE_MODE,complete_original_member_batch_replayed=True,old_complete_lengths_not_targeted=True,DN_values_assigned=0,vertical_values_assigned=0,installed_lengths_assigned=0,physical_gap_lengths_assigned=0,source_graphs_mutated=False,human_accepted=False,inputs=dict(parent_viewer_manifest=dict(path=str(mp),sha256=sha(mp)),axis_graph=dict(path=str(source),sha256=sha(source))),parent_bundle_id='CURRENT',records=[row],counts=dict(new_complete_XY_projections=1));result=context_from(parent,proof,source)
            self.assertEqual(result,json.loads(encode(result)));self.assertEqual(result['plan_crossover_centrelines']['records'][0]['component_profiles']['plan'],[['ball_valve',2]])
    def test_complete_provider_retains_correspondences_vertical_values_and_old_frontier_history(self):
        old=dict(counts=dict(pure_horizontal_complete_centerline=244,pure_horizontal_complete_DN_and_centerline=228,pure_horizontal_remaining_attributes=70,horizontal_next_scopes={'old_scope':1},all_current_vertical_DN_domains=377),records=[{'original_correspondence':'same'}],remaining_horizontal_attributes=[dict(edge_id='E',complete_centerline=False,known_whole_DN=150,next_scope='old_scope')],all_current_vertical_DN_domains=377)
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp)/'p.json';p.write_text(json.dumps(old),encoding='utf8');proofpath=Path(tmp)/'proof.json';proofpath.write_text('{}',encoding='utf8');proof=dict(inputs=dict(parent_provider=dict(path=str(p))),records=[dict(axis_edge_id='E')]);result=provider_from(proof,proofpath)
            self.assertEqual(result['counts']['pure_horizontal_complete_centerline'],245);self.assertEqual(result['counts']['pure_horizontal_complete_DN_and_centerline'],229);self.assertEqual(result['remaining_horizontal_attributes'],[]);self.assertEqual(result['records'],old['records']);self.assertEqual(result['all_current_vertical_DN_domains'],377);self.assertEqual(result['history_before_plan_crossover_centrelines']['target_frontiers'],old['remaining_horizontal_attributes']);self.assertEqual(json.loads(p.read_text()),old)
if __name__=='__main__':unittest.main()
