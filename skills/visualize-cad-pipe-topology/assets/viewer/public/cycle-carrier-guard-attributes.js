import {checkedCycleCarrierClearance}from'./riser-header-member-attributes.js';
const hash=/^[0-9a-f]{64}$/;
function checkedRoot(context){
 const r=context?.cycle_carrier_guards,b=context?.graph_first_extensions?.source_bindings;
 if(!r||r.mode!=='native_cycle_compound_carrier_guards_v1'||r.old_graphs_and_source_values_unchanged!==true||r.original_compound_carrier_reader_reused!==true||r.original_provider_and_riser_sources_independently_replayed!==true||r.physical_lengths_assigned!==0||r.physical_member_ids_assigned!==0||r.human_accepted!==false||!hash.test(r.source_proof_sha256||'')||r.source_graph_sha256!==context.source_graph_sha256||r.rendered_graph_sha256!==context.rendered_graph_sha256||!b)return null;
 if(!['raw_axis_graph','rendered_graph','cycle_metric_proof','vertical_inheritance_proof'].every(k=>r.current_cycle_context_source_bindings?.[k]===b[k]))return null;
 if(!Array.isArray(r.records)||r.records.length!==r.held_cycle_lengths||new Set(r.records.map(x=>x.axis_edge_id)).size!==r.records.length)return null;
 return r;
}
export function isCycleCarrierHeld(edge,context){
 if(checkedCycleCarrierClearance(edge,context))return false;
 if(!context?.cycle_carrier_guards)return false;
 const root=checkedRoot(context);
 // A malformed guard cannot silently restore the old physical-length claim.
 return !root||root.records.some(r=>r.axis_edge_id===edge.edge_id);
}
export function checkedCycleCarrierGuard(edge,context){
 if(checkedCycleCarrierClearance(edge,context))return null;
 const root=checkedRoot(context);if(!root)return null;const r=root.records.find(x=>x.axis_edge_id===edge.edge_id),old=context.graph_first_extensions.cycle_records.find(x=>x.axis_edge_id===edge.edge_id);
 if(!r||!old||r.system!==edge.system||r.mapping_id!==old.mapping_id||r.plan_edge_id!==old.plan_edge_id||r.prior_complete_centerline_mm!==old.complete_horizontal_centerline_mm||r.drawing_carrier_projection_mm!==r.prior_complete_centerline_mm||!Number.isFinite(r.drawing_carrier_projection_mm)||r.drawing_carrier_projection_mm<=0||!r.barriers?.length||r.status!=='physical_member_identity_unproved'||r.complete_physical_horizontal_length_mm!==null||r.physical_correspondence_confirmed!==false||r.source_annotation_ownership_inferred!==false||r.human_accepted!==false)return null;
 return r;
}
export function cycleCarrierGuardProperties(edge,zh=true,context){
 const r=checkedCycleCarrierGuard(edge,context);if(!r)return [];
 return [[zh?'\u5e73\u9762\u6295\u5f71\u8f7d\u7ebf':'Plan drawing carrier',`09 / ${r.plan_edge_id}`],[zh?'\u56fe\u793a\u6295\u5f71\u957f\u5ea6\uff08\u7269\u7406\u6210\u5458\u672a\u786e\u8ba4\uff09':'Drawing projection; physical member unproved',`${(r.drawing_carrier_projection_mm/1000).toFixed(3)} m`],
 [zh?'\u5b8c\u6574\u7269\u7406\u6c34\u5e73\u7ba1\u957f':'Complete physical horizontal length',zh?'\u672a\u77e5\uff1b\u6682\u4e0d\u8ba1\u5165\u5b8c\u6210\u6570':'Unknown; excluded from complete count'],[zh?'\u7ba1\u5f84\u53ca\u8fde\u63a5\u8303\u56f4':'DN and connection scope',zh?'\u590d\u5408\u53e0\u7ba1\u987b\u5148\u786e\u5b9a\u6210\u5458\uff1b\u539f\u56fe\u6570\u503c\u53ca\u5019\u9009\u5bf9\u5e94\u4fdd\u7559':'Compound carrier requires member identity; original evidence retained'],
 [zh?'\u5386\u53f2\u89c4\u5219\u5c4f\u969c':'Inherited rule barrier',r.barriers.map(b=>`${b.source_LINE}: ${b.declarations.map(d=>d.handle).join(', ')}`).join('; ')]];
}
export const cycleCarrierGuardCsvFields=['cycle_carrier_hold_status','cycle_carrier_drawing_projection_mm','cycle_carrier_plan_edge','cycle_carrier_evidence_json','cycle_carrier_guard_proof_sha256'];
export function cycleCarrierGuardCsvValues(edge,context){const r=checkedCycleCarrierGuard(edge,context);return r?{cycle_carrier_hold_status:r.status,cycle_carrier_drawing_projection_mm:r.drawing_carrier_projection_mm,cycle_carrier_plan_edge:r.plan_edge_id,cycle_carrier_evidence_json:JSON.stringify(r),cycle_carrier_guard_proof_sha256:context.cycle_carrier_guards.source_proof_sha256}:{};}
