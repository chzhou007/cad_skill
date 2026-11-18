import * as prior from './edge-attributes-plan-seeded-branch.js';
import {checkedInheritedEntryDN,inheritedEntryDNCsvValues,inheritedEntryDNProperties,inheritedEntryDNFields} from './inherited-branch-entries-DN.js';
import {localConnectionProperties} from './checked-source-connection-display.js';
export * from './edge-attributes-plan-seeded-branch.js';
export function edgeAttributeProperties(edge,data){
 const c=data?.attribute_value_context,old=prior.crossViewAttributeCsvValues(edge,c),r=checkedInheritedEntryDN(edge,c,old),rows=prior.edgeAttributeProperties(edge,data),zh=data?.display?.edge_attribute_language==='zh-CN';
 if(!r)return localConnectionProperties(edge,c,old,zh,rows);
 const physicalRows=r.whole_physical_DN_complete?rows.map(([k,v])=>[k,k==='\u7ba1\u5f84'||k==='Diameter'?`DN${r.nominal_mm}`:v]):rows;
 return [...inheritedEntryDNProperties(edge,zh,c,old),...localConnectionProperties(edge,c,old,zh,physicalRows)];
}
export function crossViewAttributeCsvValues(edge,context=null){
 const old=prior.crossViewAttributeCsvValues(edge,context),r=checkedInheritedEntryDN(edge,context,old);if(!r)return old;
 const fill=r.whole_physical_DN_complete&&!(typeof old.diameter_nominal_mm==='number'&&old.diameter_nominal_mm>0);
 return {...old,...(fill?{diameter_nominal_mm:r.nominal_mm,diameter_text:`DN${r.nominal_mm}`,diameter_status:'native_inherited_plan_main_T_branch_and_independent_axis11_vertical_DN'}:{}),...inheritedEntryDNCsvValues(edge,context,old)};
}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...inheritedEntryDNFields];
