import copy,unittest
import test_attach_paired_plan_scope_attributes as fixtures
from attach_refined_paired_plan_attributes import attach_checked_scope,BASIS
from refine_paired_service_path_correspondence import MODE
from match_source_checked_crossview_paths import selected_snapshot


class RefinedPairedAttributeTests(unittest.TestCase):
    def data(self):
        x=fixtures.PairedAttributeScopeTests().data();parent,mapping,plan,coverage,units,dn,evidence=x
        mapping.update(mode=MODE,status='source_checked_junction_refined_correspondence_attributes_pending',physical_values_fused=False,
            evidence=dict(native_junction_correspondence=dict(records=[dict(complete=True,matches=[dict(junction_mapping_id='PJ1')])])))
        record=mapping['records'][0];record.update(kind='main_between_matched_junctions',junction_correspondence_ids=['PJ1'])
        parent['nodes'][1]['node_type']='tee';parent['edges'][0].update(attribute_paths=[[[0,0],[10,10]]],floor_start=2,floor_end=2)
        plan['nodes']=[dict(node_id='A',node_type='tee',floor=2),dict(node_id='B',node_type='tee',floor=2)]
        plan['edges'][0].update(start_node_id='A',end_node_id='B',floor_start=2,floor_end=2)
        record['iso_snapshot']=selected_snapshot(parent,['I'])
        return x
    def run_case(self,x):
        parent,mapping,plan,coverage,units,dn,evidence=x
        return attach_checked_scope(parent,mapping,plan,coverage,units,dn,{},'M',evidence,'a'*64,[0,45,135])
    def test_generic_network_T_route_uses_plan_length_and_preserves_truthful_kind(self):
        x=self.data();before=copy.deepcopy(x);out,_,proof=self.run_case(x);self.assertEqual(x,before)
        a=out['edges'][0]['cross_view_attributes'];self.assertEqual(a['mapping_kind'],'main_between_matched_junctions')
        self.assertEqual(a['mapping_basis'],BASIS);self.assertEqual(a['junction_correspondence_ids'],['PJ1'])
        self.assertEqual(a['whole_edge_physical_length_mm'],800);self.assertEqual(a['diameter']['nominal_mm'],80)
        self.assertEqual(proof[0]['mapping_kind'],'main_between_matched_junctions');self.assertFalse(a['physical_ports_verified'])
    def test_split_mapping_assigns_different_native_plan_lengths_instead_of_repeating_total(self):
        x=self.data();parent,mapping,plan,coverage,units,dn,evidence=x
        parent['nodes'].append(dict(node_id='C',node_type='tee',floor=2));parent['edges'][0].update(end_node_id='C',attribute_paths=[[[0,0],[10,10]]])
        parent['edges'].append(dict(parent['edges'][0],edge_id='I2',start_node_id='C',end_node_id='B',attribute_paths=[[[10,10],[20,20]]]))
        plan['nodes'].append(dict(node_id='C',node_type='tee',floor=2));plan['edges'][0].update(end_node_id='C',attribute_paths=[[[100,100],[400,100]]])
        plan['edges'].append(dict(plan['edges'][0],edge_id='P2',start_node_id='C',end_node_id='B',attribute_paths=[[[400,100],[900,100]]]))
        original=copy.deepcopy(coverage['edges'][0]);coverage['edges']=[];mapping['records']=[]
        for i,(pe,ae) in enumerate(zip(plan['edges'],parent['edges'])):
            segment=copy.deepcopy(original['segments'][0]);segment.update(start=pe['attribute_paths'][0][0],end=pe['attribute_paths'][0][1],drawing_length=[300,500][i])
            coverage['edges'].append(dict(original,edge_id=pe['edge_id'],segments=[segment]))
            mid='J'+str(i);mapping['records'].append(dict(mapping_id=mid,kind='main_between_matched_junctions',junction_correspondence_ids=['PJ1'],system='supply',floor=2,
                plan_edges=[pe['edge_id']],iso_edges=[ae['edge_id']],iso_snapshot=selected_snapshot(parent,[ae['edge_id']])))
            dn[mid]=copy.deepcopy(dn['SC-1'])
        evidence['records']=[dict(evidence['records'][0],edge_id=e['edge_id'],scope_paths=copy.deepcopy(e['attribute_paths'])) for e in plan['edges']]
        out,_,_=self.run_case(x);lengths=[e['cross_view_attributes']['whole_edge_physical_length_mm'] for e in out['edges']]
        self.assertEqual(lengths,[300,500]);self.assertEqual(sum(lengths),800)
    def test_no_junction_identity_fake_equipment_or_already_composed_parent_is_rejected(self):
        for case in ('missing','unproved','fake_equipment','composed','old_mode'):
            x=self.data();parent,mapping,_,_,_,_,_=x
            if case=='missing':mapping['records'][0].pop('junction_correspondence_ids')
            elif case=='unproved':mapping['records'][0]['junction_correspondence_ids']=['OTHER']
            elif case=='fake_equipment':mapping['records'][0]['endpoint_equipment_ids']=['A','B']
            elif case=='composed':parent['pairedServiceCrossViewAttributeFusion']={'old':True}
            else:mapping['mode']='old'
            with self.subTest(case=case),self.assertRaises(ValueError):self.run_case(x)
    def test_plumb_or_wrong_floor_T_cannot_become_complete_horizontal_length(self):
        for case in ('plumb','floor','review'):
            x=self.data();parent,mapping,_,_,_,_,_=x
            if case=='plumb':parent['edges'][0]['attribute_paths']=[[[0,0],[0,20]]]
            elif case=='floor':parent['nodes'][1]['floor']=3
            else:parent['nodes'][1]['review_required']=True
            mapping['records'][0]['iso_snapshot']=selected_snapshot(parent,['I'])
            out,_,_=self.run_case(x);a=out['edges'][0]['cross_view_attributes']
            self.assertIsNone(a['whole_edge_physical_length_mm']);self.assertIsNone(a['diameter']['nominal_mm'])


if __name__=='__main__':unittest.main()
