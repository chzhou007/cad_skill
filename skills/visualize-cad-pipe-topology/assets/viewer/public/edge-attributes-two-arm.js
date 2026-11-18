import * as prior from './edge-attributes-anchored-metrics.js';
import {twoArmExternalProperties,twoArmExternalCsvFields,twoArmExternalCsvValues}from'./two-arm-external-routes.js';
export * from './edge-attributes-anchored-metrics.js';
export function edgeAttributeProperties(edge,data){return twoArmExternalProperties(edge,prior.edgeAttributeProperties(edge,data),data?.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context);}
export function crossViewAttributeCsvValues(edge,context=null){return{...prior.crossViewAttributeCsvValues(edge,context),...twoArmExternalCsvValues(edge,context)};}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...twoArmExternalCsvFields];
