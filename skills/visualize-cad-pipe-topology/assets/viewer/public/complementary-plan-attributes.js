const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),hash=/^[0-9a-f]{64}$/;
const positive=v=>typeof v==='number'&&Number.isFinite(v)&&v>0;
export function checkedComplementaryPlanAttribute(edge,context){
 const root=context?.complementary_plan_attributes,b=root?.source_bindings;
 if(root?.mode!=='qualified_complementary_plan_attributes_v1'||root.complete_corrected_parent_replayed!==true||root.current_T_and_original_metric_owners_reused!==true||root.all_historical_main_roles_reapplied!==true||root.source_graphs_mutated!==false||root.vertical_values_assigned!==0||root.installed_lengths_assigned!==0||root.human_accepted!==false||!b||!Object.values(b).every(v=>hash.test(v||''))||b.raw_axis_graph!==context.source_graph_sha256||b.rendered_graph!==context.current_rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.count)return null;
 const r=root.records.find(r=>r.axis_edge_id===edge.edge_id);if(!r)return null;
 if(r.system!==edge.system||r.floor!==(edge.floor_start??edge.start_floor)||r.floor!==(edge.floor_end??edge.end_floor)||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||!positive(r.complete_horizontal_centerline_mm)||r.projection?.value_mm!==r.complete_horizontal_centerline_mm||!r.projection.pieces?.length||r.projection.pieces.some(p=>!positive(p.length_mm))||Math.abs(r.projection.pieces.reduce((s,p)=>s+p.length_mm,0)-r.complete_horizontal_centerline_mm)>.0001||r.human_accepted!==false||r.related_HIL_confirmation_inherited!==false||r.physical_installed_length_mm!==null||r.net_pipe_cut_length_mm!==null||r.source_paths_mutated!==false||r.unknown_length_filled_with_zero!==false||r.DN_used_for_matching!==false||r.actual_current_T_DN_owner_reapplied!==true||r.original_metric_readers_reused!==true||r.axis_labels_used_to_choose_horizontal_DN!==false||r.vertical_values_assigned!==0||r.source_graphs_mutated!==false)return null;
 const binding=r.source_bindings,dn=r.plan_DN_record,relation=r.original_correspondence;
 if(!binding||!Object.values(binding).every(v=>hash.test(v||''))||binding.axis_graph!==b.native_axis_graph||binding.parent_proof!==b.native_parent_proof||dn?.nominal_mm!==r.nominal_mm||dn?.status!==r.DN_status||dn?.system!==r.system||dn?.edge_id!==r.plan_edge_id||!same(dn?.scope_paths,r.plan_attribute_paths)||relation?.axis_edge_id!==r.axis_edge_id||relation?.source_detail_difference!==false||relation?.attribute_adoption_allowed!==true)return null;
 if(r.nominal_mm!==null&&(!positive(r.nominal_mm)||!['direct_plan_DN','T_through_inherited_plan_DN','T_branch_inherited_plan_DN','reviewed_plan_DN_scope'].includes(r.DN_status)))return null;
 if(r.nominal_mm===null&&!['conflict','unresolved','source_scope_unverified','annotation_blocked'].includes(r.DN_status))return null;
 return r;
}
export function complementaryPlanProperties(edge,prior,zh,context){
 const r=checkedComplementaryPlanAttribute(edge,context);if(!r)return prior;
 const label=(a,b)=>zh?a:b,dnKey=label('\u7ba1\u5f84','Pipe diameter'),lengthKey=label('\u5b8c\u6574\u6c34\u5e73\u4e2d\u5fc3\u7ebf\u957f\u5ea6','Complete horizontal centreline');
 const rows=prior.filter(([key])=>![dnKey,lengthKey].includes(key));
 const candidates=(r.plan_DN_record.lineage||[]).map(x=>'DN'+x.nominal_mm).join(' / ');
 rows.unshift([dnKey,r.nominal_mm===null?label('\u5f85\u6838\uff1a','Unresolved: ')+candidates:'DN'+r.nominal_mm]);
 rows.push([lengthKey,`${(r.complete_horizontal_centerline_mm/1000).toFixed(3)} m`],
 [label('\u5e73\u9762\u6765\u6e90','Plan source'),`${String(r.floor+7).padStart(2,'0')} / ${r.plan_edge_id}`],
 [label('\u7ba1\u5f84\u4f9d\u636e','Diameter evidence'),r.nominal_mm===null?label('\u5e73\u9762\u6807\u6ce8\u7ee7\u627f\u51b2\u7a81\uff1b\u4fdd\u7559\u5404\u5019\u9009\u4e0e\u6765\u6e90','Conflicting native plan declarations; sources retained'):label('\u539f\u5e73\u9762\u6807\u6ce8\u53ca\u5df2\u9a8c\u8bc1T\u8282\u70b9\u7ee7\u627f','Native plan annotation and verified T inheritance')],
 [label('\u5143\u4ef6\u6838\u5bf9','Component check'),label('\u539f\u56fe\u9600\u4ef6\u5df2\u8865\u9f50\uff1b','Native source valves recovered; ')+r.ordered_native_component_pairs.length+label('\u7ec4\u987a\u5e8f\u5bf9\u5e94',' ordered pairs')],
 [label('\u957f\u5ea6\u8303\u56f4','Length scope'),label('\u5b8c\u6574\u6c34\u5e73\u4e2d\u5fc3\u7ebf\uff1b\u5b89\u88c5\u53ca\u51c0\u4e0b\u6599\u957f\u5ea6\u4ecd\u672a\u77e5','Complete horizontal centreline; installed and net cut lengths unknown')]);
 return rows;
}
export const complementaryPlanCsvFields=['complementary_mapping_id','complementary_plan_edge','complementary_plan_DN_mm','complementary_plan_DN_status','complementary_plan_centerline_mm','complementary_plan_source_sha256','complementary_plan_graph_sha256','complementary_evidence_json'];
export function complementaryPlanCsvValues(edge,context){const r=checkedComplementaryPlanAttribute(edge,context);if(!r)return{};return{
 ...(r.nominal_mm===null?{}:{diameter_nominal_mm:r.nominal_mm,diameter_text:'DN'+r.nominal_mm,diameter_status:'source_checked_current_T_plan_DN'}),
 complementary_mapping_id:r.source_scope_id,complementary_plan_edge:r.plan_edge_id,complementary_plan_DN_mm:r.nominal_mm??'',complementary_plan_DN_status:r.DN_status,
 complementary_plan_centerline_mm:r.complete_horizontal_centerline_mm,complementary_plan_source_sha256:r.source_bindings.plan_source,complementary_plan_graph_sha256:r.source_bindings.plan_graph,complementary_evidence_json:JSON.stringify(r)};}
