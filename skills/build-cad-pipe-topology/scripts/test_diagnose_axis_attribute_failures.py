import copy,unittest
from diagnose_axis_attribute_failures import vertical_failures

class CompleteVerticalFailureCategories(unittest.TestCase):
    def test_other_path_seed_is_diagnosed_without_assigning_or_merging_it(self):
        scopes=[dict(edge_id=e,path_index=0,segment_index=0,scope_points=[[0,0],[0,10]],system='return',floor_start=2,floor_end=2,native_source_status='single_source_line_covers')for e in('KNOWN','UNKNOWN','AMBIG')]
        graph=dict(edges=[dict(edge_id=e,edge_type='tee_to_equipment',connection_mode='omission_pair_stitched_at_main_marker',source_native_block_branch={'original':'scope'})for e in('KNOWN','UNKNOWN','AMBIG')])
        proof=dict(records=[],pending=[dict(edge_id=e,path_index=0,segment_index=0,reason='old_stop',original_reason='no_qualified_axis_annotation_on_this_vertical_segment'if e!='AMBIG'else'ambiguous_native_text_projection_requires_ownership_rule')for e in('KNOWN','UNKNOWN','AMBIG')])
        annotations=dict(records=[dict(edge_id='KNOWN',path_index=1,segment_index=0,nominal_mm=80)])
        args=proof,dict(records=scopes),graph,annotations;before=copy.deepcopy(args);rows=vertical_failures(*args)
        self.assertEqual([r['diagnosis']for r in rows],['same_edge_other_path_seed_requires_native_omission_or_inline_composition','no_qualified_vertical_seed_on_current_edge','ambiguous_native_text_projection_requires_ownership_rule'])
        self.assertEqual(args,before);self.assertTrue(all(r['physical_values_assigned']==0 for r in rows));self.assertEqual(rows[0]['other_path_vertical_seed_values'],[80])

if __name__=='__main__':unittest.main()
