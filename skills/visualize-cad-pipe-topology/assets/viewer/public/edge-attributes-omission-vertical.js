import * as prior from './edge-attributes-terminal-branches.js';
import {omissionVerticalDNCsvFields} from './omission-vertical-DN.js';
export * from './edge-attributes-terminal-branches.js';
// Keep the complete published export prefix, including all later providers.
export const edgeAttributeCsvFields=[...prior.edgeAttributeCsvFields.filter(k=>!omissionVerticalDNCsvFields.includes(k)),...omissionVerticalDNCsvFields];
