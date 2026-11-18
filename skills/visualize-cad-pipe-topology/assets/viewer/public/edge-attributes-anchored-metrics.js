// Versioned facade: the original attribute reader and column contract stay exact.
import * as original from './edge-attributes.js';
import {checkedAnchoredNativeMetric,anchoredNativeMetricProperties,anchoredNativeMetricCsvFields,anchoredNativeMetricCsvValues}from'./anchored-native-plan-metrics.js';
export * from './edge-attributes.js';
export function edgeAttributeProperties(edge,data){const prior=original.edgeAttributeProperties(edge,data);return checkedAnchoredNativeMetric(edge,data?.attribute_value_context)?anchoredNativeMetricProperties(edge,prior,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context):prior;}
export function crossViewAttributeCsvValues(edge,context=null){return{...original.crossViewAttributeCsvValues(edge,context),...anchoredNativeMetricCsvValues(edge,context)};}
export const edgeAttributeCsvFields=[...original.edgeAttributeCsvFields,...anchoredNativeMetricCsvFields];
