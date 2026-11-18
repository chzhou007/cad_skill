import copy,hashlib,json,tempfile,unittest,subprocess,sys
from pathlib import Path
from current_source_review_queue import compose,produce,MODE,sha

class CurrentSourceReviewQueueTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'assets').mkdir();p=self.root/'assets/pair.png';p.write_bytes(b'native source media');self.image=dict(path='assets/pair.png',sha256=sha(p));self.source=self.root/'source.dxf';self.source.write_bytes(b'fixed native source');self.spec=dict(path=str(self.source),sha256=sha(self.source))
  self.base=dict(sections=[self.section('OLD')],followup_sections=[],received_feedback=dict(answers={'OLD':dict(decision='confirmed',comment='original note')}))
 def tearDown(self):self.temp.cleanup()
 def section(self,qid):return dict(title='源图范围对照',description='保留原图',note='未知值不填零',image=copy.deepcopy(self.image),contexts=[dict(title='原CAD大范围',**self.image,locators=[dict(label='A')])],questions=[dict(id=qid,text='本范围的标注如何分区？',options=['统一','分区见说明'],source_evidence=dict(pair_sha256=self.image['sha256'],external_question_sha256='a'*64))])
 def proposal(self,qid='NEW',aliases=None):
  qualification=self.root/(qid+'-qualification.json');qualification.write_text(json.dumps(dict(mode=MODE,question_id=qid,source_inputs=[self.spec],review_ready=True,graph_mutated=False,physical_values_assigned=0,human_accepted=False)),encoding='utf8')
  return dict(section=self.section(qid),qualification=dict(path=str(qualification),sha256=sha(qualification)),source_inputs=[copy.deepcopy(self.spec)],origin='external_current_DN_region',original_question_sha256='a'*64,aliases=aliases or [])
 def test_external_items_count_once_and_all_old_answers_are_exact(self):
  old=copy.deepcopy(self.base);result,report=compose(self.base,[self.proposal()],self.root);self.assertEqual(self.base,old);self.assertEqual(result['received_feedback'],old['received_feedback']);self.assertEqual(report['queue']['pending_question_ids'],['NEW']);self.assertEqual(report['queue']['archived_received_questions'],['OLD']);self.assertEqual(report['new_canonical_question_ids'],['NEW']);self.assertFalse(report['human_accepted'])
 def test_duplicate_views_of_one_question_do_not_inflate_queue(self):
  proposal=self.proposal(aliases=['CYCLE-VIEW']);data,report=compose(self.base,[proposal,copy.deepcopy(proposal)],self.root);self.assertEqual(len(data['followup_sections']),1);self.assertEqual(report['deduplicated_question_ids'],['NEW']);self.assertEqual(report['queue']['total_questions'],2)
 def test_existing_pair_or_question_change_cannot_overwrite_history(self):
  p=self.proposal();data,_=compose(self.base,[p],self.root);broken=copy.deepcopy(p);broken['section']['questions'][0]['text']='changed source extent'
  with self.assertRaisesRegex(ValueError,'existing question'):compose(data,[broken],self.root)
 def test_changed_native_source_or_receipt_blocks_publishing(self):
  for what in('source','receipt'):
   p=self.proposal();target=self.source if what=='source'else Path(p['qualification']['path']);old=target.read_bytes();target.write_bytes(old+b' ')
   with self.assertRaisesRegex(ValueError,'changed'):compose(self.base,[p],self.root)
   target.write_bytes(old)
 def test_unready_acceptance_or_physical_values_block_question_promotion(self):
  for k,v in [('review_ready',False),('physical_values_assigned',1),('human_accepted',True),('graph_mutated',True)]:
   p=self.proposal();path=Path(p['qualification']['path']);r=json.loads(path.read_text());r[k]=v;path.write_text(json.dumps(r));p['qualification']['sha256']=sha(path)
   with self.assertRaisesRegex(ValueError,'not ready'):compose(self.base,[p],self.root)
 def test_competing_aliases_are_rejected(self):
  a=self.proposal('A',['same-external']);b=self.proposal('B',['same-external'])
  with self.assertRaisesRegex(ValueError,'competing'):compose(self.base,[a,b],self.root)
 def test_bad_media_schema_is_caught_before_page_publication(self):
  p=self.proposal();del p['section']['contexts'][0]['locators']
  with self.assertRaisesRegex(ValueError,'locators'):compose(self.base,[p],self.root)
 def test_old_followup_with_stale_pair_stays_pending_and_answer_is_retained(self):
  self.base['followup_sections']=[self.section('PREVIOUS')];self.base['received_followup_feedback']=dict(answers={'PREVIOUS':dict(decision='统一',source_pair_sha256='0'*64)})
  data,report=compose(self.base,[self.proposal()],self.root);self.assertIn('PREVIOUS',report['queue']['pending_question_ids']);self.assertEqual(data['received_followup_feedback'],self.base['received_followup_feedback'])
 def test_produce_creates_separate_reproducible_data_and_pins_originals(self):
  existing=self.root/'existing.json';proposals=self.root/'proposals.json';existing.write_text(json.dumps(self.base));proposals.write_text(json.dumps([self.proposal()]));old=existing.read_bytes();output=self.root/'output';r=produce(existing,proposals,self.root,output);self.assertEqual(existing.read_bytes(),old);self.assertEqual(r['output_sha256'],sha(output/'review-queue.json'))
  with self.assertRaises(FileExistsError):produce(existing,proposals,self.root,output)
 def test_pipeline_entry_exposes_source_inputs_without_native_runtime(self):
  pipeline=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts/pipeline.py'
  result=subprocess.run([sys.executable,'-X','utf8','-B',str(pipeline),'merge-current-source-review-queue','--help'],capture_output=True,text=True,encoding='utf8')
  self.assertEqual(result.returncode,0,result.stderr);self.assertIn('--proposals',result.stdout);self.assertIn('--page-root',result.stdout)
if __name__=='__main__':unittest.main()
