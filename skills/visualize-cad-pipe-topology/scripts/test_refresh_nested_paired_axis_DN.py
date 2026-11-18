import copy,json,unittest
from refresh_nested_paired_axis_DN import delta

class NestedPairAxisDeltaTests(unittest.TestCase):
    def test_new_segment_values_preserve_all_old_effective_fields(self):
        rows=[dict(edge_id='E',path_index=0,segment_index=0,nominal_mm=200),dict(edge_id='E',path_index=0,segment_index=2,nominal_mm=200)]
        context=dict(nested_pair_axis_vertical_DN=dict(records=rows,source_bindings=dict(native_source='S')))
        old=[dict(edge_id='E',values=dict(old_plan_DN=300,axis_omission_vertical_DN_segments_json='old',unknown_length=None)),dict(edge_id='OTHER',values={'unchanged':'yes'})]
        new=copy.deepcopy(old);new[0]['values'].update(axis_nested_pair_vertical_DN_segment_count=2,axis_nested_pair_vertical_DN_segments_json=json.dumps(rows),axis_nested_pair_vertical_DN_source_sha256='S')
        result=delta(old,new,context);self.assertEqual(result['changed_edges'],['E']);self.assertEqual(result['new_vertical_domains'],2)
        for change in ('plan','old_vertical','unknown_length','local','other'):
            with self.subTest(change=change):
                broken=copy.deepcopy(new)
                if change=='local':broken[0]['values']['axis_nested_pair_vertical_DN_segment_count']=1
                elif change=='other':broken[1]['values']['unchanged']='no'
                else:broken[0]['values'][{'plan':'old_plan_DN','old_vertical':'axis_omission_vertical_DN_segments_json','unknown_length':'unknown_length'}[change]]=0
                with self.assertRaises(ValueError):delta(old,broken,context)

if __name__=='__main__':unittest.main()
