import copy
import unittest

import attach_known_junction_main_plan_attributes as owner
import match_known_junction_direct_mains as mapping_owner
import test_match_known_junction_direct_mains as fixture_module


def fixture():
    graphs,parents=fixture_module.fixture()
    for view in graphs:
        for edge in graphs[view]['edges']:edge.update(start_floor=2,end_floor=2)
    for row in parents:
        for view in graphs:row[view+'_snapshot']=mapping_owner.selected_snapshot(graphs[view],row[view+'_edges'])
    rows,_=mapping_owner.discover(graphs,parents,2);rows[0]['mapping_id']='NEW-1'
    local=graphs['iso'];parent=copy.deepcopy(local)
    parent['metadata']=dict(hil_ready=False,review_status='old_pending')
    parent['edges'][0]['cross_view_attributes']=dict(legacy='retain')
    parent['edges'][1][owner.FIELD]=dict(nominal_mm=80,legacy='prior_anchored_main')
    parent['nodes'][-1]['source_external_destination_context']=dict(destination='室外冷冻站',external_connectivity='unknown')
    parent['prior_stage']=dict(records=['retain all old rules'])
    mapping=dict(floor=2,records=rows,plan_graph_sha256='1'*64,iso_graph_sha256='2'*64,source_sha256=dict(plan='3'*64,iso='4'*64))
    values=copy.deepcopy(rows[0]);values.update(whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,
        diameter=dict(edge_id='PMAIN',system='supply',nominal_mm=200,human_accepted=False),
        horizontal_projection=dict(status='native_plan_horizontal_projection_partial_length',value_mm=100,
            pieces=[dict(plan_edge='PMAIN',path_index=0,segment_index=0,points=[[100,0],[200,0]],length_mm=100)],installed_whole_edge_length_mm=None))
    attributes=dict(mode=owner.ATTRIBUTE_MODE,status='native_direct_main_plan_DN_XY_source_checked_not_fused',records=[values],
        mapping_sha256='5'*64,graph_sha256='1'*64,source_sha256='3'*64,local_graphs_mutated=False,physical_values_fused=False,human_accepted=False)
    hashes=dict(mapping='5'*64,parent='6'*64,attributes='7'*64)
    return parent,local,mapping,attributes,hashes


class FusionTests(unittest.TestCase):
    def test_complete_parent_restores_exactly_including_existing_anchored_and_destination_evidence(self):
        p,l,m,a,h=fixture();before=copy.deepcopy((p,l,m,a,h))
        g,stage=owner.append(p,l,m,a,h,[0,45,135])
        self.assertEqual(owner.restore(g,stage,p),p);self.assertEqual((p,l,m,a,h),before)
        self.assertEqual(g['nodes'],p['nodes']);self.assertEqual(g['prior_stage'],p['prior_stage'])
        self.assertEqual(g['edges'][1][owner.FIELD]['nominal_mm'],80)
        target=next(e for e in g['edges'] if e['edge_id']=='IMAIN')[owner.FIELD]
        self.assertEqual(target['nominal_mm'],200);self.assertIsNone(target['installed_whole_edge_length_mm'])
        self.assertFalse(target['related_HIL_confirmation_inherited'])

    def test_inline_projection_excludes_interior_and_keeps_full_route_unknown(self):
        p,l,m,a,h=fixture();metric=a['records'][0]['horizontal_projection']
        metric.update(status='native_plan_pipe_XY_inline_interiors_unknown',joint_graphic_spans_added=False,inline_joint_interior_length_mm=None)
        g,_=owner.append(p,l,m,a,h,[0]);target=next(e for e in g['edges'] if e['edge_id']=='IMAIN')[owner.FIELD]
        self.assertIsNone(target['complete_horizontal_centerline_route_mm']);self.assertEqual(target['horizontal_projection']['value_mm'],100)

    def test_inline_span_cannot_be_added_as_a_measured_joint_interior(self):
        p,l,m,a,h=fixture();a['records'][0]['horizontal_projection'].update(status='native_plan_pipe_XY_inline_interiors_unknown',joint_graphic_spans_added=True,inline_joint_interior_length_mm=300)
        with self.assertRaisesRegex(ValueError,'Inline marker'):owner.append(p,l,m,a,h,[0])

    def test_existing_target_attribute_is_not_overwritten(self):
        p,l,m,a,h=fixture();p['edges'][-1]['cross_view_attributes']=dict(keep='existing')
        with self.assertRaisesRegex(ValueError,'overlaps'):owner.append(p,l,m,a,h,[0])

    def test_unrelated_parent_pipe_geometry_change_is_rejected(self):
        p,l,m,a,h=fixture();p['edges'][0]['attribute_paths'][0][0][0]+=1
        with self.assertRaisesRegex(ValueError,'geometry or component'):owner.append(p,l,m,a,h,[0])

    def test_unrelated_component_inventory_change_is_rejected(self):
        p,l,m,a,h=fixture();p['edges'][0]['equipment_counts']=dict(ball_valve=9)
        with self.assertRaisesRegex(ValueError,'geometry or component'):owner.append(p,l,m,a,h,[0])

    def test_selected_node_identity_change_is_rejected(self):
        p,l,m,a,h=fixture();p['nodes'][0]['x']+=1
        with self.assertRaisesRegex(ValueError,'snapshot'):owner.append(p,l,m,a,h,[0])

    def test_cross_floor_or_vertical_axis_scope_is_not_a_horizontal_main(self):
        for change in ('floor','direction'):
            p,l,m,a,h=fixture()
            if change=='floor':
                for g in (p,l):g['edges'][-1]['end_floor']=3
            else:
                for g in (p,l):
                    g['nodes'][1].update(x=100,y=100);g['edges'][-1]['attribute_paths']=[[[100,0],[100,100]]]
            m['records'][0]['iso_snapshot']=mapping_owner.selected_snapshot(l,['IMAIN'])
            with self.subTest(change=change),self.assertRaises(ValueError):owner.append(p,l,m,a,h,[0,45])

    def test_metric_total_must_equal_unique_native_pieces(self):
        for change in ('total','duplicate'):
            p,l,m,a,h=fixture();metric=a['records'][0]['horizontal_projection']
            if change=='total':metric['value_mm']+=1
            else:metric['pieces']*=2;metric['value_mm']*=2
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'pieces'):owner.append(p,l,m,a,h,[0])

    def test_mapping_and_attribute_source_versions_must_match(self):
        for field in ('mapping_sha256','graph_sha256','source_sha256'):
            p,l,m,a,h=fixture();a[field]='f'*64
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'source version'):owner.append(p,l,m,a,h,[0])

    def test_repeated_fusion_and_duplicated_edge_writer_block(self):
        p,l,m,a,h=fixture();g,_=owner.append(p,l,m,a,h,[0])
        with self.assertRaisesRegex(ValueError,'already composed'):owner.append(g,l,m,a,h,[0])
        p,l,m,a,h=fixture();r=copy.deepcopy(m['records'][0]);r['mapping_id']='OTHER';m['records'].append(r)
        v=copy.deepcopy(a['records'][0]);v['mapping_id']='OTHER';a['records'].append(v)
        with self.assertRaises(ValueError):owner.append(p,l,m,a,h,[0])

    def test_restore_detects_unrelated_node_context_or_edge_change(self):
        for change in ('destination','legacy'):
            p,l,m,a,h=fixture();g,stage=owner.append(p,l,m,a,h,[0])
            if change=='destination':g['nodes'][-1]['source_external_destination_context']['destination']='OTHER'
            else:g['edges'][0]['cross_view_attributes']['legacy']='changed'
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'prior nodes'):owner.restore(g,stage,p)

    def test_restore_rejects_promoted_human_or_connection_state(self):
        for key,value in [('human_accepted',True),('related_HIL_confirmation_inherited',True),('new_connections_added',1)]:
            p,l,m,a,h=fixture();g,stage=owner.append(p,l,m,a,h,[0]);stage[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):owner.restore(g,stage,p)


if __name__=='__main__':unittest.main()
