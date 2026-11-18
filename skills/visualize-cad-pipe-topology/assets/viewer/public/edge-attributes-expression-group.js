import * as prior from './edge-attributes-reviewed-ring.js';
import {expressionGroupMetricProperties,expressionGroupMetricCsvValues,expressionGroupMetricCsvFields} from './reviewed-expression-group-metrics.js';
export * from './edge-attributes-reviewed-ring.js';
export function edgeAttributeProperties(edge,data){return [...prior.edgeAttributeProperties(edge,data),...expressionGroupMetricProperties(edge,data?.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context)];}
export function crossViewAttributeCsvValues(edge,context=null){return {...prior.crossViewAttributeCsvValues(edge,context),...expressionGroupMetricCsvValues(edge,context)};}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...expressionGroupMetricCsvFields];
