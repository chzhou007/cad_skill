import copy,hashlib,tempfile,unittest
from pathlib import Path
from review_page_preflight import validate_dataset,coverage_summary

class ReviewPagePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'assets').mkdir();path=self.root/'assets/原图.png';path.write_bytes(b'unchanged source-pair bytes');self.media=dict(path='assets/原图.png',sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        self.data=dict(sections=[dict(title='原有题目',image=self.media,contexts=[dict(title='大范围',**self.media,locators=[dict(label='A',description='待判断位置')])],questions=[dict(id='Q1',text='这两个端点的归属？',options=['对应设备','其他设备'],source_evidence=dict(pair_sha256=self.media['sha256']))])],received_feedback=dict(answers={'Q1':dict(decision='对应设备')}))
    def tearDown(self):self.temp.cleanup()
    def test_valid_context_preserves_questions_answers_and_optional_vector(self):
        before=copy.deepcopy(self.data);result=validate_dataset(self.data,self.root);self.assertEqual(self.data,before);self.assertEqual(result['question_count'],1);self.assertEqual(result['optional_vector_absent'],1);self.assertFalse(result['human_accepted'])
    def test_missing_locators_and_bad_types_are_caught_before_publication(self):
        for value in (None,'A',{}):
            with self.subTest(value=value):
                d=copy.deepcopy(self.data);d['sections'][0]['contexts'][0]['locators']=value
                with self.assertRaisesRegex(ValueError,'locators'):validate_dataset(d,self.root)
        d=copy.deepcopy(self.data);del d['sections'][0]['contexts'][0]['locators']
        with self.assertRaisesRegex(ValueError,'locators'):validate_dataset(d,self.root)
    def test_media_paths_fingerprints_and_pair_identity_cannot_drift(self):
        for change in ('path','sha','pair','vector'):
            with self.subTest(change=change):
                d=copy.deepcopy(self.data);s=d['sections'][0]
                if change=='path':s['image']['path']='../outside.png'
                elif change=='sha':s['image']['sha256']='0'*64
                elif change=='pair':s['questions'][0]['source_evidence']['pair_sha256']='0'*64
                else:s['contexts'][0]['svg_path']='assets/missing.svg'
                with self.assertRaises(ValueError):validate_dataset(d,self.root)
    def test_duplicates_and_unreadable_text_cannot_abort_a_published_page(self):
        for change in ('id','options','text'):
            with self.subTest(change=change):
                d=copy.deepcopy(self.data);q=d['sections'][0]['questions'][0]
                if change=='id':d['followup_sections']=[copy.deepcopy(d['sections'][0])]
                elif change=='options':q['options']=['同意','同意']
                else:q['text']='损坏\ufffd文本'
                with self.assertRaises(ValueError):validate_dataset(d,self.root)
    def test_progress_uses_actual_rows_and_separates_three_counts(self):
        rows=[dict(edge_id=f'E{i}',mapping_covered=i<96,native_candidate_attribute_covered=i<96,published_attribute_covered=i<90) for i in range(100)]
        coverage=dict(total_plan_edges=100,mapped_plan_edges=96,native_candidate_attribute_covered_plan_edges=96,published_attribute_covered_plan_edges=90)
        result=coverage_summary(coverage,rows);self.assertEqual((result['mapped'],result['native_candidate'],result['published'],result['unmapped']),(96,96,90,4));self.assertIn('在线属性90/100',result['text'])
        for change in ('count','publish','candidate'):
            with self.subTest(change=change):
                c=copy.deepcopy(coverage);r=copy.deepcopy(rows)
                if change=='count':c['mapped_plan_edges']=90
                elif change=='publish':r[-1]['published_attribute_covered']=True
                else:c['native_candidate_attribute_covered_plan_edges']=95
                with self.assertRaises(ValueError):coverage_summary(c,r)
    def test_unknown_native_coverage_is_not_filled_from_mapping(self):
        result=coverage_summary(dict(total_plan_edges=1,mapped_plan_edges=1,published_attribute_covered_plan_edges=0),[dict(edge_id='E',mapping_covered=True,published_attribute_covered=False)])
        self.assertIsNone(result['native_candidate']);self.assertIn('尚未记录',result['text']);self.assertNotIn('原生候选属性0/',result['text'])
    def test_floor_identity_comes_from_coverage_instead_of_the_SH16_example(self):
        rows=[dict(edge_id='E',mapping_covered=True,published_attribute_covered=False)]
        coverage=dict(total_plan_edges=1,mapped_plan_edges=1,published_attribute_covered_plan_edges=0,floor=3)
        self.assertTrue(coverage_summary(coverage,rows)['stats'].startswith('3层映射'))
        del coverage['floor'];self.assertTrue(coverage_summary(coverage,rows)['stats'].startswith('当前楼层映射'))

if __name__=='__main__':unittest.main()
