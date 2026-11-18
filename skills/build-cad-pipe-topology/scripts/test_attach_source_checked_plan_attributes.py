import copy,unittest
import test_native_plan_projection_lengths as projection_fixture
from attach_source_checked_plan_attributes import attach,native_local_diameters
from match_source_checked_crossview_paths import selected_snapshot
from native_plan_projection_lengths import unit_evidence


class SourcePlanAttributeTests(unittest.TestCase):
    def fixture(self,many=False):
        doc,plan,p,coverage,_=projection_fixture.fixture()
        parent=dict(nodes=[dict(node_id='A',node_type='tee',floor=2),dict(node_id='B',node_type='equipment',floor=2)],edges=[dict(edge_id='I',start_node_id='A',end_node_id='B',system='supply',attribute_paths=[[[0,0],[0,10]]])],crossViewAttributeFusion={'historical':'preserved'})
        ids=['I']
        if many:
            parent['nodes'].append(dict(node_id='C',node_type='tee',floor=2));parent['edges'][0]['end_node_id']='C'
            parent['edges'].append(dict(edge_id='I2',start_node_id='C',end_node_id='B',system='supply',attribute_paths=[[[0,10],[0,20]]]))
            ids.append('I2')
        record=dict(mapping_id='SC-1',kind='equipment_branch',system='supply',floor=2,plan_edges=['P'],iso_edges=ids,iso_snapshot=selected_snapshot(parent,ids))
        return doc,parent,dict(records=[record]),plan,coverage,unit_evidence(doc,p),{'SC-1':dict(nominal_mm=None,status='plan_diameter_scope_unresolved',plan_candidate=None)}

    def test_old_fusion_is_preserved_while_source_projection_is_added(self):
        doc,parent,mapping,plan,coverage,units,dn=self.fixture();before=copy.deepcopy(parent)
        parent['edges'].append(dict(edge_id='OLD',start_node_id='A',end_node_id='B',system='return',cross_view_attributes={'historical_length':2175.5}))
        out,proof=attach(parent,mapping,plan,coverage,units,dn,{'plan':'S'},'M')
        self.assertEqual(out['edges'][-1],parent['edges'][-1]);self.assertEqual(out['crossViewAttributeFusion'],parent['crossViewAttributeFusion'])
        attrs=out['edges'][0]['cross_view_attributes'];self.assertEqual(attrs['horizontal_projection']['edge_value_mm'],800)
        self.assertIsNone(attrs['diameter']['nominal_mm']);self.assertIsNone(attrs['whole_edge_physical_length_mm'])
        self.assertEqual(len(attrs['axis_vertical_drawing_strokes']),1);self.assertFalse(attrs['axis_vertical_drawing_strokes'][0]['inter_floor']);self.assertIsNone(attrs['axis_vertical_drawing_strokes'][0]['physical_length_mm'])
        self.assertFalse(out['sourceCheckedCrossViewAttributeFusion']['expert_confirmation_claimed']);self.assertNotIn('cross_view_attributes',parent['edges'][0])

    def test_one_to_many_does_not_repeat_route_total_and_stale_snapshot_fails(self):
        doc,parent,mapping,plan,coverage,units,dn=self.fixture(True)
        out,_=attach(parent,mapping,plan,coverage,units,dn,{},'M')
        self.assertTrue(all(e['cross_view_attributes']['horizontal_projection']['edge_value_mm'] is None for e in out['edges']))
        parent['edges'][0]['system']='return'
        with self.assertRaisesRegex(ValueError,'route changed'):attach(parent,mapping,plan,coverage,units,dn,{},'M')

    def test_empty_preexisting_attributes_cannot_be_silently_overwritten(self):
        doc,parent,mapping,plan,coverage,units,dn=self.fixture();parent['edges'][0]['cross_view_attributes']={}
        mapping['records'][0]['iso_snapshot']=selected_snapshot(parent,['I'])
        with self.assertRaisesRegex(ValueError,'overlaps'):attach(parent,mapping,plan,coverage,units,dn,{},'M')

    def test_native_DN_is_only_a_local_observation_and_parentheses_not_length(self):
        doc,parent,mapping,plan,coverage,units,dn=self.fixture();line=doc.modelspace().query('LINE')[0];text=doc.modelspace().add_text('DN80(2.900)',dxfattribs={'insert':(500,110)})
        obs=dict(text={'handle':text.dxf.handle,'text':'DN80(2.900)'},nominal_mm=80,point=[500,100],source_line_handle=line.dxf.handle,status='native_source_local_observation')
        plan['edges'][0]['pipe_diameter']={'observations':[obs]};result=native_local_diameters(doc,plan,mapping['records'][0],coverage)
        self.assertEqual(result['plan_candidate']['nominal_mm'],80);self.assertIsNone(result['nominal_mm']);self.assertFalse(result['selected_physical_diameter'])
        self.assertFalse(result['plan_candidate']['physical_length_from_parentheses'])
        text.dxf.text='DN65'
        with self.assertRaisesRegex(ValueError,'native route evidence'):native_local_diameters(doc,plan,mapping['records'][0],coverage)


if __name__=='__main__':unittest.main()
