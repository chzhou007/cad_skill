import * as prior from './edge-attributes-omission-vertical.js';
import {continuousAxisVerticalDNProperties,continuousAxisVerticalDNCsvValues,continuousAxisVerticalDNCsvFields} from './continuous-axis-vertical-DN.js';
export * from './edge-attributes-omission-vertical.js';
export function edgeAttributeProperties(edge,data){return [...prior.edgeAttributeProperties(edge,data),...continuousAxisVerticalDNProperties(edge,data?.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context)];}
export function crossViewAttributeCsvValues(edge,context=null){return {...prior.crossViewAttributeCsvValues(edge,context),...continuousAxisVerticalDNCsvValues(edge,context)};}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...continuousAxisVerticalDNCsvFields];
