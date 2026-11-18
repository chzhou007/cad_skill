import copy,unittest
import test_attach_source_checked_plan_attributes as fixtures
from attach_paired_plan_scope_attributes import attach_checked_scope,BASIS
from match_paired_service_crossview_paths import MODE
from match_source_checked_crossview_paths import selected_snapshot


class PairedAttributeScopeTests(unittest.TestCase):
    def data(self,many=False):
        doc,parent,mapping,plan,coverage,units,dn=fixtures.SourcePlanAttributeTests().fixture(many)
        mapping.update(mode=MODE,status='source_checked_paired_service_correspondence_attributes_pending',human_accepted=False,local_graphs_mutated=False)
        evidence=dict(records=[dict(edge_id='P',system='supply',scope_paths=copy.deepcopy(plan['edges'][0]['attribute_paths']),nominal_mm=80,
            scope='native_plan_drawn_pipe_paths_only',human_accepted=False,lineage=[dict(source='native')])])
        return parent,mapping,plan,coverage,units,dn,evidence
    def run_case(self,values):
        parent,mapping,plan,coverage,units,dn,evidence=values
        return attach_checked_scope(parent,mapping,plan,coverage,units,dn,{},'M',evidence,'a'*64,[0,45,135])
    def test_branch_gets_drawn_plan_DN_and_projection_without_inventing_connector(self):
        x=self.data();before=copy.deepcopy(x);out,proof,dn=self.run_case(x);self.assertEqual(x,before)
        a=out['edges'][0]['cross_view_attributes'];self.assertEqual(a['mapping_basis'],BASIS);self.assertEqual(a['diameter']['plan_drawn_nominal_mm'],80)
        self.assertIsNone(a['diameter']['nominal_mm']);self.assertIsNone(a['whole_edge_physical_length_mm']);self.assertEqual(a['horizontal_projection']['edge_value_mm'],800)
        self.assertTrue(out['sourceCheckedCrossViewAttributeFusion']['independent_scope_requires_composition'])
    def test_main_uses_native_plan_length_not_axis_stroke(self):
        x=self.data();parent,mapping,plan,_,_,_,_=x;record=mapping['records'][0];record['kind']='main_between_equipment_branches'
        parent['nodes'][1]['node_type']='tee';parent['edges'][0].update(attribute_paths=[[[0,0],[10,10]]],floor_start=2,floor_end=2)
        plan['nodes']=[dict(node_id='A',node_type='tee',floor=2),dict(node_id='B',node_type='tee',floor=2)]
        plan['edges'][0].update(start_node_id='A',end_node_id='B',floor_start=2,floor_end=2);record['iso_snapshot']=selected_snapshot(parent,['I'])
        out,_,_=self.run_case(x);a=out['edges'][0]['cross_view_attributes'];self.assertEqual(a['diameter']['nominal_mm'],80);self.assertEqual(a['whole_edge_physical_length_mm'],800)
    def test_unallocated_route_length_not_repeated_per_axis_edge(self):
        x=self.data(True);out,_,_=self.run_case(x)
        self.assertTrue(all(e['cross_view_attributes']['horizontal_projection']['edge_value_mm'] is None for e in out['edges']))
        self.assertTrue(all(e['cross_view_attributes']['whole_edge_physical_length_mm'] is None for e in out['edges']))
    def test_legacy_proof_composed_parent_or_overlapping_writer_is_rejected(self):
        for mode in ('legacy','composed','occupied'):
            x=self.data()
            if mode=='legacy':x[1]['mode']='not-paired'
            elif mode=='composed':x[0]['sourceCheckedCrossViewAttributeFusion']={'old':True}
            else:
                x[0]['edges'][0]['cross_view_attributes']={};x[1]['records'][0]['iso_snapshot']=selected_snapshot(x[0],['I'])
            with self.assertRaises(ValueError):self.run_case(x)


if __name__=='__main__':unittest.main()
