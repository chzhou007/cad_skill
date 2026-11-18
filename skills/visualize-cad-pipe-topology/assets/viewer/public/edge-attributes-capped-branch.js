import * as prior from './edge-attributes-received-scope.js';
import {cappedBranchProperties,cappedBranchCsvValues,cappedBranchFields} from './capped-branch-correspondence.js';
export * from './edge-attributes-received-scope.js';
export function edgeAttributeProperties(edge,data){return [...cappedBranchProperties(edge,data?.attribute_value_context,data?.display?.edge_attribute_language==='zh-CN'),...prior.edgeAttributeProperties(edge,data)];}
export function crossViewAttributeCsvValues(edge,context=null){return {...prior.crossViewAttributeCsvValues(edge,context),...cappedBranchCsvValues(edge,context)};}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...cappedBranchFields];
