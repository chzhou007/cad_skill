// Received answers are history; local edits are never proof of a new receipt.
export function mergeReviewAnswers(stored, received = {}) {
 const incoming=received.answers||{}, local=stored&&typeof stored==='object'&&!Array.isArray(stored)?stored:{};
 return Object.fromEntries([...new Set([...Object.keys(incoming),...Object.keys(local)])]
  .map(id=>[id,local[id]||incoming[id]]));
}

// Preserve the received record independently of newer browser drafts. A missing
// draft field is not an explicit deletion of an expert's historical comment.
export function buildReviewBackup(data, answers, exportedAt = new Date().toISOString()) {
 const receiptFields=['received_feedback','received_followup_feedback','received_compound_lane_feedback'];
 const incoming=Object.assign({},...receiptFields.map(field=>data[field]?.answers||{}));
 const clone=value=>JSON.parse(JSON.stringify(value));
 const serialize=section=>({...section,questions:section.questions.map(q=>({...q,answer:{...(incoming[q.id]||{}),...(answers[q.id]||{})}}))});
 const result={schema:data.schema,exported_at:exportedAt,technical_updates:data.technical_updates||[],sections:(data.sections||[]).map(serialize),followup_sections:(data.followup_sections||[]).map(serialize),browser_answer_snapshot:answers,answer_export_policy:{received_history_preserved:true,omitted_fields_inherit_received:true,explicit_empty_fields_preserved:true}};
 for(const field of receiptFields)if(data[field])result[field]=data[field];
 return clone(result);
}

export function partitionReviewSections(sections, received = {}, workflow = {}) {
 const receipts=received.answers||{}, pairs=workflow.received_pair_sha256_by_question||{};
 const reopened=new Set(workflow.reopened_question_ids||[]), seen=new Set();
 let pendingCount=0, archivedCount=0;
 const rows=sections.map((section,index)=>{
  const pending=[], archived=[];
  for(const question of section.questions){
   if(seen.has(question.id))throw new Error('Duplicate review question ID');
   seen.add(question.id);
   const answered=typeof receipts[question.id]?.decision==='string'&&receipts[question.id].decision.trim();
   const samePair=typeof pairs[question.id]==='string'&&pairs[question.id]&&pairs[question.id]===section.image?.sha256;
   (answered&&samePair&&!reopened.has(question.id)?archived:pending).push(question);
  }
  pendingCount+=pending.length;archivedCount+=archived.length;
  return {section,index,pending,archived};
 });
 return {rows,pendingCount,archivedCount,total:seen.size};
}
