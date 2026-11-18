import {checkedPlanSegments} from './upper-floor-plan-segments.js';
const hash=/^[0-9a-f]{64}$/;
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function checkedCurrentNamedPrefix(edge){
 const rows=checkedPlanSegments(edge),s=edge.current_named_prefix_source_evidence;
 if(!rows||!s)return null;
 const old=rows[0];
 if(s.mode!=='current_named_upper_prefix_evidence_fusion_v1'||s.status!=='current_named_upper_prefix_source_checked_hil_pending'||s.axis_edge!==edge.edge_id||s.mapping_id!==old.mapping_id||s.floor!==old.floor||s.system!==edge.system||s.system!==old.system||!same(s.plan_edges,old.plan_edges))return null;
 if(!['source_sha256','current_plan_graph_sha256','historical_plan_graph_sha256','historical_attribute_scope_sha256','original_mapping_sha256','native_prefix_bridge_sha256','complete_parent_graph_sha256'].every(k=>hash.test(s[k]||'')))return null;
 if(s.source_sha256!==old.source_sha256.plan||s.historical_plan_graph_sha256!==old.local_graph_sha256.plan||s.historical_attribute_scope_sha256!==old.source_scope_sha256||s.original_mapping_sha256!==old.mapping_sha256||s.current_plan_graph_sha256===s.historical_plan_graph_sha256)return null;
 if(s.native_DN_XY_and_source_paths_preserved!==true||[s.values_replaced,s.related_HIL_confirmation_inherited,s.physical_ports_verified,s.human_accepted].some(v=>v!==false))return null;
 return s;
}
export function currentNamedPrefixProperties(edge,zh=true){
 const s=checkedCurrentNamedPrefix(edge);if(!s)return [];
 return [[zh?'\u5f53\u524d\u5e73\u9762\u6e90\u56fe\u590d\u6838':'Current plan source verification',`${s.floor}F / ${s.mapping_id}`],
  [zh?'\u590d\u6838\u8303\u56f4':'Verification scope',zh?'\u65e2\u6709\u7ba1\u6bb5\u3001\u4e09\u901a\u3001\u7ba1\u5f84\u7ee7\u627f\u53ca\u6e90\u7ebfXY\u4fdd\u6301\u4e00\u81f4\uff1b\u4eba\u5de5\u9a8c\u6536\u5f85\u5b8c\u6210':'Existing pipe scopes, Ts, DN lineage and source XY unchanged; human acceptance pending'],
  [zh?'\u5f53\u524d\u5e73\u9762\u7248\u672c':'Current plan graph',s.current_plan_graph_sha256.slice(0,12)],
  [zh?'\u539f\u5e73\u9762\u7248\u672c':'Historical plan graph',s.historical_plan_graph_sha256.slice(0,12)],
  [zh?'\u6765\u6e90\u590d\u6838\u4f9d\u636e':'Native preservation proof',s.native_prefix_bridge_sha256.slice(0,12)]];
}
export const currentNamedPrefixCsvFields=['named_prefix_mapping_id','named_prefix_current_plan_graph_sha256','named_prefix_historical_plan_graph_sha256','named_prefix_native_bridge_sha256','named_prefix_source_status'];
export function currentNamedPrefixCsvValues(edge){
 const s=checkedCurrentNamedPrefix(edge);if(!s)return {};
 return {named_prefix_mapping_id:s.mapping_id,named_prefix_current_plan_graph_sha256:s.current_plan_graph_sha256,named_prefix_historical_plan_graph_sha256:s.historical_plan_graph_sha256,named_prefix_native_bridge_sha256:s.native_prefix_bridge_sha256,named_prefix_source_status:s.status};
}
