import * as prior from './edge-attributes-complementary.js';
import{anchoredTerminalBranchProperties,anchoredTerminalBranchCsvFields,anchoredTerminalBranchCsvValues}from'./anchored-terminal-branches.js';
export * from './edge-attributes-complementary.js';
export function edgeAttributeProperties(edge,data){return anchoredTerminalBranchProperties(edge,prior.edgeAttributeProperties(edge,data),data?.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context);}
export function crossViewAttributeCsvValues(edge,context=null){return{...prior.crossViewAttributeCsvValues(edge,context),...anchoredTerminalBranchCsvValues(edge,context)};}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...anchoredTerminalBranchCsvFields];
