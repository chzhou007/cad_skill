import {checkedUniformSubrouteDN,uniformSubrouteDNProperties,uniformSubrouteDNCsvValues,uniformSubrouteDNCsvFields} from './reviewed-uniform-subroute-DN.js';
import {expressionGroupMetricProperties,expressionGroupMetricCsvValues,expressionGroupMetricCsvFields} from './reviewed-expression-group-metrics.js';
const uc=c=>c?.received_scope_uniform_DN?{...c,reviewed_uniform_subroute_DN:c.received_scope_uniform_DN}:null;
const mc=c=>c?.received_scope_group_metrics?{...c,reviewed_expression_group_metrics:c.received_scope_group_metrics}:null;
const rename=(v,a,b)=>Object.fromEntries(Object.entries(v).map(([k,x])=>[k.replace(a,b),x]));
export const receivedUniformFields=uniformSubrouteDNCsvFields.map(k=>k.replace('uniform_subroute_DN_','received_scope_uniform_DN_'));
export const receivedMetricFields=expressionGroupMetricCsvFields.map(k=>k.replace('shared_plan_metric_','received_scope_metric_'));
export const receivedScopeFields=[...receivedUniformFields,...receivedMetricFields,'received_scope_direction_hold_json'];
export function checkedReceivedUniform(edge,context){const c=uc(context);return c?checkedUniformSubrouteDN(edge,c):null;}
export function receivedScopeProperties(edge,zh,context){
 const u=uc(context),m=mc(context),hold=context?.received_scope_direction_holds?.find(r=>r.edge_id===edge.edge_id);
 return [...(u?uniformSubrouteDNProperties(edge,zh,u):[]),...(m?expressionGroupMetricProperties(edge,zh,m):[]),
  ...(hold?[[zh?'\u65b9\u5411\u6838\u9a8c\u4fdd\u7559':'Direction evidence retained',zh?'\u8be5\u6e90\u7247\u6bb5\u65b9\u5411\u672a\u786e\u5b9a\uff1b\u539f\u9650\u503c\u4fdd\u6301\uff0c\u672a\u91c7\u7528\u65b0\u7684\u5e73\u9762\u7ba1\u5f84':'Unresolved source direction; original threshold retained; new plan DN withheld']]:[])];
}
export function receivedScopeCsvValues(edge,context){
 const u=uc(context),m=mc(context),hold=context?.received_scope_direction_holds?.find(r=>r.edge_id===edge.edge_id);
 return {...(u?rename(uniformSubrouteDNCsvValues(edge,u),'uniform_subroute_DN_','received_scope_uniform_DN_'):{}),
  ...(m?rename(expressionGroupMetricCsvValues(edge,m),'shared_plan_metric_','received_scope_metric_'):{}),
  ...(hold?{received_scope_direction_hold_json:JSON.stringify(hold)}:{})};
}
