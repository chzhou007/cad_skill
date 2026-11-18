import copy,json,unittest
from refresh_anchored_native_plan_metrics import delta
class Tests(unittest.TestCase):
    def test_only_new_metric_fields_may_be_added_existing_DN_stays_exact(self):
        r=dict(axis_edge_id='E',source_scope_id='M',complete_horizontal_centerline_mm=5300,native_source_index_pairs=[(0,1),(1,0)])
        before=[dict(edge_id='E',values=dict(diameter_nominal_mm=250,vertical='old')),dict(edge_id='OTHER',values={})];after=copy.deepcopy(before)
        after[0]['values'].update(anchored_metric_mapping_id='M',anchored_metric_complete_centerline_mm=5300,anchored_metric_evidence_json=json.dumps(r))
        self.assertTrue(delta(before,after,[r])['all_old_effective_attribute_values_exact'])
        for eid,key,value in [(0,'diameter_nominal_mm',300),(0,'vertical','changed'),(1,'anchored_metric_complete_centerline_mm',100)]:
            changed=copy.deepcopy(after);changed[eid]['values'][key]=value
            with self.assertRaises(ValueError):delta(before,changed,[r])
if __name__=='__main__':unittest.main()
