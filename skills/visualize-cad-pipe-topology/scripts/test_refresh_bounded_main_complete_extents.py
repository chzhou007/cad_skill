import copy,json,unittest
from refresh_bounded_main_complete_extents import delta
class Tests(unittest.TestCase):
    def test_only_new_complete_fields_change_old_DN_and_verticals_stay_exact(self):
        row=dict(axis_edge_id='E',nominal_mm=300,complete_horizontal_centerline_route_mm=19100)
        context=dict(records=[row],source_bindings=dict(native_proof='p'))
        prior=[dict(edge_id='E',values=dict(diameter_nominal_mm=300,bounded_main_plan_pipe_XY_mm=19100)),dict(edge_id='V',values=dict(axis_vertical_DN_segments_json='old'))]
        current=copy.deepcopy(prior);current[0]['values'].update(batch_complete_horizontal_centerline_mm=19100,bounded_main_complete_centerline_mm=19100,bounded_main_complete_extent_evidence_json=json.dumps(row),bounded_main_complete_extent_proof_sha256='p')
        self.assertEqual(delta(prior,current,context)['new_complete_horizontal_centerlines'],1)
        for kind in('DN','vertical','installed'):
            bad=copy.deepcopy(current)
            if kind=='DN':bad[0]['values']['diameter_nominal_mm']=200
            elif kind=='vertical':bad[1]['values']['axis_vertical_DN_segments_json']='changed'
            else:bad[0]['values']['crossview_whole_edge_length_mm']=19100
            with self.subTest(kind=kind),self.assertRaises(ValueError):delta(prior,bad,context)
if __name__=='__main__':unittest.main()
