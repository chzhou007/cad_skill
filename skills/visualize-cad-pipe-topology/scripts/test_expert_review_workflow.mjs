import test from 'node:test';
import assert from 'node:assert/strict';
import {mergeReviewAnswers,partitionReviewSections,buildReviewBackup} from '../assets/viewer/public/expert-review-workflow.mjs';

const sections=[{title:'原题',image:{sha256:'PAIR'},questions:[{id:'Q1'},{id:'Q2'}]}];
const received={answers:{Q1:{decision:'连接',comment:'保留原答复'}}};
const workflow={received_pair_sha256_by_question:{Q1:'PAIR'}};
test('only source-bound received answers are archived; local decisions remain pending',()=>{
 const input=structuredClone([sections,received,workflow]);
 const result=partitionReviewSections(sections,received,workflow);
 assert.equal(result.archivedCount,1);assert.equal(result.pendingCount,1);
 assert.deepEqual(result.rows[0].archived.map(q=>q.id),['Q1']);
 assert.deepEqual([sections,received,workflow],input);
});
test('a changed Pair or explicitly reopened question requires new judgment',()=>{
 for(const w of [{received_pair_sha256_by_question:{Q1:'OLDER'}},{...workflow,reopened_question_ids:['Q1']},{}]){
  const result=partitionReviewSections(sections,received,w);
  assert.equal(result.archivedCount,0);assert.equal(result.pendingCount,2);
 }
});
test('empty receipts and duplicate IDs never create an all-clear',()=>{
 assert.equal(partitionReviewSections(sections,{answers:{Q1:{decision:''}}},workflow).pendingCount,2);
 assert.throws(()=>partitionReviewSections([...sections,...sections],received,workflow),/Duplicate/);
});
test('archiving preserves local corrections and the received fallback without mutation',()=>{
 const stored={Q1:{decision:'本地补充',comment:'新说明'},Q2:{decision:'已填但未提交'}};
 const result=mergeReviewAnswers(stored,received);
 assert.deepEqual(result,stored);assert.equal(received.answers.Q1.decision,'连接');
 assert.deepEqual(mergeReviewAnswers({},received),received.answers);
});

test('backup retains original receipt and fills a comment omitted by an older browser draft',()=>{
 const data={schema:'review',sections,received_feedback:received,followup_sections:[{title:'待答',questions:[{id:'Q3'}]}]};
 const answers={Q1:{decision:'连接',updated_at:'browser-time'},Q2:{decision:'本地填写'}};
 const before=structuredClone({data,answers});const result=buildReviewBackup(data,answers,'export-time');
 assert.equal(result.sections[0].questions[0].answer.comment,'保留原答复');
 assert.equal(result.sections[0].questions[0].answer.updated_at,'browser-time');
 assert.deepEqual(result.received_feedback,received);assert.deepEqual(result.browser_answer_snapshot,answers);
 assert.deepEqual(result.followup_sections[0].questions[0].answer,{});
 assert.deepEqual({data,answers},before);result.received_feedback.answers.Q1.comment='mutated-output';assert.equal(received.answers.Q1.comment,'保留原答复');
});

test('explicit local correction or empty comment is kept without erasing received history',()=>{
 const data={schema:'review',sections,received_feedback:received};
 const result=buildReviewBackup(data,{Q1:{decision:'本地更正',comment:''}});
 assert.equal(result.sections[0].questions[0].answer.decision,'本地更正');
 assert.equal(result.sections[0].questions[0].answer.comment,'');
 assert.equal(result.received_feedback.answers.Q1.comment,'保留原答复');
});

test('all followup receipt kinds and source scope survive export with pending answers empty',()=>{
 const data={schema:'review',sections:[],followup_sections:sections,received_followup_feedback:received,received_compound_lane_feedback:{answers:{Q2:{decision:'已确认',source_pair_sha256:'pair-hash',comment:'中文说明'}}}};
 const result=buildReviewBackup(data,{});
 assert.deepEqual(result.followup_sections[0].questions[0].answer,received.answers.Q1);
 assert.equal(result.followup_sections[0].questions[1].answer.source_pair_sha256,'pair-hash');
 assert.deepEqual(result.received_compound_lane_feedback,data.received_compound_lane_feedback);
});
