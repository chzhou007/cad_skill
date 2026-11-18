import * as prior from './edge-attributes-nested-pair-axis.js';
import {nestedDirectAxisVerticalDNProperties,nestedDirectAxisVerticalDNCsvValues,nestedDirectAxisVerticalDNCsvFields} from './nested-direct-axis-vertical-DN.js';
export * from './edge-attributes-nested-pair-axis.js';
export function edgeAttributeProperties(edge,data){return [...prior.edgeAttributeProperties(edge,data),...nestedDirectAxisVerticalDNProperties(edge,data?.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context)];}
export function crossViewAttributeCsvValues(edge,context=null){return {...prior.crossViewAttributeCsvValues(edge,context),...nestedDirectAxisVerticalDNCsvValues(edge,context)};}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...nestedDirectAxisVerticalDNCsvFields];
