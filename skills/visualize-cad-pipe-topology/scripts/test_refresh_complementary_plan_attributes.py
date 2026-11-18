import copy,unittest
from refresh_complementary_plan_attributes import delta

class Refresh(unittest.TestCase):
    def fixture(self):
        record=dict(axis_edge_id='A',source_scope_id='NEW',complete_horizontal_centerline_mm=1000,nominal_mm=150)
        before=[dict(edge_id='A',values=dict(diameter_nominal_mm='',diameter_text='',diameter_status='unknown')),dict(edge_id='OLD',values=dict(diameter_nominal_mm=200))]
        after=copy.deepcopy(before);after[0]['values'].update(diameter_nominal_mm=150,diameter_text='DN150',diameter_status='source_checked_current_T_plan_DN',
            complementary_plan_centerline_mm=1000,complementary_mapping_id='NEW',complementary_evidence_json=__import__('json').dumps(record))
        return before,after,[record]
    def test_only_declared_new_DN_cells_change_old_column_values(self):
        args=self.fixture();result=delta(*args);self.assertEqual(len(result['declared_old_column_changes']),3);self.assertTrue(result['all_other_old248_column_values_exact'])
    def test_original_sparse_empty_reader_still_has_three_blank_export_columns(self):
        before,after,records=self.fixture();before[0]['values']={}
        result=delta(before,after,records);self.assertEqual(len(result['declared_old_column_changes']),3)
    def test_old_known_DN_unrelated_mutation_missing_column_or_bad_adoption_fails(self):
        for mutation in(lambda b,a,r:b[0]['values'].update(diameter_nominal_mm=200),lambda b,a,r:a[1]['values'].update(diameter_nominal_mm=250),lambda b,a,r:a[0]['values'].pop('diameter_text'),lambda b,a,r:a[0]['values'].update(complementary_plan_centerline_mm=0)):
            args=self.fixture();mutation(*args)
            with self.assertRaises(ValueError):delta(*args)

if __name__=='__main__':unittest.main()
