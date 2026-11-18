import {isCycleCarrierHeld}from'./cycle-carrier-guard-attributes.js';
const hash=/^[0-9a-f]{64}$/;
const positive=v=>typeof v==='number'&&Number.isFinite(v)&&v>0;
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function checkedRoot(context){
 const r=context?.graph_first_extensions,b=r?.source_bindings;
 if(r?.mode!=='qualified_graph_first_attribute_extensions_v1'||r.old_contexts_preserved!==true||r.raw_axis_graph_unchanged!==true||r.DN_values_assigned_to_horizontal!==0||r.whole_edge_vertical_DN_assigned!==0||r.physical_installed_lengths_assigned!==0||r.human_accepted!==false||!b)return null;
 if(![b.raw_axis_graph,b.rendered_graph,b.cycle_metric_proof,b.vertical_inheritance_proof,r.axis_source_sha256,r.plan_source_sha256].every(x=>hash.test(x||''))||b.raw_axis_graph!==context.source_graph_sha256||b.rendered_graph!==context.rendered_graph_sha256)return null;
 if(!Array.isArray(r.cycle_records)||r.cycle_records.length!==r.cycle_intervals||new Set(r.cycle_records.map(x=>x.axis_edge_id)).size!==r.cycle_intervals||!Array.isArray(r.vertical_records)||r.vertical_records.length!==r.new_vertical_DN_domains||new Set(r.vertical_records.map(x=>`${x.edge_id}:${x.path_index}:${x.segment_index}`)).size!==r.new_vertical_DN_domains)return null;
 return r;
}
export function checkedCycleGateRun(edge,context=null){
 if(isCycleCarrierHeld(edge,context))return null;
 const root=checkedRoot(context);if(!root)return null;const r=root.cycle_records.find(x=>x.axis_edge_id===edge.edge_id);if(!r)return null;
 if(r.system!==edge.system||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||r.floor!==(edge.floor_start??edge.start_floor)||r.floor!==(edge.floor_end??edge.end_floor)||r.nominal_mm!==null||r.DN_status!=='unknown_pending_plan_DN_scope_resolution'||!positive(r.complete_horizontal_centerline_mm)||r.human_accepted!==false||r.related_HIL_confirmation_inherited!==false||r.physical_installed_length_mm!==null||r.net_pipe_cut_length_mm!==null||r.source_paths_mutated!==false||r.unknown_length_filled_with_zero!==false||r.DN_used_for_matching!==false)return null;
 const p=r.projection;if(p?.value_mm!==r.complete_horizontal_centerline_mm||p.installed_whole_edge_length_mm!==null||!p.pieces?.length||p.pieces.some(x=>!positive(x.length_mm))||Math.abs(p.pieces.reduce((s,x)=>s+x.length_mm,0)-p.value_mm)>.0001)return null;
 return r;
}
export function checkedInheritedVerticalDN(edge,context=null){
 const root=checkedRoot(context);if(!root)return [];const rows=root.vertical_records.filter(x=>x.edge_id===edge.edge_id);
 if(rows.some(r=>{const s=r.seed_record,b=r.continuity_evidence?.bends,g=r.annotation_guard;return !positive(r.nominal_mm)||r.system!==edge.system||!Number.isInteger(r.path_index)||!Number.isInteger(r.segment_index)||!same(edge.attribute_paths?.[r.path_index]?.slice(r.segment_index,r.segment_index+2),r.scope_points)||r.axis_source_sha256!==root.axis_source_sha256||r.whole_edge_DN_assigned!==false||r.physical_length_mm!==null||r.whole_edge_physical_length_mm!==null||r.human_accepted!==false||r.related_HIL_confirmation_inherited!==false||s?.edge_id!==edge.edge_id||s.path_index!==r.path_index||s.system!==r.system||s.nominal_mm!==r.nominal_mm||!same(edge.attribute_paths?.[s.path_index]?.slice(s.segment_index,s.segment_index+2),s.scope_points)||!s.observations?.length||s.observations.some(o=>o.nominal_mm!==r.nominal_mm||o.source_text?.source_sha256!==root.axis_source_sha256)||!b?.length||b.some(x=>x.source_arms!==2||x.physical_T_crossed!==false)||!g||g.other_in_scope_DN_annotations?.length!==0||g.F_crossings?.length!==0;}))return [];
 return rows;
}
export function cycleGateRunProperties(edge,zh=true,context=null){
 const r=checkedCycleGateRun(edge,context);if(!r)return [];
 return [[zh?'\u7ba1\u5f84':'Pipe diameter',zh?'\u672a\u77e5\uff1b\u5e73\u9762DN200\uff0fDN300\u5206\u533a\u5f85\u786e\u8ba4':'Unknown; plan DN scope unresolved'],[zh?'\u697c\u5c42\u4f4d\u7f6e':'Floor',`${r.floor}F`],
 [zh?'\u5b8c\u6574\u6c34\u5e73\u4e2d\u5fc3\u7ebf\u957f\u5ea6':'Complete horizontal centreline',`${(r.complete_horizontal_centerline_mm/1000).toFixed(3)} m`],
 [zh?'\u5bf9\u5e94\u5e73\u9762\u7ba1\u6bb5':'Matched floor-plan edge',`09 / ${r.plan_edge_id}`],
 [zh?'\u5bf9\u5e94\u4f9d\u636e':'Correspondence basis',zh?'\u5df2\u77e5\u951a\u70b9\u3001\u73af\u8def\u5165\u53e3\u4e09\u901a\u4e0e\u539f\u751f\u7ba1\u6bb5\u5171\u540c\u6838\u9a8c':'Known anchors, cycle gates and native intervals checked'],
 [zh?'\u957f\u5ea6\u6765\u6e90':'Length evidence',r.projection.pieces.map(p=>`${p.plan_edge} / ${p.source_line_handle}`).join('; ')],
 [zh?'\u5b89\u88c5\u957f\u5ea6\uff0f\u51c0\u4e0b\u6599\u957f\u5ea6':'Installed / net cut length',zh?'\u672a\u77e5\uff1b\u4e2d\u5fc3\u7ebf\u957f\u5ea6\u5305\u542b\u5df2\u7ed8\u5143\u4ef6\u8303\u56f4':'Unknown; centreline includes drawn assembly extents']];
}
export function inheritedVerticalDNProperties(edge,zh=true,context=null){
 const rows=checkedInheritedVerticalDN(edge,context),out=[];
 for(const r of rows){out.push([zh?'\u7ad6\u76f4\u533a\u95f4\u7ba1\u5f84\uff0811\u56fe\u7ee7\u627f\uff09':'Inherited vertical DN (axis)',`DN${r.nominal_mm} / ${r.path_index}:${r.segment_index}`],
 [zh?'\u7ee7\u627f\u4f9d\u636e':'Inheritance evidence',`${r.seed_record.observations.map(o=>o.source_text.handle).join('; ')} -> ${r.seed_record.path_index}:${r.seed_record.segment_index} -> ${r.path_index}:${r.segment_index}`]);}
 if(rows.length)out.push([zh?'\u7ee7\u627f\u533a\u95f4\u7269\u7406\u957f\u5ea6':'Inherited segment physical length',zh?'\u672a\u77e5\uff1b\u4ec5\u786e\u8ba4\u7ba1\u5f84\uff0c\u4e0d\u4f7f\u7528\u5e73\u9762\u6216\u8f74\u6d4b\u753b\u7ebf\u957f\u5ea6':'Unknown; DN only, no drawing-span length']);return out;
}
export const graphFirstExtensionCsvFields=['cycle_gate_mapping_id','cycle_gate_plan_edge','cycle_gate_complete_centerline_mm','cycle_gate_DN_status','cycle_gate_plan_source_sha256','cycle_gate_evidence_json','unbranched_vertical_DN_segment_count','unbranched_vertical_DN_segments_json','unbranched_vertical_DN_source_sha256'];
export function graphFirstExtensionCsvValues(edge,context=null){
 const r=checkedCycleGateRun(edge,context),rows=checkedInheritedVerticalDN(edge,context),out={};
 if(r)Object.assign(out,{cycle_gate_mapping_id:r.mapping_id,cycle_gate_plan_edge:r.plan_edge_id,cycle_gate_complete_centerline_mm:r.complete_horizontal_centerline_mm,cycle_gate_DN_status:r.DN_status,cycle_gate_plan_source_sha256:context.graph_first_extensions.plan_source_sha256,cycle_gate_evidence_json:JSON.stringify(r)});
 if(rows.length)Object.assign(out,{unbranched_vertical_DN_segment_count:rows.length,unbranched_vertical_DN_segments_json:JSON.stringify(rows),unbranched_vertical_DN_source_sha256:context.graph_first_extensions.axis_source_sha256});return out;
}
