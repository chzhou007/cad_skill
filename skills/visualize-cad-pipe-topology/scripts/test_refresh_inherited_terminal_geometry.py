import copy,json,unittest
from refresh_inherited_terminal_geometry import difference,adopt_provider,source_guard
import test_refresh_anchored_terminal_branches as fixtures
from reapply_inherited_terminal_geometry import MODE

class InheritedTerminalAdoption(unittest.TestCase):
    def test_first_branch_and_all_old_nonempty_cells_preserved(self):
        before,after,rows=fixtures.ActualBranchValues().data()
        for data in(before,after):data[1]['values']['anchored_branch_mapping_id']='OLD'
        d=difference(before,after,rows)
        self.assertTrue(d['all_old264_column_nonempty_values_exact']);self.assertEqual(d['declared_previously_blank_cells_filled'],8)
        after[1]['values']['anchored_branch_mapping_id']='CHANGED'
        with self.assertRaises(ValueError):difference(before,after,rows)
    def test_prior_metadata_and_vertical_domains_retained(self):
        old=dict(mode='prior',counts={'existing_correspondence_edges':1,'mixed_edges_without_any_correspondence':1,'new_anchored_terminal_branch_contexts':10},records=[dict(edge_id='NEW',classification='mixed_horizontal_vertical',has_existing_correspondence=False,correspondence_observations=[])],new_anchored_terminal_branch_records=['EXACT-OLD'],ordinary_junction_mappings=[],member_domain_observations=[],current_component_inventory={},current_horizontal_frontier={},remaining_horizontal_attributes=[],all_current_vertical_DN_domains=['V'])
        r=dict(axis_edge_id='NEW',mapping_id='M',plan_edge_id='P',floor=3,plan_horizontal_projection={'value_mm':12})
        proof=dict(records=[r],original_published_records=[{}]*10)
        effective=[dict(edge_id='NEW',values=dict(anchored_branch_mapping_id='M',anchored_branch_plan_edge='P',anchored_branch_plan_pipe_XY_mm=12))]
        before=copy.deepcopy(old);result=adopt_provider(old,proof,effective)
        self.assertEqual(old,before);self.assertEqual(result['new_anchored_terminal_branch_records'],['EXACT-OLD']);self.assertEqual(result['counts']['new_anchored_terminal_branch_contexts'],10)
        self.assertEqual(result['all_current_vertical_DN_domains'],['V']);self.assertEqual(result['counts']['all_anchored_terminal_branch_contexts'],11)
    def test_duplicate_writer_or_missing_full_population_gate_rejected(self):
        p=dict(mode=MODE,records=[{'axis_edge_id':'E'}],original_published_records=[{'axis_edge_id':'E'}],complete_published_parent_replayed=True,all_current_marker_interfaces_screened=True,all_current_main_third_arms_screened=True,old_published_records_unchanged=True,source_graphs_mutated=False,crossed_pipes_connected=False,human_accepted=False,new_physical_nodes_created=0,whole_axis_DN_assigned=0,whole_axis_lengths_assigned=0,vertical_values_assigned=0)
        with self.assertRaises(ValueError):source_guard(p)
        p['records']=[];p['all_current_marker_interfaces_screened']=False
        with self.assertRaises(ValueError):source_guard(p)

if __name__=='__main__':unittest.main()
