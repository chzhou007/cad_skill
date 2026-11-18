import * as prior from './edge-attributes-continuous-axis.js';
import {nestedPairAxisVerticalDNProperties,nestedPairAxisVerticalDNCsvValues,nestedPairAxisVerticalDNCsvFields} from './nested-pair-axis-vertical-DN.js';
export * from './edge-attributes-continuous-axis.js';
export function edgeAttributeProperties(edge,data){return [...prior.edgeAttributeProperties(edge,data),...nestedPairAxisVerticalDNProperties(edge,data?.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context)];}
export function crossViewAttributeCsvValues(edge,context=null){return {...prior.crossViewAttributeCsvValues(edge,context),...nestedPairAxisVerticalDNCsvValues(edge,context)};}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...nestedPairAxisVerticalDNCsvFields];
