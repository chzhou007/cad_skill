import copy,json,unittest
from refresh_omission_vertical_DN import delta

class OmissionViewerDeltaTests(unittest.TestCase):
    def test_only_new_local_fields_are_written_and_old_values_remain_exact(self):
        row=dict(edge_id='E',path_index=0,segment_index=0,nominal_mm=80)
        context=dict(omission_vertical_DN=dict(records=[row],source_bindings=dict(native_source='S')))
        old=[dict(edge_id='E',values=dict(diameter_nominal_mm=150,unknown_length=None)),dict(edge_id='OTHER',values=dict(old='same'))]
        new=copy.deepcopy(old);new[0]['values'].update(axis_omission_vertical_DN_segment_count=1,axis_omission_vertical_DN_segments_json=json.dumps([row]),axis_omission_vertical_DN_source_sha256='S')
        result=delta(old,new,context)
        self.assertEqual(result['changed_edges'],['E']);self.assertEqual(result['new_physical_lengths'],0)
        for variant in ('oldDN','length','unrelated','local','population'):
            altered=copy.deepcopy(new)
            if variant=='oldDN':altered[0]['values']['diameter_nominal_mm']=80
            elif variant=='length':altered[0]['values']['unknown_length']=0
            elif variant=='unrelated':altered[1]['values']['new']='bad'
            elif variant=='local':altered[0]['values']['axis_omission_vertical_DN_segments_json']='[]'
            else:altered.pop()
            with self.subTest(variant=variant),self.assertRaises(ValueError):delta(old,altered,context)

if __name__=='__main__':unittest.main()
