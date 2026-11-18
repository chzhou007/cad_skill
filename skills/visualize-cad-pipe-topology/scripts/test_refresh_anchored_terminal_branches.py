import copy,unittest
from refresh_anchored_terminal_branches import delta
class ActualBranchValues(unittest.TestCase):
    def data(self):
        import json
        r=dict(axis_edge_id='MIX',mapping_id='M',plan_horizontal_projection={'value_mm':1200})
        before=[dict(edge_id='MIX',values=dict(diameter_nominal_mm=250,old_vertical_DN=80)),dict(edge_id='OTHER',values={'old':12})]
        after=copy.deepcopy(before);after[0]['values'].update(anchored_branch_mapping_id='M',anchored_branch_plan_edge='B',anchored_branch_plan_DN_mm=150,anchored_branch_plan_pipe_XY_mm=1200,anchored_branch_plan_source_sha256='s',anchored_branch_plan_graph_sha256='g',anchored_branch_scope='scope',anchored_branch_evidence_json=json.dumps(r))
        return before,after,[r]
    def test_no_old_cell_changes_for_new_mixed_context(self):
        before,after,rows=self.data();d=delta(before,after,rows);self.assertTrue(d['all_old256_column_values_exact']);self.assertEqual(d['new_whole_DN_values'],0)
    def test_whole_diameter_vertical_or_unrelated_writer_mutation_rejected(self):
        for key in ['diameter_nominal_mm','old_vertical_DN']:
            before,after,rows=self.data();after[0]['values'][key]=150
            with self.assertRaisesRegex(ValueError,'old pipe attribute'):delta(before,after,rows)
        before,after,rows=self.data();after[1]['values']['anchored_branch_mapping_id']='BAD'
        with self.assertRaisesRegex(ValueError,'unrelated'):delta(before,after,rows)
if __name__=='__main__':unittest.main()
