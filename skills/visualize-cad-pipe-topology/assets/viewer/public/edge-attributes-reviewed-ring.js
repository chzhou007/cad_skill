import * as prior from './edge-attributes-plan-crossover.js';
import {checkedReviewedRingDN,reviewedRingDNProperties,reviewedRingDNCsvValues,reviewedRingDNCsvFields} from './reviewed-ring-partition-DN.js';
export * from './edge-attributes-plan-crossover.js';
export function edgeAttributeProperties(edge,data){const context=data?.attribute_value_context,old=prior.crossViewAttributeCsvValues(edge,context),r=checkedReviewedRingDN(edge,context),rows=prior.edgeAttributeProperties(edge,data);if(r&&typeof old.diameter_nominal_mm==='number'&&old.diameter_nominal_mm>0&&old.diameter_nominal_mm!==r.whole_axis_nominal_mm)return rows;return reviewedRingDNProperties(edge,rows,data?.display?.edge_attribute_language==='zh-CN',context);}
export function crossViewAttributeCsvValues(edge,context=null){
 const old=prior.crossViewAttributeCsvValues(edge,context),r=checkedReviewedRingDN(edge,context);
 if(!r||(typeof old.diameter_nominal_mm==='number'&&old.diameter_nominal_mm>0&&old.diameter_nominal_mm!==r.whole_axis_nominal_mm))return old;
 return {...old,...reviewedRingDNCsvValues(edge,context)};
}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...reviewedRingDNCsvFields];
