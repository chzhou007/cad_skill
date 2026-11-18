import {checkedReviewedRingDN,reviewedRingDNProperties,reviewedRingDNCsvValues,reviewedRingDNCsvFields} from './reviewed-ring-partition-DN.js';
const key='reviewed_candidate_ring_partition_DN';
function sourceContext(context){
 const root=context?.[key];
 if(root?.mode!=='qualified_reviewed_candidate_ring_partition_DN_v1')return null;
 return {...context,reviewed_ring_partition_DN:{...root,mode:'qualified_reviewed_ring_partition_DN_v1'}};
}
export function checkedCandidateRingDN(edge,context){const scoped=sourceContext(context);return scoped?checkedReviewedRingDN(edge,scoped):null;}
export function candidateRingDNProperties(edge,prior,zh,context){const scoped=sourceContext(context);return scoped?reviewedRingDNProperties(edge,prior,zh,scoped):prior;}
export const candidateRingDNCsvFields=reviewedRingDNCsvFields.map(k=>k.replace(/^reviewed_partition_/,'candidate_ring_partition_'));
export function candidateRingDNCsvValues(edge,context){
 const scoped=sourceContext(context);if(!scoped)return {};
 return Object.fromEntries(Object.entries(reviewedRingDNCsvValues(edge,scoped)).map(([k,v])=>[k.replace(/^reviewed_partition_/,'candidate_ring_partition_'),v]));
}
