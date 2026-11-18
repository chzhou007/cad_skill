import * as prior from './edge-attributes-nonnode-boundary.js';
import {checkedPlanBranchDN,planBranchDNProperties,planBranchDNCsvValues,planBranchDNFields} from './plan-seeded-branch-DN.js';
export * from './edge-attributes-nonnode-boundary.js';
export function edgeAttributeProperties(edge,data){
 const c=data?.attribute_value_context,old=prior.crossViewAttributeCsvValues(edge,c),r=checkedPlanBranchDN(edge,c,old),zh=data?.display?.edge_attribute_language==='zh-CN';
 const rows=prior.edgeAttributeProperties(edge,data);if(!r)return rows;
 const revised=r.whole_physical_DN_complete?rows.map(([k,v])=>[k,k==='\u7ba1\u5f84'||k==='Diameter'?`DN${r.nominal_mm}`:v]):rows;
 return [...planBranchDNProperties(edge,zh,c,old),...revised];
}
export function crossViewAttributeCsvValues(edge,context=null){
 const old=prior.crossViewAttributeCsvValues(edge,context),r=checkedPlanBranchDN(edge,context,old);
 if(!r)return old;
 const fill=r.whole_physical_DN_complete&&!(typeof old.diameter_nominal_mm==='number'&&old.diameter_nominal_mm>0);
 return {...old,...(fill?{diameter_nominal_mm:r.nominal_mm,diameter_text:`DN${r.nominal_mm}`,diameter_status:'native_plan_main_T_branch_horizontal_and_retained_axis11_vertical_DN'}:{}),...planBranchDNCsvValues(edge,context,old)};
}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...planBranchDNFields];
