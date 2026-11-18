import * as prior from './edge-attributes-candidate-ring.js';
import {checkedReceivedUniform,receivedScopeProperties,receivedScopeCsvValues,receivedScopeFields} from './received-scope-attributes.js';
export * from './edge-attributes-candidate-ring.js';
function agrees(r,old){return !r?.whole_horizontal_edge||!(typeof old.diameter_nominal_mm==='number'&&old.diameter_nominal_mm>0)||old.diameter_nominal_mm===r.nominal_mm;}
export function edgeAttributeProperties(edge,data){
 const c=data?.attribute_value_context,old=prior.crossViewAttributeCsvValues(edge,c),r=checkedReceivedUniform(edge,c),rows=prior.edgeAttributeProperties(edge,data),zh=data?.display?.edge_attribute_language==='zh-CN';
 if(!agrees(r,old))return rows;
 const base=r?.whole_horizontal_edge?rows.map(([k,v])=>[k,(k==='\u7ba1\u5f84'||k==='Diameter')?`DN${r.nominal_mm}`:v]):rows;
 return [...receivedScopeProperties(edge,zh,c),...base];
}
export function crossViewAttributeCsvValues(edge,context=null){
 const old=prior.crossViewAttributeCsvValues(edge,context),r=checkedReceivedUniform(edge,context);
 if(!agrees(r,old))return old;
 const fill=r?.whole_horizontal_edge&&!(typeof old.diameter_nominal_mm==='number'&&old.diameter_nominal_mm>0);
 return {...old,...(fill?{diameter_nominal_mm:r.nominal_mm,diameter_text:`DN${r.nominal_mm}`,diameter_status:'native_plan_received_uniform_lower_subroute_DN'}:{}),...receivedScopeCsvValues(edge,context)};
}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...receivedScopeFields];
