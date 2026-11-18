import * as prior from './edge-attributes-capped-branch.js';
import {boundaryBranchProperties,boundaryBranchCsvValues,boundaryBranchFields} from './nonnode-boundary-branches.js';
export * from './edge-attributes-capped-branch.js';
export function edgeAttributeProperties(edge,data){return [...boundaryBranchProperties(edge,data?.attribute_value_context,data?.display?.edge_attribute_language==='zh-CN'),...prior.edgeAttributeProperties(edge,data)];}
export function crossViewAttributeCsvValues(edge,context=null){return {...prior.crossViewAttributeCsvValues(edge,context),...boundaryBranchCsvValues(edge,context)};}
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields,...boundaryBranchFields];
