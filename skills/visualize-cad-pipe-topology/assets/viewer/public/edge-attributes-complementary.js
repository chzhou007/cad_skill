import * as prior from './edge-attributes-two-arm.js';
import{complementaryPlanProperties,complementaryPlanCsvFields,complementaryPlanCsvValues}from'./complementary-plan-attributes.js';
export * from './edge-attributes-two-arm.js';
export function edgeAttributeProperties(edge,data){return complementaryPlanProperties(edge,prior.edgeAttributeProperties(edge,data),data?.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context);}
export function crossViewAttributeCsvValues(edge,context=null){return{...prior.crossViewAttributeCsvValues(edge,context),...complementaryPlanCsvValues(edge,context)};}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...complementaryPlanCsvFields];
