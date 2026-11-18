import copy
import unittest
from batch_rule_contract import check


class Tests(unittest.TestCase):
    def data(self):
        state='unmatched_local_or_main_detail_path'
        return dict(total_edges=2,states={state:2},records=[dict(edge_id=e,state=state,human_accepted=False,physical_length_mm=None) for e in ['E1','E2']]),dict(edges=[dict(edge_id=e) for e in ['E1','E2']])

    def test_complete_partition_retains_every_unmatched_edge(self):
        result,axis=self.data();out=check(result,axis)
        self.assertEqual(out['processed_edges'],2);self.assertEqual(out['technical_or_evidence_followup'],2)
        self.assertFalse(out['human_accepted'])

    def test_removed_or_duplicated_edges_cannot_improve_batch_completion(self):
        for mutation in ('remove','duplicate'):
            result,axis=self.data()
            if mutation=='remove':result['records'].pop()
            else:result['records'][1]['edge_id']='E1'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):check(result,axis)

    def test_zero_length_false_acceptance_and_edited_counts_fail(self):
        for key,value in [('physical_length_mm',0),('human_accepted',True),('state','complete')]:
            result,axis=self.data();result['records'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):check(result,axis)
        result,axis=self.data();result['total_edges']=1
        with self.assertRaises(ValueError):check(result,axis)


if __name__=='__main__':unittest.main()
