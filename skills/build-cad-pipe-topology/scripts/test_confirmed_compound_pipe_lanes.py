import copy,hashlib,unittest
from confirm_crossview_paths import encode
from compound_pipe_label_evidence import parse
from confirmed_compound_pipe_lanes import resolve

class Tests(unittest.TestCase):
    def fixture(self):
        rows=[dict(parse('DN300(3.600)/DN200(3.000)'),handle=h,source_sha256='S')for h in ['A','B']]
        answer=dict(decision='different form;see explanation',comment='two overlapping pipes;sideview200,other300',source_pair_sha256='PAIR')
        reply=dict(answers={'Q':answer},source_evidence=dict(source_sha256='S'))
        policy=dict(question_id='Q',answer_sha256=hashlib.sha256(encode(answer)).hexdigest(),source_pair_sha256='PAIR',source_sha256='S',two_distinct_overlapping_pipes=True,nominals_mm=[300,200],sideview_nominal_mm=200,text_handles=['A','B'])
        return dict(records=rows),reply,policy
    def test_preserves_actual_option_and_comment_with_separate_declared_lanes(self):
        obs,reply,p=self.fixture();before=copy.deepcopy(obs);r=resolve(obs,reply,p)
        self.assertEqual(obs,before);self.assertEqual(r['confirmed_declarations'],2);self.assertEqual(r['confirmed_declaration_slots'],4);self.assertEqual(r['physical_pipe_instances_created'],0)
        for row in r['records']:
            self.assertEqual([x['nominal_mm']for x in row['members']],[300,200]);self.assertEqual(row['members'][1]['role'],'sideview_network_lane');self.assertIsNone(row['scalar_whole_edge_DN_mm']);self.assertFalse(row['source_LINE_membership_confirmed'])
            for member in row['members']:self.assertIsNone(member['physical_pipe_id']);self.assertIsNone(member['source_LINE_identity']);self.assertIsNone(member['physical_length_mm'])
    def test_wrong_source_reply_pair_or_member_never_unlocks_a_barrier(self):
        for case in ('source','answer','pair','member'):
            obs,reply,p=self.fixture()
            if case=='source':obs['records'][0]['source_sha256']='OTHER'
            elif case=='answer':reply['answers']['Q']['comment']='changed'
            elif case=='pair':reply['answers']['Q']['source_pair_sha256']='old'
            else:obs['records'][0]['members'][1]['nominal_mm']=150
            with self.subTest(case=case),self.assertRaises(ValueError):resolve(obs,reply,p)
    def test_unconfirmed_observations_remain_separate_and_order_is_preserved(self):
        obs,reply,p=self.fixture();p['text_handles']=['A'];r=resolve(obs,reply,p);self.assertEqual(r['other_source_declarations'],['B'])
        obs['records'][0]['members'].reverse();r=resolve(obs,reply,p);self.assertEqual([m['nominal_mm']for m in r['records'][0]['members']],[200,300])
if __name__=='__main__':unittest.main()
