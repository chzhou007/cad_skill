import copy,unittest
from unittest.mock import patch
import cohort_plan_DN_reapplication as rule
class Tests(unittest.TestCase):
    def fixture(self):
        annotation=dict(seeds=[dict(edge_id='old',nominal_mm=80,evidence_id='source:old')],blocked_edges={'cap':[dict(text_handle='dn'),dict(text_handle='other')]},assigned=[],pending=[],unparsed_candidates=[],exceptions=[])
        spec=dict(group_id='known',scope=dict(seeds=[dict(source_line_handle='L',text_handle='dn')]),calibration_origin={})
        proof=dict(observations=[dict(edge_id='cap',nominal_mm=150,source_text=dict(handle='dn'))]);cohorts=[dict(source_family=['L','copy'])];return annotation,spec,proof,cohorts
    def test_specific_original_reader_resolves_only_its_own_text_and_keeps_other_barriers(self):
        a,s,p,c=self.fixture();before=copy.deepcopy(s)
        with patch.object(rule,'inventory',return_value=a),patch.object(rule,'pinned',return_value=dict(graph_sha256='old')),patch.object(rule,'specific_configuration',return_value=({},dict(controls='original'),{})),patch.object(rule,'calibrated_collect',return_value=p)as reader:
            out=rule.source_inventory('doc','graph','source','graph_hash',{},[s],c)
        self.assertEqual(out['blocked_edges'],{'cap':[dict(text_handle='other')]});self.assertEqual(out['seeds'],[dict(edge_id='old',nominal_mm=80,evidence_id='source:old'),dict(edge_id='cap',nominal_mm=150,evidence_id='source:dn')]);self.assertEqual(s,before);reader.assert_called_once_with('doc','graph',dict(controls='original'),'source','graph_hash')
    def test_conflicting_old_direct_owner_duplicate_claim_and_outside_family_stop(self):
        for kind in('conflict','duplicate','outside','missing'):
            a,s,p,c=self.fixture();specs=[s]
            if kind=='conflict':a['seeds'].append(dict(edge_id='other',nominal_mm=200,evidence_id='source:dn'))
            elif kind=='duplicate':specs=[s,copy.deepcopy(s)]
            elif kind=='outside':s['scope']['seeds'][0]['source_line_handle']='unknown'
            else:p['observations']=[]
            with self.subTest(kind=kind),patch.object(rule,'inventory',return_value=a),patch.object(rule,'pinned',return_value=dict(graph_sha256='old')),patch.object(rule,'specific_configuration',return_value=({},dict(controls='original'),{})),patch.object(rule,'calibrated_collect',return_value=p),self.assertRaises(ValueError):rule.source_inventory('doc','graph','source','graph_hash',{},specs,c)
if __name__=='__main__':unittest.main()
