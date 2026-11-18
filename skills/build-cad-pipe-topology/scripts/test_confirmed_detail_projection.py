import copy,hashlib,unittest
from unittest.mock import patch
from confirm_crossview_paths import encode
from confirmed_detail_projection import projection,STATUS,ALLOCATION
from reconstruct_sideview_equipment_ownership import MODE
from test_native_plan_projection_lengths import fixture as metric_fixture
from test_fuse_plan_DN_scopes import PlanDNScopeFusionTests
from fuse_plan_DN_scopes import apply as fuse
from attach_source_checked_plan_attributes import metric_context


def fixture():
    doc,graph,policy,coverage,_=metric_fixture();state={'records':[{'source':'confirmed original answer'}]};digest=hashlib.sha256(encode(state)).hexdigest()
    graph.update(metadata={'source_sha256':'S'},confirmedSideviewCanonicalization=state,
        sourceSideviewEquipmentOwnership=dict(mode=MODE,source_sha256='S',input_graph_sha256='P',human_accepted=False,physical_ports_verified=False,detail_edge_ids=['P']))
    graph['edges'][0].update(start_floor=2,end_floor=2,source_view_context=dict(kind='confirmed_detail_view',coordinate_domain='native_detail_drawing',source_sha256='S',input_graph_sha256='P',confirmed_alias_root_sha256=digest,physical_length_from_drawing_span=False,metric_verified_by_this_stage=False))
    return doc,graph,copy.deepcopy(coverage),dict(plan_edges=['P'],system='supply',floor=2),dict(plan='S',plan_graph='a'*64)


class ConfirmedDetailProjectionTests(unittest.TestCase):
    def test_native_span_is_preserved_as_drawing_evidence_and_never_mm(self):
        doc,g,c,r,s=fixture();before=copy.deepcopy(g)
        result=projection(g,c,r,{},s,allow_detail=True)
        self.assertEqual(result['status'],STATUS);self.assertIsNone(result['value_mm']);self.assertEqual(result['pieces'][0]['drawing_span_native_units'],800)
        self.assertIsNone(result['pieces'][0]['physical_length_mm']);self.assertNotIn('length_mm',result['pieces'][0]);self.assertEqual(g,before)

    def test_explicit_mode_cannot_hide_stale_or_mixed_source_scope(self):
        for variant in ('mode','source','alias','floor','physical','units','coverage','path','root','mixed'):
            doc,g,c,r,s=fixture();allow=True;e=g['edges'][0]
            if variant=='mode':allow=False
            elif variant=='source':e['source_view_context']['source_sha256']='OTHER'
            elif variant=='alias':g['confirmedSideviewCanonicalization']['changed']=True
            elif variant=='floor':e['end_floor']=3
            elif variant=='physical':e['source_view_context']['physical_length_from_drawing_span']=True
            elif variant=='units':e['source_view_context']['metric_verified_by_this_stage']=True
            elif variant=='coverage':c['edges'][0]['segments'][0]['witnesses'].append(copy.deepcopy(c['edges'][0]['segments'][0]['witnesses'][0]))
            elif variant=='path':e['attribute_paths'][0][0][0]+=5
            elif variant=='root':g['sourceSideviewEquipmentOwnership']['human_accepted']=True
            else:e.pop('source_view_context');other=copy.deepcopy(e);other['edge_id']='P2';other['source_view_context']={};g['edges'].append(other);r['plan_edges'].append('P2');c['edges'].append(dict(edge_id='P2'))
            with self.subTest(variant=variant),self.assertRaises((ValueError,KeyError)):projection(g,c,r,{},s,allow_detail=allow)

    def test_detail_only_entry_does_not_borrow_global_dimensions_as_a_scale(self):
        doc,g,c,r,s=fixture()
        with patch('attach_source_checked_plan_attributes.unit_evidence',side_effect=AssertionError('detail units must not be used')):
            units,allow=metric_context(doc,dict(allow_confirmed_detail_topology_only=True),g,dict(records=[r]))
            self.assertFalse(units['physical_units_applied']);self.assertTrue(allow)
            with self.assertRaises(ValueError):metric_context(doc,{},g,dict(records=[r]))

    def test_whole_main_DN_is_independent_of_unmeasured_detail_length(self):
        inputs=PlanDNScopeFusionTests().fixture();axis,mapping,plan,evidence=inputs;record=mapping['records'][0];edge=axis['edges'][0]
        plan['edges'][0]['source_view_context']={'kind':'confirmed_detail_view'}
        evidence.update(source_sha256='S',graph_sha256='G')
        metric=dict(status=STATUS,value_mm=None,edge_value_mm=None,allocation=ALLOCATION,
            detail_context=dict(plan_edges=['P'],plan_source_sha256='S',plan_graph_sha256='G',physical_units_applied=False,human_accepted=False))
        edge['cross_view_attributes']['horizontal_projection']=metric;before=copy.deepcopy(inputs)
        out,proof=fuse(*inputs,'b'*64,[0,45,135]);attr=out['edges'][0]['cross_view_attributes']
        self.assertEqual(attr['diameter']['nominal_mm'],80);self.assertTrue(attr['diameter']['selected_physical_diameter'])
        self.assertEqual(attr['diameter']['status'],'source_checked_whole_horizontal_main_DN_length_unknown')
        self.assertIsNone(attr['whole_edge_physical_length_mm']);self.assertFalse(proof[0]['whole_main_DN_and_centerline_route']);self.assertTrue(proof[0]['whole_main_DN_length_unknown']);self.assertEqual(inputs,before)
        metric['edge_value_mm']=0
        with self.assertRaises(ValueError):fuse(*inputs,'b'*64,[0,45,135])


if __name__=='__main__':unittest.main()
