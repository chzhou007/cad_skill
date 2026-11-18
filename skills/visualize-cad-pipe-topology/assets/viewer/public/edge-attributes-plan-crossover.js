import * as prior from './edge-attributes-axis-rule.js';
import {planCrossoverCentrelineProperties,planCrossoverCentrelineCsvValues,planCrossoverCentrelineCsvFields} from './plan-crossover-centreline.js';
export * from './edge-attributes-axis-rule.js';
export function edgeAttributeProperties(edge,data){return [...prior.edgeAttributeProperties(edge,data),...planCrossoverCentrelineProperties(edge,data?.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context)];}
export function crossViewAttributeCsvValues(edge,context=null){return {...prior.crossViewAttributeCsvValues(edge,context),...planCrossoverCentrelineCsvValues(edge,context)};}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...planCrossoverCentrelineCsvFields];
