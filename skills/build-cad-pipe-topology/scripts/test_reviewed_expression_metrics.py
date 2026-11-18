import copy,unittest
from reviewed_expression_metrics import measure
from native_plan_projection_lengths import unit_evidence
from batch_native_path_coverage import collect
from test_native_plan_projection_lengths import fixture as unit_fixture

def fixture():
    doc,graph,policy,_,_=unit_fixture();m=doc.modelspace()
    e=graph['edges'][0];e.update(start_node_id='A',end_node_id='B',start_floor=2,end_floor=2)
    for a,b in [((900,100),(1300,100)),((1400,100),(2100,100))]:m.add_line(a,b,dxfattribs={'layer':'空调冷冻水供水'})
    graph['edges'].append(dict(edge_id='Q',system='supply',start_node_id='B',end_node_id='C',start_floor=2,end_floor=2,attribute_paths=[[[900,100],[1300,100]],[[1400,100],[2100,100]]]))
    coverage=collect(doc,graph,['P','Q'],'S','G')
    scope=dict(scope_id='range',floor=2,system='supply',status='native_bounded_range_correspondence',views=dict(plan=dict(route=dict(edges=['P','Q'],nodes=['A','B','C']),path_coverage=coverage,source_snapshot=dict(edges=copy.deepcopy(graph['edges'])),junction_failures={},path_failures=[]),iso=dict(route=dict(edges=['I','J','K'],nodes=['X','Y','Z','W']))))
    return scope,graph,unit_evidence(doc,policy)

class ReviewedGroupMetricsTests(unittest.TestCase):
    def test_unequal_route_counts_preserve_unknown_gap_and_per_edge_allocation(self):
        s,g,u=fixture();before=copy.deepcopy((s,g,u));r=measure(s,g,u)
        self.assertEqual(r['known_plan_XY_fragment_sum_mm'],1900)
        self.assertEqual(r['source_checked_route_window'],[-100,2100,-100,1500])
        self.assertEqual(len(r['pieces']),3);self.assertEqual(r['pieces'][-1]['path_index'],1)
        self.assertEqual(len(r['omitted_span_evidence']),1)
        self.assertIsNone(r['complete_group_physical_length_mm']);self.assertIsNone(r['per_axis_edge_length_allocation']);self.assertIsNone(r['per_axis_edge_DN_assignment'])
        self.assertFalse(r['internal_node_identities_assigned']);self.assertEqual((s,g,u),before)
    def test_holds_bad_unit_calibration_and_other_floor_block(self):
        for kind in ['held','units','floor','wave','detail','inline']:
            with self.subTest(kind=kind):
                s,g,u=fixture()
                if kind=='held':s['status']='held_local_source_evidence'
                elif kind=='units':u['status']='unknown'
                elif kind=='floor':g['edges'][0]['start_floor']=3
                else:g['edges'][0][{'wave':'source_wave_omission','detail':'source_view_context','inline':'source_flexible_joints'}[kind]]={'unverified':True}
                s['views']['plan']['source_snapshot']['edges']=copy.deepcopy(g['edges'])
                with self.assertRaises(ValueError):measure(s,g,u)
    def test_ambiguous_missing_nested_stale_or_extra_fragments_block(self):
        for kind in ['ambiguous','missing','nested','stale','extra','repeated']:
            with self.subTest(kind=kind):
                s,g,u=fixture();a=s['views']['plan']['path_coverage']['edges'][0];segment=a['segments'][0]
                if kind=='ambiguous':segment['witnesses'].append(copy.deepcopy(segment['witnesses'][0]))
                elif kind=='missing':segment['status']='no_witness_in_scoped_search'
                elif kind=='nested':segment['witnesses'][0]['scope']='decomposed_selected_insert'
                elif kind=='stale':g['edges'][0]['attribute_paths'][0][0][0]+=1
                elif kind=='extra':a['segments'].append(copy.deepcopy(segment))
                else:s['views']['plan']['route']['edges'][1]='P'
                with self.assertRaises(ValueError):measure(s,g,u)
    def test_route_node_order_and_source_system_are_not_inferred_from_equal_lengths(self):
        s,g,u=fixture();s['views']['plan']['route']['nodes'][1]='wrong'
        with self.assertRaises(ValueError):measure(s,g,u)
        s,g,u=fixture();s['system']='return'
        with self.assertRaises(ValueError):measure(s,g,u)

if __name__=='__main__':unittest.main()
