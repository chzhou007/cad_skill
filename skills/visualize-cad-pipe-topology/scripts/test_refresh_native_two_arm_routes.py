import copy,json,unittest,tempfile
from pathlib import Path
from refresh_native_two_arm_routes import delta,fresh_result,sha
class Tests(unittest.TestCase):
    def test_native_insertion_order_and_viewer_sorted_JSON_have_equal_values_but_keep_receipt_hash(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);p=root/'proof.json';p.write_text(json.dumps({'z':2,'a':[(0,1)]}),encoding='utf8');(root/'receipt.json').write_text(json.dumps({'output_sha256':{'proof.json':sha(p)}}),encoding='utf8')
            self.assertTrue(fresh_result({'a':[(0,1)],'z':2},p));self.assertFalse(fresh_result({'a':[(0,1)],'z':3},p));p.write_text(json.dumps({'a':[[0,1]],'z':2},sort_keys=True),encoding='utf8');self.assertFalse(fresh_result({'a':[(0,1)],'z':2},p))
    def test_only_qualified_source_correspondence_is_added_no_old_metric_change(self):
        record=dict(axis_edge_id='E',mapping_id='M',native_indices=[(0,1)])
        before=[dict(edge_id='E',values={'diameter_nominal_mm':250,'anchored_metric_complete_centerline_mm':3550}),dict(edge_id='OTHER',values={'vertical':'old'})];after=copy.deepcopy(before);after[0]['values'].update(two_arm_external_mapping_id='M',two_arm_external_evidence_json=json.dumps(record))
        self.assertTrue(delta(before,after,[record])['all_old244_column_values_exact'])
        for idx,key,value in[(0,'diameter_nominal_mm',200),(0,'anchored_metric_complete_centerline_mm',0),(1,'two_arm_external_mapping_id','M')]:
            changed=copy.deepcopy(after);changed[idx]['values'][key]=value
            with self.assertRaises(ValueError):delta(before,changed,[record])
        after[0]['values']['two_arm_external_evidence_json']='{}'
        with self.assertRaises(ValueError):delta(before,after,[record])
if __name__=='__main__':unittest.main()
