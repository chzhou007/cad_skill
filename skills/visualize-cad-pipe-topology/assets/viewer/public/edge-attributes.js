import {omissionVerticalDNProperties,omissionVerticalDNCsvValues,omissionVerticalDNCsvFields} from './omission-vertical-DN.js';
import {componentInventoryAttributeScope} from './component-inventory-attribute-bridge.js';
import {checkedContactOwnerPath,contactOwnerPathProperties,contactOwnerPathCsvValues,contactOwnerPathCsvFields} from './contact-owner-plan-attributes.js';
import {checkedCohortMember,cohortMemberProperties,cohortMemberCsvValues,cohortMemberCsvFields} from './cohort-member-plan-attributes.js';
import {checkedRiserHeaderMember,riserHeaderMemberProperties,riserHeaderCsvValues,riserHeaderCsvFields}from'./riser-header-member-attributes.js';
import {checkedCycleCarrierGuard,cycleCarrierGuardProperties,cycleCarrierGuardCsvValues,cycleCarrierGuardCsvFields}from'./cycle-carrier-guard-attributes.js';
import {checkedCycleGateRun,cycleGateRunProperties,inheritedVerticalDNProperties,graphFirstExtensionCsvValues,graphFirstExtensionCsvFields} from './graph-first-attribute-extensions.js';
import {checkedOrderedOwnerRun,orderedOwnerRunProperties,orderedOwnerRunCsvValues,orderedOwnerRunCsvFields} from './ordered-owner-plan-runs.js';
import {checkedBoundedMain,boundedMainProperties,boundedMainCsvValues,boundedMainCsvFields} from './anchor-bounded-main-attributes.js';
import {checkedOrderedBranch,orderedBranchProperties,orderedBranchCsvValues,orderedBranchCsvFields} from './ordered-branch-plan-attributes.js';
import {checkedCompoundBridge,compoundBridgeProperties,compoundBridgeCsvValues,compoundBridgeCsvFields,axisVerticalSegmentProperties,axisVerticalSegmentCsvValues,axisVerticalSegmentCsvFields,checkedCompoundInterface,compoundInterfaceProperties,compoundInterfaceCsvValues,compoundInterfaceCsvFields,checkedNoncompoundMainExtent,noncompoundMainExtentProperties,noncompoundMainExtentCsvValues,noncompoundMainExtentCsvFields,hasCompoundMemberScope,checkedCompoundMember,compoundMemberProperties,compoundMemberCsvValues,compoundMemberCsvFields,checkedBatchPlanScope,batchPlanProperties,reconcileBatchPlanCsvValues,batchPlanCsvFields,memberPlanRunProperties,memberPlanRunCsvValues,memberPlanRunCsvFields,orderedGroupRunProperties,orderedGroupRunCsvValues,orderedGroupRunCsvFields} from './full-batch-plan-attributes.js';
import {currentNamedPrefixProperties,currentNamedPrefixCsvValues,currentNamedPrefixCsvFields} from './current-named-prefix-evidence.js';
import {checkedExternalFeed,externalFeedProperties,externalFeedCsvValues,externalFeedCsvFields} from './external-feed-plan-attributes.js';
import {axisRiserAttributeProperties,axisRiserAttributeCsvValues,axisRiserAttributeCsvFields} from './axis-riser-attributes.js';
import {checkedPlanSegments,planSegmentProperties,planSegmentCsvValues,planSegmentCsvFields} from './upper-floor-plan-segments.js';
import {currentPlanScopeProperties,currentPlanScopeCsvValues,currentPlanScopeCsvFields} from './current-plan-scope-attributes.js';
import {checkedAnchoredMain,anchoredMainProperties,anchoredMainCsvValues,anchoredMainCsvFields} from './anchored-floor-main-attributes.js';
import {currentFloorPlanScopeProperties,currentFloorPlanScopeCsvValues,currentFloorPlanScopeCsvFields} from './current-floor-plan-scopes.js';

import {checkedAliasMemberInterface,aliasMemberInterfaceProperties,aliasMemberInterfaceCsvValues,aliasMemberInterfaceCsvFields} from './alias-member-interface-attributes.js';
import {checkedAliasMemberBridge,aliasMemberBridgeProperties,aliasMemberBridgeCsvValues,aliasMemberBridgeCsvFields} from './alias-member-bridge-attributes.js';

export function waveOmissionDescription(edge){
 if(!edge.source_wave_omission)return null;
 const confirmed=edge.source_wave_omission.scoped_expert_convention_confirmed===true||edge.connection_mode==='expert_confirmed_wave_schematic_continuity';
 return confirmed?'\u957f\u7ba1\u7701\u7565\u753b\u6cd5\uff1b\u7ba1\u8def\u8fde\u7eed\uff0c\u5b9e\u9645\u957f\u5ea6\u672a\u77e5':'\u6ce2\u6d6a\u7701\u7565\u8fde\u63a5\u5019\u9009\uff1b\u8fde\u901a\u5f85\u6838\uff0c\u5b9e\u9645\u957f\u5ea6\u672a\u77e5';
}
export function nodeFloorRepairProperties(node,data){
 const r=node.source_floor_reconciliation;
 if(!r||r.status!=='source_main_caption_floor_label_reconciled'||node.node_id!==r.node_id||node.floor!==r.to_floor||r.physical_floor_verified!==false)return [];
 const zh=data.display?.edge_attribute_language==='zh-CN';
 return [[zh?'\u697c\u5c42\u6807\u7b7e\u4fee\u590d':'Floor label correction',`${r.from_floor} \u2192 ${r.to_floor}`],
  [zh?'\u539f\u56fe\u4e3b\u7ba1\u4f9d\u636e':'Native main evidence',r.main_edge_ids.join(' / ')],
  [zh?'\u6821\u6838\u8303\u56f4':'Evidence scope',zh?'\u539f\u56fe\u4e3b\u7ba1\u4e0e\u697c\u5c42\u6807\u6ce8\u4e00\u81f4\u6027\uff1b\u8de8\u56fe\u8def\u5f84\u4ecd\u5f85\u6838':'Native main and caption consistency; cross-view paths unverified']];
}
const zhLabel={diameter:'\u7ba1\u5f84',floor:'\u697c\u5c42\u4f4d\u7f6e',source:'\u539f\u56fe\u6807\u6ce8',unknown:'\u672a\u6807\u6ce8 / \u5f85\u6838\u5b9e'};
export function upstreamJointSystemProperties(edge,zh=true){
 const records=(edge.source_inline_system_resolutions||[]).filter(r=>
  r.status==='source_colour_error_resolved_by_confirmed_upstream_rule'&&
  r.to_edge===edge.edge_id&&r.system===edge.system&&
  r.confirmation?.rule==='expert_confirmed_no_system_change_follow_upstream_main'&&
  r.confirmation?.status==='user_confirmed'&&r.source_line_handles?.length&&
  r.joint_handle&&r.upstream_tee&&r.physical_port_verified===false&&r.physical_length==='unknown');
 if(!records.length)return [];
 return [[zh?'\u8f6f\u63a5\u7cfb\u7edf\u6821\u51c6':'Joint system correction',records.map(r=>`${r.joint_handle}: ${zh?(r.system==='supply'?'\u4f9b\u6c34':'\u56de\u6c34'):r.system}; ${r.upstream_tee}`).join('; ')],
  [zh?'\u5f52\u5c5e\u4f9d\u636e':'Ownership evidence',zh?'\u4e13\u5bb6\u786e\u8ba4\u7684\u4e0a\u6e38\u4e3b\u7ba1\u89c4\u5219\uff1b\u6e90\u7ebf\u4e0e\u4e09\u901a\u5df2\u91cd\u67e5\uff0c\u539f\u56fe\u9519\u8272\u8bb0\u5f55\u4fdd\u7559':'Confirmed upstream-main rule; native route and tee rechecked; original colour conflict retained'],
  [zh?'\u5143\u4ef6\u5f52\u5c5e\u53d8\u66f4':'Component ownership history',records.map(r=>`${r.original_device_name} [${r.from_edge}] \u2192 ${r.device_name} [${r.to_edge}]`).join('; ')],
  [zh?'\u7269\u7406\u7aef\u53e3\u4e0e\u5b89\u88c5\u957f\u5ea6':'Physical port and installed length',zh?'\u7aef\u53e3\u5f85\u6838\uff1b\u5b89\u88c5\u957f\u5ea6\u672a\u77e5':'Port unverified; installed length unknown']];
}
export function checkedDetailTopology(c){
 const p=c?.horizontal_projection,ctx=p?.detail_context,hash=/^[0-9a-f]{64}$/;
 if(p?.status!=='source_confirmed_detail_topology_physical_length_unknown'||p.value_mm!==null||p.edge_value_mm!==null||p.allocation!=='unmeasured_confirmed_detail_view_not_floor_plan_metric'||c.whole_edge_physical_length_mm!==null||ctx?.physical_units_applied!==false||ctx.human_accepted!==false)return false;
 if(!hash.test(c.source_hashes?.plan||'')||!hash.test(c.source_hashes?.plan_graph||'')||ctx.plan_source_sha256!==c.source_hashes.plan||ctx.plan_graph_sha256!==c.source_hashes.plan_graph||!hash.test(ctx.confirmed_alias_root_sha256||'')||!hash.test(ctx.native_coverage_sha256||'')||JSON.stringify(ctx.plan_edges)!==JSON.stringify(c.plan_edges))return false;
 const roles=ctx.source_view_roles||[];
 return c.plan_edges?.length>0&&roles.length===c.plan_edges.length&&new Set(roles.map(r=>r.edge_id)).size===roles.length&&roles.every(r=>{
  const v=r.source_view_context;
  return c.plan_edges.includes(r.edge_id)&&v?.kind==='confirmed_detail_view'&&v.coordinate_domain==='native_detail_drawing'&&v.source_sha256===ctx.plan_source_sha256&&hash.test(v.input_graph_sha256||'')&&v.confirmed_alias_root_sha256===ctx.confirmed_alias_root_sha256&&v.physical_length_from_drawing_span===false&&v.metric_verified_by_this_stage===false;
 });
}
export function checkedPlanDiameterScope(c){
 const d=c?.diameter,hash=/^[0-9a-f]{64}$/;
 if(c?.status!=='partial_plan_attributes_source_checked'||c.human_accepted!==false||!hash.test(c.plan_DN_scope_evidence_sha256||'')||d?.plan_scope_evidence_sha256!==c.plan_DN_scope_evidence_sha256||!hash.test(c.source_hashes?.plan||'')||d.plan_drawn_status!=='source_checked_plan_DN_scope_human_pending')return null;
 const rows=d.plan_drawn_values||[],value=d.plan_drawn_nominal_mm;
 if(!Number.isFinite(value)||value<=0||!c.plan_edges?.length||rows.length!==c.plan_edges.length||new Set(rows.map(r=>r.edge_id)).size!==rows.length||rows.some(r=>!c.plan_edges.includes(r.edge_id)||r.system!==c.system||r.nominal_mm!==value||r.scope!=='native_plan_drawn_pipe_paths_only'||r.human_accepted!==false))return null;
 const detail=checkedDetailTopology(c),normal=d.status==='source_checked_whole_horizontal_main_DN';
 const junctionIds=c.junction_correspondence_ids;
 const nativeJunctionMain=c.mapping_kind==='main_between_matched_junctions'&&c.mapping_basis==='native_paired_service_junction_correspondence'&&Array.isArray(junctionIds)&&junctionIds.length>0&&new Set(junctionIds).size===junctionIds.length&&junctionIds.every(id=>typeof id==='string'&&id.trim().length>0);
 const whole=(normal||(detail&&d.status==='source_checked_whole_horizontal_main_DN_length_unknown'))&&d.selected_physical_diameter===true&&d.nominal_mm===value&&(c.mapping_kind==='main_between_equipment_branches'||nativeJunctionMain)&&c.plan_edges.length===1&&c.iso_edges?.length===1&&c.whole_axis_main_scope==='source_checked_plan_native_T_to_T_horizontal_main';
 const length=whole&&normal&&c.whole_edge_length_kind==='floor_plan_horizontal_main_centerline_route'&&c.whole_edge_length_scope==='complete_mapped_T_to_T_centerline_route_not_pipe_net_cut_length'&&c.pipe_net_cut_length_mm===null&&c.horizontal_projection?.route_scope_status==='complete_mapped_horizontal_main_centerline'&&Number.isFinite(c.whole_edge_physical_length_mm)&&c.whole_edge_physical_length_mm>0&&c.whole_edge_physical_length_mm===c.horizontal_projection?.edge_value_mm?c.whole_edge_physical_length_mm:null;
 return {value,whole,length,rows,detail};
}
export function namedRiserApproachProperties(c,zh=true){
 const context=c?.named_riser_interface_context,scoped=checkedPlanDiameterScope(c);
 if(c?.mapping_basis!=='native_named_riser_and_independent_equipment_service'||c.mapping_kind!=='named_riser_floor_approach'||!scoped||scoped.whole||!context||c.physical_ports_verified!==false||c.equipment_connector_length_mm!==null||c.whole_edge_physical_length_mm!==null||c.diameter.nominal_mm!==null||context.floor!==c.floor||context.physical_port_verified!==false||context.graphic_circle_radius_added_to_length!==false||context.whole_installed_length_mm!==null)return [];
 if(!new RegExp(c.system==='supply'?'^CHWS[1-9][0-9]*$':c.system==='return'?'^CHWR[1-9][0-9]*$':'a^').test(context.identifier)||!['plan_riser_interface','iso_riser_junction','equipment_anchor','plan_equipment_main_T','iso_equipment_main_T'].every(k=>typeof context[k]==='string'&&context[k].trim()))return [];
 return [[zh?'\u5bf9\u5e94\u4f9d\u636e':'Correspondence basis',zh?'\u547d\u540d\u7acb\u7ba1\u4e0e\u72ec\u7acb\u8bbe\u5907\u652f\u8def\u5df2\u5171\u540c\u6821\u9a8c':'Native named riser and independent equipment service checked'],
  [zh?'\u7acb\u7ba1\u7f16\u53f7':'Riser identifier',context.identifier],
  [zh?'\u7acb\u7ba1\u63a5\u53e3\u5bf9\u5e94':'Riser interface correspondence',`${context.plan_riser_interface} (plan) -> ${context.iso_riser_junction} (axis)`],
  [zh?'\u8bbe\u5907\u652f\u8def\u951a\u70b9':'Independent equipment anchor',`${context.equipment_anchor}: ${context.plan_equipment_main_T} -> ${context.iso_equipment_main_T}`],
  [zh?'\u63a5\u5165\u8def\u5f84\u957f\u5ea6\u8303\u56f4':'Approach length scope',zh?'\u5e73\u9762\u5df2\u7ed8\u8def\u5f84\uff1b\u5706\u7b26\u53f7\u534a\u5f84\u672a\u8ba1\u5165\uff1b\u6574\u8fb9\u5b89\u88c5\u957f\u5ea6\u672a\u77e5':'Drawn plan path; graphic circle radius not added; whole installed length unknown']];
}
export function crossViewAttributeProperties(edge,zh=true){
 const c=edge.cross_view_attributes;if(!c||c.status!=='partial_plan_attributes_source_checked')return [];
 const metric=c.horizontal_projection,dn=c.diameter,known=Number.isFinite(metric?.edge_value_mm)&&metric.edge_value_mm>0;
 const rows=[[zh?'\u5bf9\u5e94\u5e73\u9762\u7ba1\u6bb5':'Mapped plan edges',(c.plan_edges||[]).join(', ')],
  [zh?'\u5e73\u9762\u6c34\u5e73\u6295\u5f71\u957f\u5ea6':'Plan horizontal projection',known?`${(metric.edge_value_mm/1000).toFixed(4)} m (${metric.edge_value_mm.toFixed(1)} mm)`:(zh?'\u5bf9\u5e94\u8def\u5f84\u5408\u8ba1\uff0c\u5c1a\u672a\u5206\u914d\u5230\u672c\u8fb9':'Route total not allocated to this edge')],
  [zh?'\u957f\u5ea6\u8bc1\u636e':'Length evidence',(metric?.pieces||[]).map(p=>`${p.plan_edge} / ${p.source_line_handle}`).join('; ')],
  [zh?'\u6574\u8fb9\u7269\u7406\u957f\u5ea6':'Whole-edge physical length',zh?'\u672a\u77e5\uff1b\u4e0b\u63a5\u7ba1\u53ca\u8bbe\u5907\u63a5\u7ba1\u672a\u8865\u6210\u5b9e\u6d4b\u957f\u5ea6':'Unknown; drops and equipment connectors unmeasured'],
  [zh?'\u5e73\u9762\u7ba1\u5f84\u5019\u9009':'Plan diameter candidate',dn?.plan_candidate?`${dn.plan_candidate.text} [${dn.plan_candidate.handle}] ${zh?'\uff08\u7ee7\u627f\u5019\u9009\uff0c\u672a\u9009\u5b9a\uff09':'(inheritance candidate, unselected)'}`:(zh?'\u672a\u77e5':'Unknown')],
  [zh?'\u8f74\u6d4b\u6807\u6ce8\u5bf9\u7167':'Axis annotation comparison',dn?.axis_observation?`${dn.axis_observation.text} [${dn.axis_observation.handle}] ${zh?'\uff08\u5f52\u5c5e\u5f85\u6838\uff09':'(attribution pending)'}`:(zh?'\u672a\u77e5':'Unknown')],
  [zh?'\u8de8\u56fe\u5c5e\u6027\u72b6\u6001':'Cross-view attribute status',zh?'\u5e73\u9762\u6295\u5f71\u957f\u5ea6\u5df2\u56de\u8bc1\uff1b\u7ba1\u5f84\u53ca\u6574\u8fb9\u957f\u5ea6\u672a\u95ed\u73af':'Plan projection checked; diameter and total length unresolved']];
 if(c.axis_vertical_drawing_strokes?.length)rows.push([zh?'\u8f74\u6d4b\u7ad6\u7ebf\u8303\u56f4':'Axis vertical strokes',zh?'\u540c\u697c\u5c42\u8def\u5f84\u5185\u7684\u753b\u7ebf\uff1b\u4e0d\u6309\u8de8\u5c42\u7ba1\u957f\u53d6\u503c':'Same-floor drawing strokes; no inter-floor length assigned']);
 if(dn?.plan_candidate?.scope==='local_source_observation'){
  const row=rows.find(([key])=>key===(zh?'\u5e73\u9762\u7ba1\u5f84\u5019\u9009':'Plan diameter candidate'));
  if(row)row[1]=`${dn.plan_candidate.text} [${dn.plan_candidate.handle}] ${zh?'\uff08\u5c40\u90e8\u6807\u6ce8\uff1b\u6574\u6bb5\u5f85\u6838\uff09':'(local annotation; edge-wide scope pending)'}`;
 }
 if(c.mapping_basis==='native_source_and_main_branch_order')rows.push([zh?'\u5bf9\u5e94\u4f9d\u636e':'Correspondence basis',zh?'\u6e90\u56fe\u548c\u4e3b\u7ba1\u5206\u652f\u6b21\u5e8f\u5df2\u6821\u9a8c\uff1b\u4eba\u5de5\u9a8c\u6536\u5f85\u5b8c\u6210':'Source and main branch order checked; human acceptance pending']);
 if(c.mapping_basis==='native_paired_service_corridors')rows.push([zh?"\u5bf9\u5e94\u4f9d\u636e":'Correspondence basis',zh?"\u6210\u5bf9\u8bbe\u5907\u7684\u4f9b\u56de\u6c34\u53ca\u4e3b\u7ba1\u8def\u5f84\u5df2\u6821\u9a8c\uff1b\u4eba\u5de5\u9a8c\u6536\u5f85\u5b8c\u6210":'Paired equipment services and native main paths checked; human acceptance pending']);
 if(c.mapping_basis==='native_paired_service_junction_correspondence'){
  rows.push([zh?'\u5bf9\u5e94\u4f9d\u636e':'Correspondence basis',zh?'\u539f\u751f\u4e09\u901a\u53ca\u652f\u8def\u53bb\u5411\u5df2\u6821\u9a8c\uff1b\u5e73\u9762\u7ba1\u5f84\u548c\u957f\u5ea6\u91cd\u7b97\uff0c\u4eba\u5de5\u9a8c\u6536\u5f85\u5b8c\u6210':'Native junctions and branch targets checked; plan DN and length recomputed; human acceptance pending']);
  if(c.junction_correspondence_ids?.length)rows.push([zh?'\u5df2\u5bf9\u5e94\u4e09\u901a':'Matched native junctions',c.junction_correspondence_ids.join(' / ')]);
 }
 rows.push(...namedRiserApproachProperties(c,zh));
 const detail=checkedDetailTopology(c);
 if(detail){
  const change=(key,value)=>{const row=rows.find(([k])=>k===key);if(row)row[1]=value;};
  change(zh?'\u5e73\u9762\u6c34\u5e73\u6295\u5f71\u957f\u5ea6':'Plan horizontal projection',zh?'\u5b9e\u9645\u957f\u5ea6\u672a\u77e5\uff1b\u8be6\u56fe\u8de8\u5ea6\u4e0d\u4f5c\u4e3a\u5b9e\u9645\u7ba1\u957f':'Actual length unknown; detail drawing span is not physical pipe length');
  change(zh?'\u8de8\u56fe\u5c5e\u6027\u72b6\u6001':'Cross-view attribute status',zh?'\u53cc\u89c6\u56fe\u62d3\u6251\u5df2\u5bf9\u5e94\uff1b\u5b9e\u9645\u7ba1\u957f\u672a\u77e5':'Dual-view topology checked; actual pipe length unknown');
 }
 const scoped=checkedPlanDiameterScope(c);
 if(scoped){
  const change=(key,value)=>{const row=rows.find(([k])=>k===key);if(row)row[1]=value;};
  change(zh?'\u8de8\u56fe\u5c5e\u6027\u72b6\u6001':'Cross-view attribute status',scoped.whole?(zh?'\u6c34\u5e73\u4e3b\u7ba1\u7ba1\u5f84\u4e0e\u4e2d\u5fc3\u7ebf\u8def\u5f84\u957f\u5ea6\u5df2\u56de\u8bc1\uff1b\u4eba\u5de5\u9a8c\u6536\u5f85\u5b8c\u6210':'Horizontal main DN and centerline route checked; human acceptance pending'):(zh?'\u5e73\u9762\u5df2\u7ed8\u7ba1\u6bb5\u7ba1\u5f84\u4e0e\u6295\u5f71\u957f\u5ea6\u5df2\u56de\u8bc1\uff1b\u672a\u753b\u63a5\u7ba1\u8303\u56f4\u4ecd\u672a\u77e5':'Drawn plan pipe DN and projection checked; unseen connector extent unknown'));
  if(scoped.detail){
   change(zh?'\u8de8\u56fe\u5c5e\u6027\u72b6\u6001':'Cross-view attribute status',scoped.whole?(zh?'\u6c34\u5e73\u4e3b\u7ba1\u7ba1\u5f84\u5df2\u56de\u8bc1\uff1b\u5b9e\u9645\u957f\u5ea6\u672a\u77e5':'Horizontal main DN checked; actual length unknown'):(zh?'\u8be6\u56fe\u5df2\u7ed8\u7ba1\u5f84\u5df2\u56de\u8bc1\uff1b\u672a\u753b\u63a5\u7ba1\u8303\u56f4\u4e0e\u5b9e\u9645\u957f\u5ea6\u672a\u77e5':'Drawn detail DN checked; unseen connector extent and actual length unknown'));
  }
  if(scoped.length!==null){
   const lengthRow=rows.find(([k])=>k===(zh?'\u6574\u8fb9\u7269\u7406\u957f\u5ea6':'Whole-edge physical length'));
   if(lengthRow){lengthRow[0]=zh?'\u6c34\u5e73\u4e3b\u7ba1\u4e2d\u5fc3\u7ebf\u8def\u5f84\u957f\u5ea6':'Horizontal main centerline route length';lengthRow[1]=`${(scoped.length/1000).toFixed(4)} m (${scoped.length.toFixed(1)} mm)`;}
   rows.push([zh?'\u957f\u5ea6\u8303\u56f4':'Length scope',zh?'\u4e24\u7aef\u4e09\u901a\u4e4b\u95f4\u7684\u5e73\u9762\u4e2d\u5fc3\u7ebf\u8def\u5f84\uff1b\u672a\u6263\u5143\u4ef6\uff0c\u4e0d\u4f5c\u4e3a\u7ba1\u6750\u51c0\u4e0b\u6599\u957f\u5ea6':'Plan centerline route between Ts; components not deducted; not net pipe cut length']);
  }
  rows.push([zh?'\u5e73\u9762\u5df2\u7ed8\u7ba1\u6bb5\u7ba1\u5f84':'Drawn plan pipe diameter',`DN${scoped.value}${scoped.whole?(zh?'\uff08\u8986\u76d6\u672c\u6bb5\u6c34\u5e73\u4e3b\u7ba1\uff09':' (covers this horizontal main)'):(zh?'\uff08\u672a\u753b\u63a5\u7ba1\u7684\u6574\u8fb9\u8303\u56f4\u5f85\u5b9a\uff09':' (unseen connector extent unresolved)')}`],
   [zh?'\u5e73\u9762\u7ba1\u5f84\u7ee7\u627f\u4f9d\u636e':'Plan diameter lineage',scoped.rows.flatMap(r=>(r.lineage||[]).flatMap(l=>(l.evidence||[]).map(e=>`${e.evidence_id}: ${(e.edge_path||[]).join(' -> ')}`))).join('; ')||c.plan_DN_scope_evidence_sha256]);
 }
 return rows;
}
function legacyCrossViewAttributeCsvValues(edge,context=null){
 const c=edge.cross_view_attributes;if(!c||c.status!=='partial_plan_attributes_source_checked')return reconcileBatchPlanCsvValues(edge,{...axisRiserAttributeCsvValues(edge),...planSegmentCsvValues(edge),...anchoredMainCsvValues(edge),...externalFeedCsvValues(edge),...currentFloorPlanScopeCsvValues(edge),...currentNamedPrefixCsvValues(edge)},context);
 const value=c.horizontal_projection?.edge_value_mm,scoped=checkedPlanDiameterScope(c);
 return reconcileBatchPlanCsvValues(edge,{diameter_nominal_mm:scoped?.whole?scoped.value:'',diameter_text:scoped?.whole?`DN${scoped.value}`:'',diameter_status:'cross_view_'+c.diameter.status,
  crossview_mapping_id:c.mapping_id,crossview_plan_edges:(c.plan_edges||[]).join(';'),
  crossview_plan_horizontal_projection_mm:Number.isFinite(value)&&value>0?value:'',
  crossview_projection_allocation:c.horizontal_projection?.allocation||'',crossview_metric_status:c.horizontal_projection?.status||'',crossview_detail_context_json:checkedDetailTopology(c)?JSON.stringify(c.horizontal_projection.detail_context):'',crossview_whole_edge_length_mm:scoped?.length??'',
  crossview_whole_edge_length_kind:scoped?.length?'floor_plan_horizontal_main_centerline_route':'',
  crossview_plan_drawn_nominal_mm:scoped?.value??'',crossview_plan_DN_scope_status:scoped?c.diameter.status:'',crossview_plan_DN_scope_sha256:scoped?c.plan_DN_scope_evidence_sha256:'',
  crossview_plan_diameter_candidate_mm:c.diameter.plan_candidate?.nominal_mm??'',
  crossview_axis_diameter_observation_mm:c.diameter.axis_observation?.nominal_mm??'',
  crossview_plan_source_sha256:c.source_hashes?.plan||'',...axisRiserAttributeCsvValues(edge),...planSegmentCsvValues(edge),...currentPlanScopeCsvValues(edge),...externalFeedCsvValues(edge),...currentFloorPlanScopeCsvValues(edge),...currentNamedPrefixCsvValues(edge)},context);
}
function checkedOwnershipLengthScope(edge,data){
 const r=edge.source_layout_equipment_interface,root=data?.sourceLayoutEquipmentOwnership,mode='calibrated_ownership_preserve_source_scopes_v2';
 if(!r||r.length_scope_composition!==mode||root?.scope_composition_mode!==mode||root.prior_edge_scopes_preserved!==true||r.edge_id!==edge.edge_id||r.system!==edge.system||![edge.start_node_id,edge.end_node_id].includes(r.equipment_id)||r.human_accepted!==false||r.physical_port_verified!==false||edge.physical_length!=='unknown'||edge.path_length_complete!==false||edge.equipment_connector_length_mm!==null)return null;
 if((root.records||[]).filter(row=>JSON.stringify(row)===JSON.stringify(r)).length!==1||!r.prior_edge_length_scope||!Array.isArray(edge.length_scope_evidence))return null;
 const prior=r.prior_edge_length_scope;
 if(Object.hasOwn(prior,'path_length_scope')&&prior.path_length_scope!==edge.path_length_scope)return null;
 return {record:r,prior};
}
export function ownershipLengthScopeProperties(edge,data,zh=true){
 const s=checkedOwnershipLengthScope(edge,data);if(!s)return [];
 const descriptions={
  drawing_paths_excluding_source_crossover_gaps_physical_length_unknown:'\u5df2\u7ed8\u7ba1\u6bb5\uff1b\u8de8\u7ba1\u65ad\u53e3\u7684\u5b9e\u9645\u957f\u5ea6\u672a\u77e5',
  source_drawn_pipe_only_source_reviewed_circle_and_equipment_length_unknown:'\u5df2\u7ed8\u7ba1\u6bb5\uff1b\u5706\u5708\u63a5\u89e6\u4e0e\u8bbe\u5907\u63a5\u7ba1\u7684\u5b9e\u9645\u957f\u5ea6\u672a\u77e5',
  source_drawn_pipe_only_technical_calibrated_circle_and_equipment_length_unknown:'\u5df2\u7ed8\u7ba1\u6bb5\uff1b\u6821\u51c6\u5706\u5708\u63a5\u89e6\u4e0e\u8bbe\u5907\u63a5\u7ba1\u7684\u5b9e\u9645\u957f\u5ea6\u672a\u77e5',
  source_drawn_pipe_only_expert_confirmed_circle_and_equipment_length_unknown:'\u5df2\u7ed8\u7ba1\u6bb5\uff1b\u5706\u5708\u63a5\u89e6\u4e0e\u8bbe\u5907\u63a5\u7ba1\u7684\u5b9e\u9645\u957f\u5ea6\u672a\u77e5\uff0c\u8fde\u63a5\u5173\u7cfb\u7ecf\u786e\u8ba4',
  source_drawn_pipe_only_circle_and_crossover_lengths_unknown:'\u5df2\u7ed8\u7ba1\u6bb5\uff1b\u5706\u5708\u63a5\u89e6\u4e0e\u8de8\u7ba1\u65ad\u53e3\u7684\u5b9e\u9645\u957f\u5ea6\u672a\u77e5'};
 const scope=s.prior.path_length_scope,description=zh?(scope?(descriptions[scope]||'\u539f\u56fe\u957f\u5ea6\u8303\u56f4\u5df2\u4fdd\u7559\uff1b\u5b9e\u9645\u957f\u5ea6\u672a\u786e\u8ba4'):'\u539f\u56fe\u672a\u5355\u72ec\u7ed9\u51fa\u5b8c\u6574\u957f\u5ea6\u8303\u56f4\uff1b\u8bbe\u5907\u63a5\u7ba1\u4ecd\u672a\u77e5'):'Prior source drawing scope retained; physical omitted spans unresolved';
 return [[zh?'\u8bbe\u5907\u63a5\u53e3\u5f52\u5c5e':'Equipment interface ownership',s.record.equipment_id],
  [zh?'\u4fdd\u7559\u7684\u539f\u56fe\u957f\u5ea6\u8303\u56f4':'Retained source length scope',description],
  [zh?'\u8bbe\u5907\u63a5\u7ba1\u957f\u5ea6':'Equipment connector length',zh?'\u672a\u77e5\uff1b\u539f\u56fe\u672a\u753b\uff0c\u672a\u6309\u96f6\u8ba1\u5165':'Unknown; unshown in source, not counted as zero'],
  [zh?'\u7269\u7406\u7aef\u53e3':'Physical equipment port',zh?'\u672a\u9a8c\u8bc1\uff1b\u5f53\u524d\u4e3a\u6e90\u56fe\u652f\u6301\u7684\u903b\u8f91\u5f52\u5c5e':'Unverified; source-supported logical ownership'],
  [zh?'\u957f\u5ea6\u8303\u56f4\u8bc1\u636e':'Length scope evidence',zh?'\u539f\u6709\u65ad\u53e3/\u5706\u5708\u8bf4\u660e\u4e0e\u65b0\u589e\u63a5\u7ba1\u672a\u77e5\u72b6\u6001\u5206\u522b\u4fdd\u7559':'Prior source scope and new connector uncertainty retained separately']];
}
export function ownershipLengthScopeCsvValues(edge,data){
 const s=checkedOwnershipLengthScope(edge,data);if(!s)return {};
 return {equipment_connector_length_mm:'',equipment_connector_length_status:edge.equipment_connector_length_status,prior_length_scope:s.prior.path_length_scope||'',length_scope_evidence_json:JSON.stringify(edge.length_scope_evidence)};
}
export function crossViewAttributeCsvValues(edge,context=null){
 if(!componentInventoryAttributeScope(edge,context))return {};
 return {...legacyCrossViewAttributeCsvValues(edge,context),...memberPlanRunCsvValues(edge,context),...orderedGroupRunCsvValues(edge,context),...orderedBranchCsvValues(edge,context),...boundedMainCsvValues(edge,context),...compoundMemberCsvValues(edge,context),...noncompoundMainExtentCsvValues(edge,context),...compoundInterfaceCsvValues(edge,context),...axisVerticalSegmentCsvValues(edge,context),...compoundBridgeCsvValues(edge,context),...orderedOwnerRunCsvValues(edge,context),...aliasMemberInterfaceCsvValues(edge,context),...aliasMemberBridgeCsvValues(edge,context),...graphFirstExtensionCsvValues(edge,context),...cycleCarrierGuardCsvValues(edge,context),...riserHeaderCsvValues(edge,context),...cohortMemberCsvValues(edge,context),...contactOwnerPathCsvValues(edge,context),...omissionVerticalDNCsvValues(edge,context)};
}

export function edgeAttributeProperties(edge,data){
 if(!componentInventoryAttributeScope(edge,data?.attribute_value_context))return [];
 return [...baseEdgeAttributeProperties(edge,data),...axisVerticalSegmentProperties(edge,data.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context),...inheritedVerticalDNProperties(edge,data.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context),...omissionVerticalDNProperties(edge,data.display?.edge_attribute_language==='zh-CN',data?.attribute_value_context)];
}
function baseEdgeAttributeProperties(edge,data){
 if(checkedContactOwnerPath(edge,data?.attribute_value_context))return contactOwnerPathProperties(edge,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context);
 if(checkedCohortMember(edge,data?.attribute_value_context))return cohortMemberProperties(edge,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context);
 if(checkedRiserHeaderMember(edge,data?.attribute_value_context))return riserHeaderMemberProperties(edge,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context);
 if(checkedCycleCarrierGuard(edge,data?.attribute_value_context))return cycleCarrierGuardProperties(edge,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context);
 if(checkedCycleGateRun(edge,data?.attribute_value_context))return cycleGateRunProperties(edge,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context);
 if(checkedAliasMemberBridge(edge,data?.attribute_value_context))return aliasMemberBridgeProperties(edge,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context);
 if(checkedAliasMemberInterface(edge,data?.attribute_value_context))return aliasMemberInterfaceProperties(edge,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context);
 if(checkedOrderedOwnerRun(edge,data?.attribute_value_context))return orderedOwnerRunProperties(edge,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context);
 if(checkedCompoundBridge(edge,data?.attribute_value_context))return compoundBridgeProperties(edge,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context);
 if(checkedCompoundInterface(edge,data?.attribute_value_context))return compoundInterfaceProperties(edge,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context);
 if(checkedNoncompoundMainExtent(edge,data?.attribute_value_context))return noncompoundMainExtentProperties(edge,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context);
 if(hasCompoundMemberScope(edge,data?.attribute_value_context))return compoundMemberProperties(edge,data.display?.edge_attribute_language==='zh-CN',data.attribute_value_context);
 if(!edge.batch_plan_attribute_scopes&&!edge.external_feed_plan_attributes&&!edge.network_named_lower_plan_attributes&&!edge.anchored_floor_main_attributes&&!edge.cross_view_attributes&&!edge.plan_segment_attributes?.length&&!edge.axis_riser_attributes?.length&&!edge.pipe_diameter&&!edge.pipe_floor_location&&!edge.source_named_service&&!edge.source_midpath_symbol_candidates?.length&&!edge.source_inline_axis_candidates?.length&&!edge.source_straight_crossover_evidence&&!edge.source_normalized_crossovers?.length&&!edge.source_expert_circle_link&&!edge.source_dimensioned_segments?.length&&!edge.source_partial_line_evidence&&!edge.source_drafting_erratum&&!edge.source_layout_equipment_interface?.length_scope_composition&&!upstreamJointSystemProperties(edge).length&&!checkedOrderedBranch(edge,data?.attribute_value_context)&&!checkedBoundedMain(edge,data?.attribute_value_context))return [];
 const zh=data.display?.edge_attribute_language==='zh-CN',label=zh?zhLabel:{diameter:'Pipe diameter',floor:'Floor location',source:'Source annotation',unknown:'Not annotated / unverified'};
 const scoped=checkedPlanDiameterScope(edge.cross_view_attributes);
 const dn=edge.cross_view_attributes?(scoped?(scoped.whole?`DN${scoped.value}`:`DN${scoped.value} ${zh?'\uff08\u5e73\u9762\u5df2\u7ed8\u7ba1\u6bb5\uff1b\u6574\u8fb9\u8303\u56f4\u5f85\u5b9a\uff09':'(drawn plan scope; whole edge unresolved)'}`):label.unknown):edge.pipe_diameter?.display||label.unknown,floor=edge.pipe_floor_location?.display_zh||label.unknown;
 const rows=[[label.diameter,dn],[label.floor,floor],[label.source,(edge.pipe_diameter?.observations||[]).map(o=>o.text.text+' ['+o.text.source_id+':'+o.text.handle+']').join('; ')||label.unknown]];
 const plan=checkedPlanSegments(edge)?.[0];
 if(plan){if(plan.whole_local_edge)rows[0][1]=`DN${plan.nominal_mm}`;rows[1][1]=plan.whole_local_edge?`${plan.floor}F`:`${edge.floor_start??edge.start_floor}F -> ${edge.floor_end??edge.end_floor}F`;}
 const external=checkedExternalFeed(edge);
 if(external){
  rows[0][1]=external.nominal_mm===null?label.unknown:`DN${external.nominal_mm} ${zh?'\uff08\u539f\u7ba1\u7ebf\u8303\u56f4\uff09':'(source pipe scope)'}`;
  rows[1][1]=`${external.floor}F`;
  rows[2][1]=external.diameter_evidence.lineage.flatMap(c=>c.evidence.map(e=>e.evidence_id+': '+e.edge_path.join(' -> '))).join('; ')||label.unknown;
 }
 if(edge.source_drafting_erratum){const c=edge.source_drafting_erratum;rows.push([zh?'\u56fe\u7eb8\u52d8\u8bef':'Drawing erratum',`${c.project_scope} / ${c.issue_id}`],[zh?'\u5904\u7406\u8303\u56f4':'Correction scope',zh?'\u672c\u56fe\u5df2\u786e\u8ba4\u89d2\u843d\u8fde\u7eed\uff1b\u4f9b\u56de\u6c34\u72ec\u7acb\uff1b\u4e0d\u4f5c\u4e3a\u901a\u7528\u5706\u5708\u89c4\u5219':'Confirmed local corner continuity; separate systems; no general circle rule'],[zh?'\u7f3a\u53e3\u7269\u7406\u957f\u5ea6':'Physical gap length',zh?'\u672a\u77e5\uff1b\u4ec5\u793a\u610f\u8fde\u63a5\uff0c\u4e0d\u8ba1\u5165\u5df2\u77e5\u7ba1\u957f':'Unknown; logical continuation only, excluded from known length']);}
 if(edge.diameter_inference){const c=edge.diameter_inference;rows.push([zh?'\u7ba1\u5f84\u7ee7\u627f\u4f9d\u636e':'Diameter candidate lineage',(c.lineage||[]).map(x=>x.source_text+' ['+x.source_text_handle+']: '+x.edge_path.join(' \u2192 ')).join('; ')],[zh?'\u5019\u9009\u72b6\u6001':'Candidate status',zh?'\u4ec5\u6e90\u56fe\u7ebf\u53ca\u6807\u6ce8\u7b5b\u67e5\uff1b\u6574\u6bb5\u7ba1\u5f84\u548c\u7ee7\u627f\u5f85\u6838':'Source screening only; edge-wide diameter and inheritance unverified']);}
 if(edge.source_dimensioned_segments?.length){rows.push([zh?'\u539f\u56fe\u6807\u6ce8\u6bb5\u957f':'Source dimensioned segment',edge.source_dimensioned_segments.map(x=>x.dimension_value_mm+' mm ['+x.dimension_handle+']').join('; ')],[zh?'\u6574\u8fb9\u7269\u7406\u957f\u5ea6':'Whole-edge physical length',zh?'\u672a\u77e5\uff1b\u5176\u4ed6\u7ba1\u6bb5\u5f85\u6838':'Unknown; other segments unverified']);}
 if(edge.source_partial_line_evidence){const r=edge.source_partial_line_evidence.records||[];rows.push([zh?'\u5c40\u90e8\u6e90\u7ebf\u91cd\u5408\u5019\u9009':'Partial source-line overlap',r.map(x=>`${x.unique_source_drawing_length.toFixed(2)} ${zh?'\u56fe\u7eb8\u5355\u4f4d':'drawing units'} [${x.pieces.filter(p=>p.status==='unique_source_line').flatMap(p=>p.source_handles).join(', ')}]`).join('; ')],[zh?'\u5c40\u90e8\u8bc1\u636e\u72b6\u6001':'Partial evidence status',zh?'\u4ec5\u539f\u56fe\u7ebf\u6bb5\u91cd\u5408\uff1b\u7ba1\u7ebf\u5f52\u5c5e\u3001\u8fde\u63a5\u53ca\u5b9e\u4f53\u957f\u5ea6\u5f85\u6838':'Source geometry overlap only; ownership, connectivity and physical length unverified']);}
 const service=edge.source_named_service;
 if(service){rows.push(['\u539f\u56fe\u8bed\u4e49\u5019\u9009',service.display_zh+'\uff08\u5f85\u6838\u5b9e\uff09'],['\u5019\u9009\u4f9d\u636e',(service.witnesses||[]).map(w=>w.original_text+' ['+w.label_handle+']').join('\uff1b')],['\u63a8\u65ad\u8303\u56f4','\u539f\u56fe\u6807\u6ce8\u53ca\u540c\u5c42\u8def\u5f84\uff1b\u7cfb\u7edf\u5206\u7c7b\u5f85\u6838']);}
 if(edge.source_midpath_symbol_candidates?.length)rows.push([zh?'\u539f\u56fe\u7ba1\u4e2d\u5706\u5f62\u6807\u8bb0':'Source circle on pipe',edge.source_midpath_symbol_candidates.map(x=>x.source_circle_handle).join(', ')],[zh?'\u6807\u8bb0\u542b\u4e49':'Symbol meaning',zh?'\u5f85\u6838\u5b9e\uff1b\u672a\u63a8\u65ad\u7ad6\u5411\u8fde\u63a5':'Unverified; no vertical connection inferred']);
 if(edge.source_inline_axis_candidates?.length)rows.push([zh?'\u5143\u4ef6\u8f74\u5411\u6295\u5f71':'Component axis projection',edge.source_inline_axis_candidates.map(x=>x.source_device_name+' ('+(x.status==='axis_projection_partial'?(zh?'\u90e8\u5206\u8986\u76d6':'partial'):(zh?'\u8de8\u8fc7\u4e24\u70b9':'spans both points'))+')').join('; ')],[zh?'\u8fde\u901a\u72b6\u6001':'Continuity status',zh?'\u4ec5\u6295\u5f71\u5bf9\u7167\uff0c\u7269\u7406\u8fde\u901a\u5f85\u6838':'Projection only; physical continuity unverified']);
 if(edge.source_straight_crossover_evidence){const c=edge.source_straight_crossover_evidence;rows.push([zh?'\u8de8\u8d8a\u8bc1\u636e':'Crossover evidence',`${c.source_gap_id}: ${c.source_handles.join(' / ')} \u00d7 ${c.crossed_handle}`],[zh?'\u4ea4\u53c9\u5904\u5173\u7cfb':'Crossing relationship',zh?'\u4f9b\u56de\u6c34\u5404\u81ea\u8fde\u7eed\uff0c\u4ea4\u53c9\u5904\u4e0d\u8fde\u63a5':'Independent pipes; no connection at crossing'],[zh?'\u8de8\u8d8a\u6bb5\u5b9e\u9645\u957f\u5ea6\u53ca\u9ad8\u5dee':'Physical length and elevation',zh?'\u672a\u77e5':'Unknown']);}
 if(edge.source_normalized_crossovers?.length){const c=edge.source_normalized_crossovers[0];rows.push([zh?'\u8de8\u8d8a\u8bc1\u636e':'Crossover evidence',`${c.source_handles.join(' / ')} \u00d7 ${c.crossings?.[0]?.crossed_handle||'?'}`],[zh?'\u4ea4\u53c9\u5904\u5173\u7cfb':'Crossing relationship',zh?'\u7ba1\u7ebf\u5404\u81ea\u8fde\u7eed\uff0c\u4ea4\u53c9\u5904\u4e0d\u8fde\u63a5':'Independent pipes; no connection at crossing'],[zh?'\u8de8\u8d8a\u6bb5\u5b9e\u9645\u957f\u5ea6\u53ca\u9ad8\u5dee':'Physical length and elevation',zh?'\u672a\u77e5':'Unknown']);}
 if(edge.source_expert_circle_link){const c=edge.source_expert_circle_link;rows.push([zh?'\u4e13\u5bb6\u5706\u5708\u63a5\u7ba1':'Expert circle connection',`${c.expert_issue}: ${c.circle_handle}`],[zh?'\u8fde\u63a5\u6bb5\u5b9e\u9645\u957f\u5ea6':'Physical connection length',zh?'\u672a\u77e5\uff1b\u56fe\u793a\u91cd\u53e0\u4e0d\u662f\u5b9e\u6d4b\u7ba1\u957f':'Unknown; graphic overlap is not measured pipe length']);if(c.similar_location_inferred)rows.push([zh?'\u8bc1\u636e\u72b6\u6001':'Evidence status',zh?'\u4f9d\u636e\u4e13\u5bb6\u6240\u8bf4\u7c7b\u4f3c\u4f4d\u7f6e\u63a8\u65ad\uff1b\u5f85\u4e13\u5bb6\u9010\u70b9\u590d\u6838':'Inferred similar location; individual expert review pending']);}
 const anchored=checkedAnchoredMain(edge);if(anchored){rows[0][1]=anchored.nominal_mm===null?(zh?'\u672a\u77e5\uff1bDN\u7ee7\u627f\u51b2\u7a81':'Unknown; DN inheritance conflict'):`DN${anchored.nominal_mm}`;rows[1][1]=`${anchored.floor}F`;rows[2][1]=anchored.diameter_evidence.lineage.flatMap(l=>(l.evidence||[]).map(e=>e.evidence_id)).join('; ')||label.unknown;}
 const currentBatch=checkedBatchPlanScope(edge);
 if(currentBatch){
  rows[0][1]=currentBatch.plan_drawn_nominal_mm===null?(zh?'\u672a\u77e5\uff1b\u672c\u8f6e\u6765\u6e90\u672a\u89e3\u51b3':label.unknown):`DN${currentBatch.plan_drawn_nominal_mm}${currentBatch.whole_axis_nominal_mm===null?(zh?'\uff08\u5e73\u9762\u5df2\u7ed8\u533a\u6bb5\uff09':' (drawn plan scope)'):''}`;
  const resolved=crossViewAttributeCsvValues(edge,data?.attribute_value_context);
  if(resolved.batch_retained_prior_whole_DN_mm!==''){
   rows[0][1]=`DN${resolved.batch_retained_prior_whole_DN_mm}${zh?'\uff08\u4fdd\u7559\u65e2\u6709\u6574\u8fb9\u7ba1\u5f84\uff0c\u672c\u8f6e\u503c\u4e00\u81f4\uff09':' (prior source-checked whole-edge DN retained; current value agrees)'}`;
   rows.push([zh?'\u65e2\u6709\u7ba1\u5f84\u4fdd\u7559\u4f9d\u636e':'Prior DN retention basis',zh?'\u65e2\u6709\u6e90\u56fe\u6838\u9a8c\u7684\u6574\u8fb9\u503c\u4e0e\u672c\u8f6e\u5e73\u9762\u503c\u4e00\u81f4\uff1b\u957f\u5ea6\u8303\u56f4\u53e6\u884c\u4fdd\u7559':'Prior source-checked whole-edge DN agrees with the current plan value; metric scope remains separate']);
  }
  if(resolved.batch_uniform_group_child_DN_mm!==''){
   rows[0][1]=`DN${resolved.batch_uniform_group_child_DN_mm}${zh?'\uff08\u8def\u5f84\u7ec4\u7ba1\u5f84\u4e00\u81f4\uff0c\u9002\u7528\u672c\u8fb9\uff09':' (uniform source path DN applies to this child)'}`;
   rows.push([zh?'\u8def\u5f84\u7ec4\u7ba1\u5f84\u4f9d\u636e':'Uniform path DN basis',zh?'\u5df2\u6838\u5bf9\u8def\u5f84\u7ec4\u5404\u6bb5DN\u4e00\u81f4\uff0c\u4e14\u672c\u8fb9\u5b8c\u6574\u4f4d\u4e8e\u6c34\u5e73\u7ba1\u6bb5':'Every source path DN agrees and this complete child is horizontal']);
  }
  rows[1][1]=`${currentBatch.floor}F`;rows[2][1]=batchPlanProperties(edge,zh,data?.attribute_value_context).find(r=>r[0]===(zh?'\u7ba1\u5f84\u6765\u6e90':'DN source'))?.[1]||label.unknown;
  rows.push(...batchPlanProperties(edge,zh,data?.attribute_value_context));
 }
 rows.push(...upstreamJointSystemProperties(edge,zh),...crossViewAttributeProperties(edge,zh),...ownershipLengthScopeProperties(edge,data,zh),...axisRiserAttributeProperties(edge,zh),...planSegmentProperties(edge,zh),...currentPlanScopeProperties(edge,zh),...anchoredMainProperties(edge,zh),...externalFeedProperties(edge,zh),...currentFloorPlanScopeProperties(edge,zh),...currentNamedPrefixProperties(edge,zh));
 const drawnBranch=checkedOrderedBranch(edge,data?.attribute_value_context);
 if(drawnBranch){rows[0][1]=drawnBranch.plan_drawn_nominal_mm===null?label.unknown:`DN${drawnBranch.plan_drawn_nominal_mm}${zh?'\uff08\u5e73\u9762\u5df2\u7ed8\u652f\u8def\uff09':' (drawn plan branch)'}`;rows[1][1]=`${drawnBranch.floor}F`;rows[2][1]=drawnBranch.plan_DN_records.flatMap(r=>(r.lineage||[]).flatMap(l=>(l.evidence||[]).map(e=>e.evidence_id))).join(' / ')||label.unknown;}
 const bounded=checkedBoundedMain(edge,data?.attribute_value_context);
 if(bounded){const effective=boundedMainCsvValues(edge,data?.attribute_value_context);rows[0][1]=effective.diameter_status==='compound_carrier_member_identity_pending'?`${effective.diameter_text} (${zh?'\u6210\u5458\u5f85\u5b9a':'member unresolved'})`:bounded.nominal_mm===null?label.unknown:`DN${bounded.nominal_mm}`;rows[1][1]=`${bounded.floor}F`;rows[2][1]=(bounded.plan_DN_record.lineage||[]).flatMap(l=>(l.evidence||[]).map(e=>e.evidence_id)).join(' / ')||label.unknown;}
 rows.splice(3,0,...boundedMainProperties(edge,zh,data?.attribute_value_context));
 rows.splice(3,0,...orderedBranchProperties(edge,zh,data?.attribute_value_context));
 rows.splice(3,0,...memberPlanRunProperties(edge,zh,data?.attribute_value_context),...orderedGroupRunProperties(edge,zh,data?.attribute_value_context));
 return rows;
}
export const edgeAttributeCsvFields=['diameter_nominal_mm','diameter_text','diameter_status','diameter_candidate_mm','diameter_candidate_status','diameter_candidate_lineage','source_dimensioned_segments_json','physical_edge_length_status','floor_location_text_zh','floor_location_status','crossview_mapping_id','crossview_plan_edges','crossview_plan_horizontal_projection_mm','crossview_projection_allocation','crossview_metric_status','crossview_detail_context_json','crossview_whole_edge_length_mm','crossview_whole_edge_length_kind','crossview_plan_drawn_nominal_mm','crossview_plan_DN_scope_status','crossview_plan_DN_scope_sha256','crossview_plan_diameter_candidate_mm','crossview_axis_diameter_observation_mm','crossview_plan_source_sha256','equipment_connector_length_mm','equipment_connector_length_status','prior_length_scope','length_scope_evidence_json',...axisRiserAttributeCsvFields,...planSegmentCsvFields,...currentPlanScopeCsvFields,...anchoredMainCsvFields,...externalFeedCsvFields,...currentFloorPlanScopeCsvFields,...currentNamedPrefixCsvFields,...batchPlanCsvFields,...memberPlanRunCsvFields,...orderedGroupRunCsvFields,...orderedBranchCsvFields,...boundedMainCsvFields,...compoundMemberCsvFields,...noncompoundMainExtentCsvFields,...compoundInterfaceCsvFields,...axisVerticalSegmentCsvFields,...compoundBridgeCsvFields,...orderedOwnerRunCsvFields,...aliasMemberInterfaceCsvFields,...aliasMemberBridgeCsvFields,...graphFirstExtensionCsvFields,...cycleCarrierGuardCsvFields,...riserHeaderCsvFields,...cohortMemberCsvFields,...contactOwnerPathCsvFields,...omissionVerticalDNCsvFields];
