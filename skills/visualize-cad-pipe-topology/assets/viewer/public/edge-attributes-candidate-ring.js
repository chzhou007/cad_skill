import * as prior from './edge-attributes-effective-provider.js';
import {checkedCandidateRingDN,candidateRingDNProperties,candidateRingDNCsvValues,candidateRingDNCsvFields} from './reviewed-candidate-ring-DN.js';
export * from './edge-attributes-effective-provider.js';
function eligible(edge,context,old){const r=checkedCandidateRingDN(edge,context);return r&&(!(typeof old.diameter_nominal_mm==='number'&&old.diameter_nominal_mm>0)||old.diameter_nominal_mm===r.whole_axis_nominal_mm);}
export function edgeAttributeProperties(edge,data){const c=data?.attribute_value_context,old=prior.crossViewAttributeCsvValues(edge,c),rows=prior.edgeAttributeProperties(edge,data);return eligible(edge,c,old)?candidateRingDNProperties(edge,rows,data?.display?.edge_attribute_language==='zh-CN',c):rows;}
export function crossViewAttributeCsvValues(edge,context=null){const old=prior.crossViewAttributeCsvValues(edge,context);return eligible(edge,context,old)?{...old,...candidateRingDNCsvValues(edge,context)}:old;}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...candidateRingDNCsvFields];
