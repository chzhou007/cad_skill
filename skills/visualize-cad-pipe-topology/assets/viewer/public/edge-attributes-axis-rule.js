import * as prior from './edge-attributes-nested-direct-axis.js';
import {axisRuleVerticalDNProperties,axisRuleVerticalDNCsvValues,axisRuleVerticalDNCsvFields} from './axis-rule-vertical-DN.js';
export * from './edge-attributes-nested-direct-axis.js';
export function edgeAttributeProperties(edge,data){return [...prior.edgeAttributeProperties(edge,data),...axisRuleVerticalDNProperties(edge,data?.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context)];}
export function crossViewAttributeCsvValues(edge,context=null){return {...prior.crossViewAttributeCsvValues(edge,context),...axisRuleVerticalDNCsvValues(edge,context)};}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...axisRuleVerticalDNCsvFields];
