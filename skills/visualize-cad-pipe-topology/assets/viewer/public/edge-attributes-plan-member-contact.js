import * as prior from './edge-attributes-inherited-entries.js';
import {planMemberContactProperties,planMemberContactCsvValues}from'./plan-member-contact-routes.js';
export * from './edge-attributes-inherited-entries.js';
export function edgeAttributeProperties(edge,data){return planMemberContactProperties(edge,prior.edgeAttributeProperties(edge,data),data?.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context);}
export function crossViewAttributeCsvValues(edge,context=null){return {...prior.crossViewAttributeCsvValues(edge,context),...planMemberContactCsvValues(edge,context)};}
