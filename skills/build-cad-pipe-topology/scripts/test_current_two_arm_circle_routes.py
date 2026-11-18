import copy,unittest,tempfile,json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from ezdxf.math import Matrix44
from test_normalize_two_arm_circle_continuity import fixture,transform
from current_two_arm_circle_routes import rebuild,circle_omissions,inherit

class Tests(unittest.TestCase):
    def test_adopted_provider_key_order_is_not_a_value_difference_after_native_replay(self):
        from rebuild_current_two_arm_circle_routes import checked_provider
        from confirm_crossview_paths import sha
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);proof=root/'anchored-plan-metrics.json';original=root/'original.json';actual=root/'actual.json';manifest=root/'viewer/public/data/manifest.json';manifest.parent.mkdir(parents=True)
            original.write_text('{}',encoding='utf8');proof.write_text(json.dumps({'inputs':{'provider':{'path':str(original)}}}),encoding='utf8');manifest.write_text(json.dumps({'sourceHashes':{'anchored_native_plan_metrics':sha(proof)}}),encoding='utf8');actual.write_text(json.dumps({'a':1,'b':2},sort_keys=True),encoding='utf8')
            def run(cmd,**kwargs):
                p=Path(cmd[-1]);p.mkdir();(p/'anchored-plan-metrics.json').write_bytes(proof.read_bytes());return SimpleNamespace(returncode=0,stderr='')
            m=dict(inputs=dict(metric_proof={'path':str(proof),'sha256':sha(proof)},provider_snapshot={'path':str(root/'snapshot.json')},viewer_manifest={'path':str(manifest)},provider={'path':str(actual)}),parent_replay_cwd=str(root))
            with patch('rebuild_current_two_arm_circle_routes.subprocess.run',side_effect=run),patch('reapply_anchored_plan_metrics.inventory_from',return_value={'b':2,'a':1}),patch('refresh_anchored_native_plan_metrics.effective_attributes',return_value=[]):self.assertEqual(checked_provider(m),{'a':1,'b':2})
            with patch('rebuild_current_two_arm_circle_routes.subprocess.run',side_effect=run),patch('reapply_anchored_plan_metrics.inventory_from',return_value={'b':3,'a':1}),patch('refresh_anchored_native_plan_metrics.effective_attributes',return_value=[]):
                with self.assertRaisesRegex(ValueError,'provider differs'):checked_provider(m)

    def test_batch_reuses_original_native_rule_conserves_components_and_unknown_gap(self):
        for angle,mirror in[(0,1),(37,1),(90,-1),(270,-1)]:
            import math
            doc,g,handles,rows=fixture();transform(doc,g,Matrix44.chain(Matrix44.scale(mirror,1,1),Matrix44.z_rotate(math.radians(angle))));before=copy.deepcopy(g)
            out,assigned,proof=rebuild(doc,g,rows);self.assertEqual(g,before);self.assertEqual(proof['counts']['qualified'],1);self.assertEqual(proof['counts']['retired_nonphysical_endpoints'],2);self.assertEqual(len(assigned),2)
            edge=out['edges'][0];gap=[r['endpoint'][:2]for r in proof['records'][0]['contacts']];omission=circle_omissions(out,edge,[gap],'return')[0];self.assertIsNone(omission['physical_connector_length_mm']);self.assertEqual(edge['physical_length'],'unknown');self.assertEqual(proof['physical_Ts_added'],0)
            with self.assertRaises(ValueError):circle_omissions(out,edge,[[[v+1 for v in p]for p in gap]],'return')
            with self.assertRaises(ValueError):circle_omissions(out,edge,[gap],'supply')

    def test_known_boundaries_crossing_third_arm_colour_and_Z_stay_held(self):
        for kind in('boundary','third_arm','colour','Z','supply'):
            doc,g,handles,rows=fixture();lines=list(doc.modelspace().query('LINE'))
            if kind=='boundary':g['boundary_anchors']=[dict(source_marker_handles=handles)]
            elif kind=='third_arm':doc.modelspace().add_line((0,0),(1000,0),dxfattribs={'layer':'空调冷冻水回水'})
            elif kind=='colour':lines[1].dxf.color=1
            elif kind=='Z':lines[0].dxf.start=(0,1000,1)
            else:lines[1].dxf.layer='空调冷冻水供水'
            out,assigned,proof=rebuild(doc,g,rows)
            with self.subTest(kind=kind):self.assertEqual(out,g);self.assertEqual(assigned,rows);self.assertEqual(proof['counts']['held'],1)

    def test_already_connected_or_missing_circle_never_generates_a_new_connection(self):
        doc,g,handles,rows=fixture();doc.modelspace().delete_entity(doc.entitydb[handles[0]]);out,assigned,proof=rebuild(doc,g,rows);self.assertEqual(out,g);self.assertEqual(proof['counts']['qualified'],0)
        doc,g,handles,rows=fixture();g['nodes'][1]['subtype']='actual_equipment_port';out,assigned,proof=rebuild(doc,g,rows);self.assertEqual(out,g);self.assertEqual(proof['counts']['candidates'],0)

    def test_provider_inheritance_preserves_all_old_metrics_and_member_ids(self):
        observation={'mapping_id':'OLD','domain':'member'}
        original=dict(records=[dict(edge_id='OLD',has_existing_correspondence=True,correspondence_observations=[observation]),dict(edge_id='NEW',classification='mixed_horizontal_vertical',has_existing_correspondence=False,correspondence_observations=[])],ordinary_junction_mappings={'3':{'T':'A'}},remaining_horizontal_attributes=[{'edge_id':'H','complete_centerline':True,'next_scope':'DN_conflict'}],member_domain_observations=[{'member_edge_id':'MEMBER:OLD'}],counts={},current_horizontal_frontier={'records':[]},current_component_inventory={'physical_resistance':None},anchored_metric_attribute_observations=[{'axis_edge_id':'H','complete_horizontal_centerline_mm':100}],new_member_external_records=[{'mapping_id':'HISTORY'}])
        record=dict(mapping_id='NEW-RELATION',kind='member_to_ordinary_external_route',axis_edge_id='NEW',plan_member_edge_id='MEMBER:NEW',plan_source_edge_id='PLAN-NEW',member_node_id='MEMBER:START',plan_remote='T',axis_remote='A',system='return',floor=3,plan_attribute_paths=[[[0,0],[1,0]]],physical_values_assigned=0,attribute_adoption_allowed=False,human_accepted=False)
        plan=dict(nodes=[dict(node_id='T',node_type='tee')]);local=dict(nodes=[{'node_id':'MEMBER:START'}],edges=[],external_ports=[{'axis_edge_id':'NEW'}]);before=copy.deepcopy(original)
        result,reading=inherit(original,[record],local,plan,{'3':{'reading_graph_sha256':'HASH'}});self.assertEqual(original,before);self.assertEqual(result['new_member_external_records'],before['new_member_external_records']);self.assertEqual(result['anchored_metric_attribute_observations'],before['anchored_metric_attribute_observations']);self.assertEqual(result['records'][0],before['records'][0]);self.assertEqual(result['remaining_horizontal_attributes'],before['remaining_horizontal_attributes']);self.assertEqual(result['counts']['existing_correspondence_edges'],2);self.assertEqual(len(reading['edges']),1)
        changed=dict(record,physical_values_assigned=1)
        with self.assertRaises(ValueError):inherit(original,[changed],local,plan,{})
if __name__=='__main__':unittest.main()
