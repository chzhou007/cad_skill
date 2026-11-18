import json,csv,math,pathlib,hashlib,collections,html,subprocess,sys,shutil
import ezdxf
from cad_ceiling_native_rules import circle_connection_candidate,match_out_of_plane_symbol,riser_terminal_candidate,expert_circle_connection_candidate
from source_reviewed_circle_connections import load_review as load_circle_source_review, candidate as reviewed_circle_candidate
from straight_crossovers import recover_straight_crossovers
import pipe_geometry as pg
import argparse
from topology_normalization import snap_near_junction_endpoints
from proven_contacts import canonical_contact_points,validate_junction_contacts
from native_inline_coordinates import ball_valve_anchor,balancing_valve_anchor
from riser_source_lengths import correct_riser_source_lengths
from expert_circle_source_lengths import correct_circle_branch_lengths
from expert_riser_connection import apply_source_riser_connections,separate_riser_source_path
from expert_native_wave_terminals import attach as attach_expert_wave_terminals
from source_readability import read_source, bind_graph_source
from unbound_ceiling_symbols import identify as identify_unbound_ceiling_symbols
from equipment_identity_dn_recheck import prepare as prepare_identity_dn_recheck
cli=argparse.ArgumentParser();cli.add_argument('--input-root',type=pathlib.Path,required=True);cli.add_argument('--output-root',type=pathlib.Path,required=True);cli.add_argument('--normalization-config',type=pathlib.Path,required=True);cli.add_argument('--flex-policy-map',type=pathlib.Path,help='Optional JSON task ID to hash-pinned flexible-joint policy path mapping');cli.add_argument('--wave-policy-map',type=pathlib.Path,help='Optional JSON task ID to source-scoped wave policy and expert issue paths');cli.add_argument('--circle-pair-policy-map',type=pathlib.Path,help='Optional JSON task ID to explicit source circle-pair policy and expert issue paths');cli.add_argument('--detail-policy-map',type=pathlib.Path,help='Optional JSON task ID to source-scoped non-connecting detail comparison policy and issue paths');cli.add_argument('--boundary-policy-map',type=pathlib.Path,help='Optional JSON task ID to explicit boundary policy and expert issue paths');cli.add_argument('--similar-boundary-policy-map',type=pathlib.Path,help='Optional JSON task ID to separately scoped inferred boundary policy and issue');cli.add_argument('--endpoint-semantics',action='store_true',help='Add a separate endpoint semantics output after all selected expert stages');cli.add_argument('--source-glyph-conflicts',action='store_true',help='Attach source-confirmed glyph/system conflict evidence after endpoint semantics');cli.add_argument('--source-main-continuity',action='store_true',help='Identify source-proven main continuities at pending junctions');cli.add_argument('--direct-dn-policy-map',type=pathlib.Path,help='Optional task ID to source/graph-pinned direct DN candidate policy');cli.add_argument('--equipment-identity-policy-map',type=pathlib.Path,help='Optional task ID to source-scoped uniquely matchable equipment group policy');cli.add_argument('--confirmed-interface-policy-map',type=pathlib.Path,help='Optional task ID to explicit user confirmation and native inventory policy paths');cli.add_argument('--local-dn-policy-map',type=pathlib.Path,help='Optional task ID to source- and final-graph-pinned local DN policy');cli.add_argument('--dn-inheritance-policy-map',type=pathlib.Path,help='Optional source-bound scoped DN inheritance candidate policies');cli.add_argument('--segment-dimension-policy-map',type=pathlib.Path,help='Optional exact source dimension-to-segment policies');cli.add_argument('--circle-rim-screen-policy-map',type=pathlib.Path,help='Optional source/graph-pinned circle-rim comparison policies');cli.add_argument('--confirmed-circle-policy-map',type=pathlib.Path,help='Optional task ID to user-confirmed circle policy and prior screen paths');cli.add_argument('--detail-glyph-policy-map',type=pathlib.Path,help='Optional source and graph pinned detail-glyph ambiguity policies');cli.add_argument('--detail-scope-policy-map',type=pathlib.Path,help='Optional source-bound interface inventory regions for detail coverage');cli.add_argument('--detail-boundary-policy-map',type=pathlib.Path,help='Optional source-bound non-node detail boundary inventory');cli.add_argument('--confirmed-gap-tee-policy-map',type=pathlib.Path,help='Optional task ID to source/graph-pinned user gap-tee policy and image paths');cli.add_argument('--partial-source-length-policy-map',type=pathlib.Path,help='Optional task ID to graph-pinned source coverage and length policy');cli.add_argument('--confirmed-overlap-branch-policy-map',type=pathlib.Path,help='Optional task ID to source-pinned overlap branch policy and evidence manifest');cli.add_argument('--hidden-branch-screen-policy-map',type=pathlib.Path,help='Optional task ID to source/graph-pinned plan hidden-branch candidate screen policy');cli.add_argument('--followup-overlap-policy-map',type=pathlib.Path,help='Optional task ID to ordered followup confirmed overlap policies');cli.add_argument('--source-reviewed-circle-policy-map',type=pathlib.Path,help='Optional source-reviewed circle reconstruction before DN and dimensions');cli.add_argument('--circle-conflict-reconciliation-policy-map',type=pathlib.Path,help='Optional source-bound retirement of proven obsolete crossover conflicts');cli.add_argument('--followup-source-reviewed-circle-policy-map',type=pathlib.Path,help='Optional fresh source-reviewed connection reentry after conflict reconciliation');cli.add_argument('--calibrated-source-circle-policy-map',type=pathlib.Path,help='Optional calibrated repeated plan circle review after followup reconstruction');cli.add_argument('--duplicate-main-diagnostic-tasks',type=pathlib.Path,help='Optional JSON array of task IDs to diagnose ambiguous native mains after circle screening');cli.add_argument('--followup-confirmed-circle-policy-map',type=pathlib.Path,help='Optional task ID to current-graph user-confirmed circle policy and source screen');cli.add_argument('--post-confirmed-source-circle-policy-map',type=pathlib.Path,help='Optional task ID to source-reviewed circle policy after current user-confirmed circles');cli.add_argument('--post-dimension-confirmed-interface-policy-map',type=pathlib.Path,help='Optional task ID to followup confirmed equipment interface policy and inventory');cli.add_argument('--expert-duplicate-circle-policy-map',type=pathlib.Path,help='Optional source and issue bound duplicate-main expert circle repair');cli.add_argument('--calibrated-duplicate-circle-policy-map',type=pathlib.Path,help='Optional expert-control-calibrated duplicate-main source review');cli.add_argument('--confirmed-terminal-boundary-policy-map',type=pathlib.Path,help='User-confirmed non-node source boundary policy and review evidence')
cli.add_argument('--pending-main-reconciliation-policy-map',type=pathlib.Path,help='Source-verified rebinding of pending main edge references after topology changes')
cli.add_argument('--late-flex-policy-map',type=pathlib.Path,help='Source calibrated native flexible-joint repair after endpoint graph')
cli.add_argument('--calibrated-wave-policy-map',type=pathlib.Path,help='Source calibrated scoped wave omissions after pending-main reconciliation')
cli.add_argument('--unpaired-wave-evidence-policy-map',type=pathlib.Path,help='Source-bound unpaired wave marks on edges without inferred destinations')
cli.add_argument('--wave-convention-confirmation-map',type=pathlib.Path,help='Scoped expert drawing convention confirmation and original image')
cli.add_argument('--final-crossover-length-policy-map',type=pathlib.Path,help='Source and graph pinned crossover drawing-length correction before final checks')
cli.add_argument('--final-dn-recheck-policy-map',type=pathlib.Path,help='Recheck scoped DN candidates on final topology without accepting them')
cli.add_argument('--final-dimension-recheck-policy-map',type=pathlib.Path,help='Recheck native source segment dimensions on final topology')
cli.add_argument('--final-dimension-screen-policy-map',type=pathlib.Path,help='Optional source/graph-pinned modelspace dimension segment inventory')
cli.add_argument('--final-compound-dn-policy-map',type=pathlib.Path,help='Source/graph-pinned final compound DN text inventory')
cli.add_argument('--final-plan-line-policy-map',type=pathlib.Path,help='Source/graph-pinned final native plan LINE inventory')
cli.add_argument('--final-near-endpoint-policy-map',type=pathlib.Path,help='Optional final-graph small endpoint overshoot screen')
cli.add_argument('--final-named-leader-policy-map',type=pathlib.Path,help='Optional source/graph-pinned named-DN endpoint candidate screen')
cli.add_argument('--final-unidentified-equipment-policy-map',type=pathlib.Path,help='Optional source-pinned preservation of unlabeled equipment instances before final checks')
cli.add_argument('--final-local-dn-policy-map',type=pathlib.Path,help='Optional source-pinned final local DN observations before final checks')
cli.add_argument('--final-near-tee-state-policy-map',type=pathlib.Path,help='Optional source-pinned pending state for normalized near tees')
cli.add_argument('--final-equipment-pair-candidates-map',type=pathlib.Path,help='Optional source-bound paired equipment label candidates, never a mapping')
cli.add_argument('--final-component-conservation-policy-map',type=pathlib.Path,help='Optional final graph initial-component and scoped flex conservation check')
cli.add_argument('--final-expert-node-reconciliation-map',type=pathlib.Path,help='Optional final-graph selected legacy expert node reconciliation')
cli.add_argument('--final-source-segment-dimension-policy-map',type=pathlib.Path,help='Optional exact source segment dimensions on final graph without existing DN evidence')
cli.add_argument('--final-id-audit-map',type=pathlib.Path,help='Optional source- and prior-graph-pinned read-only ID reuse audit')
cli.add_argument('--detail-evidence-islands-map',type=pathlib.Path,help='Optional task ID to source/graph-pinned independent detail island audit')
cli.add_argument('--detail-frame-policy-map',type=pathlib.Path,help='Optional task ID to source-drawn detail frame context policies')
cli.add_argument('--additional-circle-rim-policy-map',type=pathlib.Path,help='Optional task ID to list of extra source/graph-pinned circle radius policies')
cli.add_argument('--near-offset-circle-policy-map',type=pathlib.Path,help='Optional task ID to source/graph-pinned near-offset circle policy')
cli.add_argument('--batch-confirmed-circle-policy-map',type=pathlib.Path,help='Explicit batch Pair circle confirmations, rebuilt before final graph screens')
cli.add_argument('--confirmed-sideview-policy-map',type=pathlib.Path,help='Explicit main/detail Pair confirmations; reuse verified detail segmentation before final source screens')
cli.add_argument('--confirmed-equipment-pairs-policy-map',type=pathlib.Path,help='Explicit paired equipment ownership and main-circle reconstruction before final screens')
cli.add_argument('--confirmed-near-tee-policy-map',type=pathlib.Path,help='Explicit native Pair confirmations of already reconstructed near tees before final screens')
cli.add_argument('--rotated-equipment-identity-policy-map',type=pathlib.Path,help='Resolve isolated retained equipment IDs from source caption footprints after local checks; ports stay unknown')
cli.add_argument('--source-layout-equipment-ownership-policy-map',type=pathlib.Path,help='Source-calibrated equipment/interface logical ownership after local checks; map task to policy, control_source and control_graph')
cli.add_argument('--source-sideview-equipment-ownership-policy-map',type=pathlib.Path,help='Source-calibrated ownership through confirmed main/detail aliases; map task to pinned policy')
cli.add_argument('--reviewed-plan-gap-map',type=pathlib.Path,help='Pinned explicit same-service drawing-gap reconstruction after final pending-native-T topology')
cli.add_argument('--reviewed-interface-owner-map',type=pathlib.Path,help='Pinned explicit paired-owner answers after final local topology; local inputs belong to the family')
cli.add_argument('--wave-main-cohort-map',type=pathlib.Path,help='Batch calibrated paired wave frontiers onto source main carriers; rebuild all main children and components')
cli.add_argument('--inherited-wave-continuity-map',type=pathlib.Path,help='Pinned same-system paired wave controls after final local ownership; no physical length or HIL claim')
cli.add_argument('--plan-circle-continuity-map',type=pathlib.Path,help='Native two-arm circle continuations and optional exact pending-T resolution after local ownership')
cli.add_argument('--capped-branch-annotation-policy-map',type=pathlib.Path,help='Source/graph-pinned Chinese caption, leader and marker evidence after final topology; sidecar only')
cli.add_argument('--final-circle-path-policy-map',type=pathlib.Path,help='Pinned source-reviewed radius exclusion after logical ownership; map task to policy')
cli.add_argument('--project-known-erratum-policy-map',type=pathlib.Path,help='Explicit project issue/context repair after local checks and before equipment ownership')
args=cli.parse_args()
PROJECT_KNOWN_ERRATA=json.loads(args.project_known_erratum_policy_map.read_text(encoding='utf8')) if args.project_known_erratum_policy_map else {}
if not isinstance(PROJECT_KNOWN_ERRATA,dict) or any(not isinstance(v,dict) or set(v)!={'policy','issue','context'} or any(not isinstance(p,str) or not p for p in v.values()) for v in PROJECT_KNOWN_ERRATA.values()):raise ValueError('invalid explicit project erratum map')
if args.rotated_equipment_identity_policy_map and not args.endpoint_semantics:raise ValueError('rotated equipment identity requires endpoint semantics')
ROTATED_EQUIPMENT_IDENTITIES=json.loads(args.rotated_equipment_identity_policy_map.read_text(encoding='utf8')) if args.rotated_equipment_identity_policy_map else {}
if not isinstance(ROTATED_EQUIPMENT_IDENTITIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in ROTATED_EQUIPMENT_IDENTITIES.items()):raise ValueError('invalid rotated equipment identity map')
LAYOUT_EQUIPMENT_OWNERSHIPS=json.loads(args.source_layout_equipment_ownership_policy_map.read_text(encoding='utf8')) if args.source_layout_equipment_ownership_policy_map else {}
FINAL_CIRCLE_PATHS=json.loads(args.final_circle_path_policy_map.read_text(encoding='utf8')) if args.final_circle_path_policy_map else {}
if not isinstance(FINAL_CIRCLE_PATHS,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in FINAL_CIRCLE_PATHS.items()):raise ValueError('invalid final circle path map')
if not isinstance(LAYOUT_EQUIPMENT_OWNERSHIPS,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','control_source','control_graph'} or any(not isinstance(x,str) or not x for x in v.values()) for k,v in LAYOUT_EQUIPMENT_OWNERSHIPS.items()):raise ValueError('invalid source layout equipment ownership map')
CONFIRMED_NEAR_TEES=json.loads(args.confirmed_near_tee_policy_map.read_text(encoding='utf8')) if args.confirmed_near_tee_policy_map else {}
if not isinstance(CONFIRMED_NEAR_TEES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in CONFIRMED_NEAR_TEES.items()):raise ValueError('invalid confirmed near-tee map')
if CONFIRMED_NEAR_TEES and not args.endpoint_semantics:raise ValueError('near-tee confirmation requires endpoint semantics')
CONFIRMED_EQUIPMENT_PAIRS=json.loads(args.confirmed_equipment_pairs_policy_map.read_text(encoding='utf8')) if args.confirmed_equipment_pairs_policy_map else {}
if not isinstance(CONFIRMED_EQUIPMENT_PAIRS,dict) or any(not isinstance(v,dict) or set(v)!={'reviewed_graph','manifest','reply','policy'} or any(not isinstance(p,str) or not p for p in v.values()) for v in CONFIRMED_EQUIPMENT_PAIRS.values()):raise ValueError('invalid confirmed equipment pair map')
if CONFIRMED_EQUIPMENT_PAIRS and not args.endpoint_semantics:raise ValueError('equipment pair reconstruction requires endpoint semantics')
CONFIRMED_SIDEVIEWS=json.loads(args.confirmed_sideview_policy_map.read_text(encoding='utf8')) if args.confirmed_sideview_policy_map else {}
if not isinstance(CONFIRMED_SIDEVIEWS,dict) or any(not isinstance(v,dict) or set(v)!={'manifest','reply','policy'} or any(not isinstance(p,str) or not p for p in v.values()) for v in CONFIRMED_SIDEVIEWS.values()):raise ValueError('invalid confirmed side-view map')
if CONFIRMED_SIDEVIEWS and not args.endpoint_semantics:raise ValueError('confirmed side-views require endpoint semantics')
BATCH_CONFIRMED_CIRCLES=json.loads(args.batch_confirmed_circle_policy_map.read_text(encoding='utf8')) if args.batch_confirmed_circle_policy_map else {}
if not isinstance(BATCH_CONFIRMED_CIRCLES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in BATCH_CONFIRMED_CIRCLES.items()):raise ValueError('invalid batch confirmed circle map')
if BATCH_CONFIRMED_CIRCLES and not args.endpoint_semantics:raise ValueError('batch circle reconstruction requires endpoint semantics')
FINAL_ID_AUDITS=json.loads(args.final_id_audit_map.read_text(encoding='utf8')) if args.final_id_audit_map else {}
if not isinstance(FINAL_ID_AUDITS,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'previous_graph','previous_graph_sha256','source_sha256'} or any(not isinstance(x,str) or not x for x in v.values()) for k,v in FINAL_ID_AUDITS.items()):raise ValueError('invalid final ID audit map')
if (args.source_glyph_conflicts or args.source_main_continuity or args.direct_dn_policy_map or args.equipment_identity_policy_map or args.confirmed_interface_policy_map or args.confirmed_circle_policy_map or args.confirmed_gap_tee_policy_map or args.confirmed_overlap_branch_policy_map or args.hidden_branch_screen_policy_map or args.followup_overlap_policy_map or args.partial_source_length_policy_map or args.local_dn_policy_map or args.dn_inheritance_policy_map or args.segment_dimension_policy_map or args.circle_rim_screen_policy_map) and not args.endpoint_semantics:raise ValueError('source evidence requires endpoint semantics')
BATCH=args.input_root;OUT=args.output_root;TOL=.05;NORM=json.loads(args.normalization_config.read_text(encoding='utf8'))
FLEX_POLICIES=json.loads(args.flex_policy_map.read_text(encoding='utf8')) if args.flex_policy_map else {}
if not isinstance(FLEX_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in FLEX_POLICIES.items()):raise ValueError('flex policy map must map task IDs to policy paths')
WAVE_POLICIES=json.loads(args.wave_policy_map.read_text(encoding='utf8')) if args.wave_policy_map else {}
if not isinstance(WAVE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','issue'} or any(not isinstance(x,str) for x in v.values()) for k,v in WAVE_POLICIES.items()):raise ValueError('wave policy map must map task IDs to policy and issue paths')
CIRCLE_PAIR_POLICIES=json.loads(args.circle_pair_policy_map.read_text(encoding='utf8')) if args.circle_pair_policy_map else {}
if not isinstance(CIRCLE_PAIR_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','issue'} or any(not isinstance(x,str) for x in v.values()) for k,v in CIRCLE_PAIR_POLICIES.items()):raise ValueError('circle pair policy map must map task IDs to policy and issue paths')
DETAIL_POLICIES=json.loads(args.detail_policy_map.read_text(encoding='utf8')) if args.detail_policy_map else {}
if not isinstance(DETAIL_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','issue'} or any(not isinstance(x,str) for x in v.values()) for k,v in DETAIL_POLICIES.items()):raise ValueError('detail policy map must map task IDs to policy and issue paths')
BOUNDARY_POLICIES=json.loads(args.boundary_policy_map.read_text(encoding='utf8')) if args.boundary_policy_map else {}
if not isinstance(BOUNDARY_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','issue'} or any(not isinstance(x,str) for x in v.values()) for k,v in BOUNDARY_POLICIES.items()):raise ValueError('boundary policy map must map task IDs to policy and issue paths')
IDENTITY_POLICIES=json.loads(args.equipment_identity_policy_map.read_text(encoding='utf8')) if args.equipment_identity_policy_map else {}
CONFIRMED_INTERFACE_POLICIES=json.loads(args.confirmed_interface_policy_map.read_text(encoding='utf8')) if args.confirmed_interface_policy_map else {}
LOCAL_DN_POLICIES=json.loads(args.local_dn_policy_map.read_text(encoding='utf8')) if args.local_dn_policy_map else {}
DN_INHERITANCE_POLICIES=json.loads(args.dn_inheritance_policy_map.read_text(encoding='utf8')) if args.dn_inheritance_policy_map else {}
SEGMENT_DIMENSION_POLICIES=json.loads(args.segment_dimension_policy_map.read_text(encoding='utf8')) if args.segment_dimension_policy_map else {}
DETAIL_GLYPH_POLICIES=json.loads(args.detail_glyph_policy_map.read_text(encoding='utf8')) if args.detail_glyph_policy_map else {}
DETAIL_FRAME_POLICIES=json.loads(args.detail_frame_policy_map.read_text(encoding='utf8')) if args.detail_frame_policy_map else {}
if not isinstance(DETAIL_FRAME_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in DETAIL_FRAME_POLICIES.items()) or not set(DETAIL_FRAME_POLICIES).issubset(DETAIL_GLYPH_POLICIES):raise ValueError('detail frame screen requires a glyph policy for each task')
DETAIL_SCOPE_POLICIES=json.loads(args.detail_scope_policy_map.read_text(encoding='utf8')) if args.detail_scope_policy_map else {}
if not isinstance(DETAIL_SCOPE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in DETAIL_SCOPE_POLICIES.items()):raise ValueError('invalid detail scope policy map')
if not set(DETAIL_SCOPE_POLICIES).issubset(DETAIL_GLYPH_POLICIES):raise ValueError('detail scope inventory requires current glyph screen')
DETAIL_BOUNDARY_POLICIES=json.loads(args.detail_boundary_policy_map.read_text(encoding='utf8')) if args.detail_boundary_policy_map else {}
if not isinstance(DETAIL_BOUNDARY_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in DETAIL_BOUNDARY_POLICIES.items()):raise ValueError('invalid detail boundary policy map')
if not set(DETAIL_BOUNDARY_POLICIES).issubset(DETAIL_SCOPE_POLICIES):raise ValueError('detail boundary inventory requires scope inventory')
DETAIL_EVIDENCE_ISLANDS=json.loads(args.detail_evidence_islands_map.read_text(encoding='utf8')) if args.detail_evidence_islands_map else {}
if not isinstance(DETAIL_EVIDENCE_ISLANDS,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in DETAIL_EVIDENCE_ISLANDS.items()):raise ValueError('invalid detail evidence islands map')
if not set(DETAIL_EVIDENCE_ISLANDS).issubset(DETAIL_GLYPH_POLICIES):raise ValueError('detail evidence requires a current glyph screen for each task')
CIRCLE_RIM_SCREEN_POLICIES=json.loads(args.circle_rim_screen_policy_map.read_text(encoding='utf8')) if args.circle_rim_screen_policy_map else {}
EXTRA_CIRCLE_POLICIES=json.loads(args.additional_circle_rim_policy_map.read_text(encoding='utf8')) if args.additional_circle_rim_policy_map else {}
if not isinstance(EXTRA_CIRCLE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,list) or not v or any(not isinstance(p,str) or not p for p in v) or len(v)!=len(set(v)) for k,v in EXTRA_CIRCLE_POLICIES.items()) or not set(EXTRA_CIRCLE_POLICIES).issubset(CIRCLE_RIM_SCREEN_POLICIES):raise ValueError('extra circle screens require a primary screen and nonempty unique policy lists')
NEAR_OFFSET_CIRCLE_POLICIES=json.loads(args.near_offset_circle_policy_map.read_text(encoding='utf8')) if args.near_offset_circle_policy_map else {}
if not isinstance(NEAR_OFFSET_CIRCLE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in NEAR_OFFSET_CIRCLE_POLICIES.items()) or not set(NEAR_OFFSET_CIRCLE_POLICIES).issubset(CIRCLE_RIM_SCREEN_POLICIES):raise ValueError('near-offset circle screens require a primary screen and task policy paths')
CONFIRMED_CIRCLE_POLICIES=json.loads(args.confirmed_circle_policy_map.read_text(encoding='utf8')) if args.confirmed_circle_policy_map else {}
DUPLICATE_MAIN_TASKS=json.loads(args.duplicate_main_diagnostic_tasks.read_text(encoding='utf8')) if args.duplicate_main_diagnostic_tasks else []
if not isinstance(DUPLICATE_MAIN_TASKS,list) or any(not isinstance(t,str) or not t for t in DUPLICATE_MAIN_TASKS) or len(set(DUPLICATE_MAIN_TASKS))!=len(DUPLICATE_MAIN_TASKS):raise ValueError('invalid duplicate-main diagnostic task list')
CALIBRATED_SOURCE_CIRCLE_POLICIES=json.loads(args.calibrated_source_circle_policy_map.read_text(encoding='utf8')) if args.calibrated_source_circle_policy_map else {}
FOLLOWUP_CONFIRMED_CIRCLE_POLICIES=json.loads(args.followup_confirmed_circle_policy_map.read_text(encoding='utf8')) if args.followup_confirmed_circle_policy_map else {}
POST_CONFIRMED_SOURCE_CIRCLE_POLICIES=json.loads(args.post_confirmed_source_circle_policy_map.read_text(encoding='utf8')) if args.post_confirmed_source_circle_policy_map else {}
EXPERT_DUPLICATE_CIRCLE_POLICIES=json.loads(args.expert_duplicate_circle_policy_map.read_text(encoding='utf8')) if args.expert_duplicate_circle_policy_map else {}
CALIBRATED_DUPLICATE_CIRCLE_POLICIES=json.loads(args.calibrated_duplicate_circle_policy_map.read_text(encoding='utf8')) if args.calibrated_duplicate_circle_policy_map else {}
if not isinstance(CALIBRATED_DUPLICATE_CIRCLE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'screen','review','calibration_policy','repair_policy'} or any(not isinstance(x,str) or not x for x in v.values()) for k,v in CALIBRATED_DUPLICATE_CIRCLE_POLICIES.items()):raise ValueError('invalid calibrated duplicate circle policy map')
if not set(CALIBRATED_DUPLICATE_CIRCLE_POLICIES).issubset(EXPERT_DUPLICATE_CIRCLE_POLICIES):raise ValueError('calibrated duplicate circles require expert control stage')
if not isinstance(EXPERT_DUPLICATE_CIRCLE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'screen','issue','screen_policy','repair_policy'} or any(not isinstance(x,str) or not x for x in v.values()) for k,v in EXPERT_DUPLICATE_CIRCLE_POLICIES.items()):raise ValueError('invalid expert duplicate circle policy map')
if not set(EXPERT_DUPLICATE_CIRCLE_POLICIES).issubset(POST_CONFIRMED_SOURCE_CIRCLE_POLICIES):raise ValueError('expert duplicate circle repair requires post-confirmed source circles')
CONFIRMED_TERMINAL_BOUNDARY_POLICIES=json.loads(args.confirmed_terminal_boundary_policy_map.read_text(encoding='utf8')) if args.confirmed_terminal_boundary_policy_map else {}
if not isinstance(CONFIRMED_TERMINAL_BOUNDARY_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'manifest','signatures','confirmation','policy'} or any(not isinstance(x,str) or not x for x in v.values()) for k,v in CONFIRMED_TERMINAL_BOUNDARY_POLICIES.items()):raise ValueError('invalid confirmed terminal boundary policy map')
PENDING_MAIN_RECONCILIATION_POLICIES=json.loads(args.pending_main_reconciliation_policy_map.read_text(encoding='utf8')) if args.pending_main_reconciliation_policy_map else {}
if not isinstance(PENDING_MAIN_RECONCILIATION_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in PENDING_MAIN_RECONCILIATION_POLICIES.items()):raise ValueError('invalid pending main reconciliation map')
if not set(PENDING_MAIN_RECONCILIATION_POLICIES).issubset(CONFIRMED_TERMINAL_BOUNDARY_POLICIES):raise ValueError('pending main reconciliation requires explicit prior terminal boundary stage')
LATE_FLEX_POLICIES=json.loads(args.late_flex_policy_map.read_text(encoding='utf8')) if args.late_flex_policy_map else {}
if not isinstance(LATE_FLEX_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in LATE_FLEX_POLICIES.items()):raise ValueError('invalid late flexible joint policy map')
if LATE_FLEX_POLICIES and not args.endpoint_semantics:raise ValueError('late flexible joint repair requires endpoint semantics')
CALIBRATED_WAVE_POLICIES=json.loads(args.calibrated_wave_policy_map.read_text(encoding='utf8')) if args.calibrated_wave_policy_map else {}
if not isinstance(CALIBRATED_WAVE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in CALIBRATED_WAVE_POLICIES.items()):raise ValueError('invalid calibrated wave policy map')
if not set(CALIBRATED_WAVE_POLICIES).issubset(PENDING_MAIN_RECONCILIATION_POLICIES):raise ValueError('calibrated wave repair requires current pending-main reconciliation')
if set(CALIBRATED_WAVE_POLICIES)&set(LATE_FLEX_POLICIES):raise ValueError('combined late flex and wave stages require explicit dependency ordering')
UNPAIRED_WAVE_POLICIES=json.loads(args.unpaired_wave_evidence_policy_map.read_text(encoding='utf8')) if args.unpaired_wave_evidence_policy_map else {}
if not isinstance(UNPAIRED_WAVE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in UNPAIRED_WAVE_POLICIES.items()):raise ValueError('invalid unpaired wave policy map')
if not set(UNPAIRED_WAVE_POLICIES).issubset(CALIBRATED_WAVE_POLICIES):raise ValueError('unpaired wave evidence requires current calibrated wave stage')
WAVE_CONVENTION_CONFIRMATIONS=json.loads(args.wave_convention_confirmation_map.read_text(encoding='utf8')) if args.wave_convention_confirmation_map else {}
if not isinstance(WAVE_CONVENTION_CONFIRMATIONS,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'confirmation','image'} for k,v in WAVE_CONVENTION_CONFIRMATIONS.items()):raise ValueError('invalid wave convention confirmation map')
if not set(WAVE_CONVENTION_CONFIRMATIONS).issubset(UNPAIRED_WAVE_POLICIES):raise ValueError('wave convention confirmation requires current unpaired wave stage')
FINAL_DN_RECHECK_POLICIES=json.loads(args.final_dn_recheck_policy_map.read_text(encoding='utf8')) if args.final_dn_recheck_policy_map else {}
if not isinstance(FINAL_DN_RECHECK_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','direct_policy'} for k,v in FINAL_DN_RECHECK_POLICIES.items()):raise ValueError('invalid final DN recheck policy map')
if not set(FINAL_DN_RECHECK_POLICIES).issubset(WAVE_CONVENTION_CONFIRMATIONS):raise ValueError('final DN recheck requires current wave convention stage')
FINAL_DIMENSION_RECHECK_POLICIES=json.loads(args.final_dimension_recheck_policy_map.read_text(encoding='utf8')) if args.final_dimension_recheck_policy_map else {}
if not isinstance(FINAL_DIMENSION_RECHECK_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in FINAL_DIMENSION_RECHECK_POLICIES.items()):raise ValueError('invalid final dimension recheck policy map')
if not set(FINAL_DIMENSION_RECHECK_POLICIES).issubset(FINAL_DN_RECHECK_POLICIES):raise ValueError('final dimension recheck requires current DN recheck')
FINAL_DIMENSION_SCREEN_POLICIES=json.loads(args.final_dimension_screen_policy_map.read_text(encoding='utf8')) if args.final_dimension_screen_policy_map else {}
if not isinstance(FINAL_DIMENSION_SCREEN_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in FINAL_DIMENSION_SCREEN_POLICIES.items()):raise ValueError('invalid final dimension screen policy map')
FINAL_COMPOUND_DN_POLICIES=json.loads(args.final_compound_dn_policy_map.read_text(encoding='utf8')) if args.final_compound_dn_policy_map else {}
if not isinstance(FINAL_COMPOUND_DN_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'source_sha256','graph_sha256','text_layers'} or not isinstance(v['text_layers'],list) or not v['text_layers'] or any(not isinstance(x,str) or not x for x in v['text_layers']) for k,v in FINAL_COMPOUND_DN_POLICIES.items()):raise ValueError('invalid final compound DN policy map')
if not set(FINAL_COMPOUND_DN_POLICIES).issubset(FINAL_DIMENSION_SCREEN_POLICIES):raise ValueError('final compound DN requires final graph dimension screen')
FINAL_PLAN_LINE_POLICIES=json.loads(args.final_plan_line_policy_map.read_text(encoding='utf8')) if args.final_plan_line_policy_map else {}
if not isinstance(FINAL_PLAN_LINE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in FINAL_PLAN_LINE_POLICIES.items()):raise ValueError('invalid final plan line policy map')
if not set(FINAL_PLAN_LINE_POLICIES).issubset(FINAL_DIMENSION_SCREEN_POLICIES):raise ValueError('final plan line inventory requires final graph dimension screen')
FINAL_CROSSOVER_POLICIES=json.loads(args.final_crossover_length_policy_map.read_text(encoding='utf8')) if args.final_crossover_length_policy_map else {}
if not isinstance(FINAL_CROSSOVER_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in FINAL_CROSSOVER_POLICIES.items()):raise ValueError('invalid final crossover length policy map')
if not set(FINAL_CROSSOVER_POLICIES).issubset(FINAL_DIMENSION_SCREEN_POLICIES):raise ValueError('crossover correction requires explicitly rebound final source and structural checks')
FINAL_NAMED_LEADER_POLICIES=json.loads(args.final_named_leader_policy_map.read_text(encoding='utf8')) if args.final_named_leader_policy_map else {}
FINAL_UNIDENTIFIED_EQUIPMENT_POLICIES=json.loads(args.final_unidentified_equipment_policy_map.read_text(encoding='utf8')) if args.final_unidentified_equipment_policy_map else {}
FINAL_LOCAL_DN_POLICIES=json.loads(args.final_local_dn_policy_map.read_text(encoding='utf8')) if args.final_local_dn_policy_map else {}
FINAL_NEAR_TEE_STATE_POLICIES=json.loads(args.final_near_tee_state_policy_map.read_text(encoding='utf8')) if args.final_near_tee_state_policy_map else {}
FINAL_EQUIPMENT_PAIR_CANDIDATES=json.loads(args.final_equipment_pair_candidates_map.read_text(encoding='utf8')) if args.final_equipment_pair_candidates_map else {}
if not set(BATCH_CONFIRMED_CIRCLES).issubset(FINAL_DIMENSION_SCREEN_POLICIES):raise ValueError('batch circles require explicitly rebound final source checks')
if not isinstance(FINAL_NAMED_LEADER_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in FINAL_NAMED_LEADER_POLICIES.items()):raise ValueError('invalid final named leader policy map')
if not set(FINAL_NAMED_LEADER_POLICIES).issubset(FINAL_DIMENSION_SCREEN_POLICIES):raise ValueError('named leader screen requires explicit final graph selection')
FINAL_NEAR_ENDPOINT_POLICIES=json.loads(args.final_near_endpoint_policy_map.read_text(encoding='utf8')) if args.final_near_endpoint_policy_map else {}
if not isinstance(FINAL_NEAR_ENDPOINT_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in FINAL_NEAR_ENDPOINT_POLICIES.items()):raise ValueError('invalid final near-endpoint policy map')
if not set(FINAL_NEAR_ENDPOINT_POLICIES).issubset(FINAL_DIMENSION_SCREEN_POLICIES):raise ValueError('near-endpoint screen requires explicit final graph selection')
FINAL_COMPONENT_POLICIES=json.loads(args.final_component_conservation_policy_map.read_text(encoding='utf8')) if args.final_component_conservation_policy_map else {}
if not isinstance(FINAL_COMPONENT_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','repair_stage'} or not isinstance(v['policy'],str) or not v['policy'] or v['repair_stage'] not in ('topology-expert-flex','topology-late-flexible-joints') for k,v in FINAL_COMPONENT_POLICIES.items()):raise ValueError('invalid final component conservation policy map')
if not set(FINAL_COMPONENT_POLICIES).issubset(FINAL_DIMENSION_SCREEN_POLICIES):raise ValueError('component conservation requires explicit final graph selection')
FINAL_EXPERT_NODE_POLICIES=json.loads(args.final_expert_node_reconciliation_map.read_text(encoding='utf8')) if args.final_expert_node_reconciliation_map else {}
if not isinstance(FINAL_EXPERT_NODE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','issue','context'} or any(not isinstance(x,str) or not x for x in v.values()) for k,v in FINAL_EXPERT_NODE_POLICIES.items()):raise ValueError('invalid expert node reconciliation map')
if not set(FINAL_EXPERT_NODE_POLICIES).issubset(FINAL_DIMENSION_SCREEN_POLICIES):raise ValueError('expert node reconciliation requires explicit final graph selection')

FINAL_SOURCE_SEGMENT_DIMENSION_POLICIES=json.loads(args.final_source_segment_dimension_policy_map.read_text(encoding='utf8')) if args.final_source_segment_dimension_policy_map else {}
if not isinstance(FINAL_SOURCE_SEGMENT_DIMENSION_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in FINAL_SOURCE_SEGMENT_DIMENSION_POLICIES.items()):raise ValueError('invalid final source segment dimension policy map')
POST_DIMENSION_INTERFACE_POLICIES=json.loads(args.post_dimension_confirmed_interface_policy_map.read_text(encoding='utf8')) if args.post_dimension_confirmed_interface_policy_map else {}
if not isinstance(POST_DIMENSION_INTERFACE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','inventory_policy'} or any(not isinstance(x,str) or not x for x in v.values()) for k,v in POST_DIMENSION_INTERFACE_POLICIES.items()):raise ValueError('invalid post-dimension confirmed interface policy map')
if POST_DIMENSION_INTERFACE_POLICIES and not args.endpoint_semantics:raise ValueError('post-dimension interfaces require endpoint semantics')
if not isinstance(POST_CONFIRMED_SOURCE_CIRCLE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in POST_CONFIRMED_SOURCE_CIRCLE_POLICIES.items()):raise ValueError('invalid post-confirmed source circle policy map')
if not set(POST_CONFIRMED_SOURCE_CIRCLE_POLICIES).issubset(FOLLOWUP_CONFIRMED_CIRCLE_POLICIES):raise ValueError('post-confirmed source circles require the followup confirmed stage')
if not isinstance(FOLLOWUP_CONFIRMED_CIRCLE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','screen'} or any(not isinstance(x,str) or not x for x in v.values()) for k,v in FOLLOWUP_CONFIRMED_CIRCLE_POLICIES.items()):raise ValueError('invalid followup confirmed circle policy map')
if FOLLOWUP_CONFIRMED_CIRCLE_POLICIES and not args.endpoint_semantics:raise ValueError('followup confirmed circles require endpoint semantics')
if CALIBRATED_SOURCE_CIRCLE_POLICIES and not args.endpoint_semantics:raise ValueError('calibrated source review requires endpoint semantics')
FOLLOWUP_SOURCE_REVIEWED_POLICIES=json.loads(args.followup_source_reviewed_circle_policy_map.read_text(encoding='utf8')) if args.followup_source_reviewed_circle_policy_map else {}
if FOLLOWUP_SOURCE_REVIEWED_POLICIES and not args.endpoint_semantics:raise ValueError('followup source review requires endpoint semantics')
CIRCLE_CONFLICT_RECONCILIATION_POLICIES=json.loads(args.circle_conflict_reconciliation_policy_map.read_text(encoding='utf8')) if args.circle_conflict_reconciliation_policy_map else {}
if CIRCLE_CONFLICT_RECONCILIATION_POLICIES and not args.endpoint_semantics:raise ValueError('conflict reconciliation requires endpoint semantics')
CONFIRMED_GAP_TEE_POLICIES=json.loads(args.confirmed_gap_tee_policy_map.read_text(encoding='utf8')) if args.confirmed_gap_tee_policy_map else {}
CONFIRMED_OVERLAP_POLICIES=json.loads(args.confirmed_overlap_branch_policy_map.read_text(encoding='utf8')) if args.confirmed_overlap_branch_policy_map else {}
FOLLOWUP_OVERLAP_POLICIES=json.loads(args.followup_overlap_policy_map.read_text(encoding='utf8')) if args.followup_overlap_policy_map else {}
if not isinstance(FOLLOWUP_OVERLAP_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,list) or not v or any(not isinstance(x,dict) or set(x)!={'policy','evidence_manifest'} or any(not isinstance(y,str) for y in x.values()) for x in v) for k,v in FOLLOWUP_OVERLAP_POLICIES.items()):raise ValueError('invalid followup overlap policy map')
if not set(FOLLOWUP_OVERLAP_POLICIES).issubset(CONFIRMED_OVERLAP_POLICIES):raise ValueError('followup overlap requires initial overlap stage')
HIDDEN_BRANCH_SCREEN_POLICIES=json.loads(args.hidden_branch_screen_policy_map.read_text(encoding='utf8')) if args.hidden_branch_screen_policy_map else {}
if not isinstance(HIDDEN_BRANCH_SCREEN_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in HIDDEN_BRANCH_SCREEN_POLICIES.items()):raise ValueError('invalid hidden branch screen policy map')
if not isinstance(CONFIRMED_OVERLAP_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','evidence_manifest'} or any(not isinstance(x,str) for x in v.values()) for k,v in CONFIRMED_OVERLAP_POLICIES.items()):raise ValueError('invalid confirmed overlap policy map')
PARTIAL_SOURCE_LENGTH_POLICIES=json.loads(args.partial_source_length_policy_map.read_text(encoding='utf8')) if args.partial_source_length_policy_map else {}
if not isinstance(CONFIRMED_GAP_TEE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','evidence'} or any(not isinstance(x,str) for x in v.values()) for k,v in CONFIRMED_GAP_TEE_POLICIES.items()):raise ValueError('invalid confirmed gap tee policy map')
if not isinstance(PARTIAL_SOURCE_LENGTH_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','coverage'} or any(not isinstance(x,str) for x in v.values()) for k,v in PARTIAL_SOURCE_LENGTH_POLICIES.items()):raise ValueError('invalid partial source length policy map')
if not isinstance(CONFIRMED_CIRCLE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','screen'} or any(not isinstance(x,str) for x in v.values()) for k,v in CONFIRMED_CIRCLE_POLICIES.items()):raise ValueError('invalid confirmed circle policy map')
if not isinstance(CIRCLE_RIM_SCREEN_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in CIRCLE_RIM_SCREEN_POLICIES.items()):raise ValueError('invalid circle rim screen policy map')
if not isinstance(SEGMENT_DIMENSION_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in SEGMENT_DIMENSION_POLICIES.items()):raise ValueError('invalid segment dimension policy map')
if not isinstance(DETAIL_GLYPH_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in DETAIL_GLYPH_POLICIES.items()):raise ValueError('invalid detail glyph policy map')
if not isinstance(DN_INHERITANCE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in DN_INHERITANCE_POLICIES.items()):raise ValueError('invalid DN inheritance policy map')
if not isinstance(LOCAL_DN_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in LOCAL_DN_POLICIES.items()):raise ValueError('invalid local DN policy map')
if not isinstance(CONFIRMED_INTERFACE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','inventory_policy'} or any(not isinstance(x,str) for x in v.values()) for k,v in CONFIRMED_INTERFACE_POLICIES.items()):raise ValueError('invalid confirmed interface policy map')
if not isinstance(IDENTITY_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in IDENTITY_POLICIES.items()):raise ValueError('equipment identity policy map must map task IDs to policy paths')
DIRECT_DN_POLICIES=json.loads(args.direct_dn_policy_map.read_text(encoding='utf8')) if args.direct_dn_policy_map else {}
if not isinstance(DIRECT_DN_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in DIRECT_DN_POLICIES.items()):raise ValueError('direct DN policy map must map task IDs to policy paths')
SIMILAR_BOUNDARY_POLICIES=json.loads(args.similar_boundary_policy_map.read_text(encoding='utf8')) if args.similar_boundary_policy_map else {}
if not isinstance(SIMILAR_BOUNDARY_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,dict) or set(v)!={'policy','issue'} or any(not isinstance(x,str) for x in v.values()) for k,v in SIMILAR_BOUNDARY_POLICIES.items()) or not set(SIMILAR_BOUNDARY_POLICIES).issubset(BOUNDARY_POLICIES):raise ValueError('similar boundary policy requires a configured initial boundary stage')

SOURCE_REVIEW_CIRCLE_POLICIES=json.loads(args.source_reviewed_circle_policy_map.read_text(encoding='utf8')) if args.source_reviewed_circle_policy_map else {}
if not isinstance(SOURCE_REVIEW_CIRCLE_POLICIES,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in SOURCE_REVIEW_CIRCLE_POLICIES.items()):raise ValueError('invalid source reviewed circle map')
if SOURCE_REVIEW_CIRCLE_POLICIES and not args.endpoint_semantics:raise ValueError('source reviewed circles require endpoint semantics')
if set(SOURCE_REVIEW_CIRCLE_POLICIES)-set(CONFIRMED_INTERFACE_POLICIES):raise ValueError('source reviewed circle reconstruction currently follows confirmed interfaces')
if set(SOURCE_REVIEW_CIRCLE_POLICIES)&(set(CONFIRMED_CIRCLE_POLICIES)|set(CONFIRMED_GAP_TEE_POLICIES)|set(CONFIRMED_OVERLAP_POLICIES)|set(FOLLOWUP_OVERLAP_POLICIES)):raise ValueError('combine source reviewed and other connection policies only after explicit stage rebase')

def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def table(p,rows,fields):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def pt(v):return (float(v[0]),float(v[1]))
def key(p):return tuple(round(x/ TOL) for x in p)
def distance(a,b):return math.dist(a,b)
def on(p,a,b,tol=TOL):
 dx=b[0]-a[0];dy=b[1]-a[1];l=dx*dx+dy*dy
 if not l:return None
 t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/l
 q=(a[0]+t*dx,a[1]+t*dy)
 return max(0,min(1,t)) if -tol/math.sqrt(l)<=t<=1+tol/math.sqrt(l) and distance(p,q)<=tol else None
reg=json.loads((BATCH/'batch.json').read_text(encoding='utf-8'));lib=BATCH/'reference-library/parameters-v1';manifest=json.loads((lib/'catalog-manifest.json').read_text(encoding='utf-8'));protos=json.loads((lib/'cad-pattern-prototypes.json').read_text(encoding='utf-8'));proto_by_block={x['source_block']:x for x in protos}
eligible={t['task_id'] for t in reg['tasks'] if t['sheet'] in ['08','09','10']}
from sideview_equipment_ownership_stage import load_policy_map as load_sideview_ownership_map,run_stage as run_sideview_ownership_stage
SIDEVIEW_EQUIPMENT_OWNERSHIPS=load_sideview_ownership_map(args.source_sideview_equipment_ownership_policy_map,eligible)
from inherited_wave_family_stage import load_policy_map as load_inherited_wave_map,run_stage as run_inherited_wave_stage
INHERITED_WAVE_CONTINUITIES=load_inherited_wave_map(args.inherited_wave_continuity_map,eligible)
from plan_circle_continuity_family_stage import load_policy_map as load_plan_circle_map,run_stage as run_plan_circle_stage
PLAN_CIRCLE_CONTINUITIES=load_plan_circle_map(args.plan_circle_continuity_map,eligible)
from capped_branch_annotation_stage import load_policy_map as load_capped_annotation_map,run_stage as run_capped_annotation_stage
CAPPED_BRANCH_ANNOTATIONS=load_capped_annotation_map(args.capped_branch_annotation_policy_map,eligible)
from reviewed_interface_owner_stage import load_policy_map as load_reviewed_owner_map,run_stage as run_reviewed_owner_stage
REVIEWED_INTERFACE_OWNERS=load_reviewed_owner_map(args.reviewed_interface_owner_map,eligible)
from wave_main_cohort_stage import load_policy_map as load_wave_main_cohort_map,run_stage as run_wave_main_cohort_stage
WAVE_MAIN_COHORTS=load_wave_main_cohort_map(args.wave_main_cohort_map,eligible)
if WAVE_MAIN_COHORTS and not args.endpoint_semantics:raise ValueError('wave main cohort requires endpoint semantics')
from reviewed_plan_gap_stage import load_policy_map as load_reviewed_gap_map,run_stage as run_reviewed_gap_stage
REVIEWED_PLAN_GAPS=load_reviewed_gap_map(args.reviewed_plan_gap_map,eligible)
if REVIEWED_PLAN_GAPS and not args.endpoint_semantics:raise ValueError('reviewed gaps require endpoint semantics')
if set(REVIEWED_PLAN_GAPS)-set(PLAN_CIRCLE_CONTINUITIES):raise ValueError('reviewed gaps require a current pending native-T parent')
if set(REVIEWED_PLAN_GAPS)&set(REVIEWED_INTERFACE_OWNERS):raise ValueError('reviewed gap and owner composition requires a separately supported parent')
if REVIEWED_INTERFACE_OWNERS and not args.endpoint_semantics:raise ValueError('reviewed owners require endpoint semantics')
if set(REVIEWED_INTERFACE_OWNERS)-set(FINAL_CIRCLE_PATHS)-set(INHERITED_WAVE_CONTINUITIES):raise ValueError('reviewed owners require a supported final circle or wave parent')
if set(REVIEWED_INTERFACE_OWNERS)&set(PLAN_CIRCLE_CONTINUITIES):raise ValueError('reviewed owners require a separately supported circle-continuity composition')
if CAPPED_BRANCH_ANNOTATIONS and not args.endpoint_semantics:raise ValueError('capped-branch annotation requires endpoint semantics')
if INHERITED_WAVE_CONTINUITIES and not args.endpoint_semantics:raise ValueError('inherited wave continuity requires endpoint semantics')
if set(INHERITED_WAVE_CONTINUITIES)-set(LAYOUT_EQUIPMENT_OWNERSHIPS):raise ValueError('inherited wave continuity requires a calibrated layout ownership parent')
if set(INHERITED_WAVE_CONTINUITIES)&(set(SIDEVIEW_EQUIPMENT_OWNERSHIPS)|set(FINAL_CIRCLE_PATHS)):raise ValueError('inherited wave continuity needs a separately supported parent composition')
if SIDEVIEW_EQUIPMENT_OWNERSHIPS and not args.endpoint_semantics:raise ValueError('sideview equipment ownership requires endpoint semantics')
if set(SIDEVIEW_EQUIPMENT_OWNERSHIPS)-set(LAYOUT_EQUIPMENT_OWNERSHIPS):raise ValueError('sideview equipment ownership requires a calibrated layout ownership parent')
if set(SIDEVIEW_EQUIPMENT_OWNERSHIPS)&set(FINAL_CIRCLE_PATHS):raise ValueError('sideview equipment ownership and final circle normalization need a separately supported composition')
if set(FLEX_POLICIES)-eligible:raise ValueError('flex policy map contains unrecognized ceiling task IDs')
if set(DIRECT_DN_POLICIES)-eligible:raise ValueError('direct DN policy map contains unrecognized ceiling task IDs')
if set(IDENTITY_POLICIES)-eligible:raise ValueError('equipment identity policy map contains unrecognized ceiling task IDs')
if set(CONFIRMED_INTERFACE_POLICIES)-eligible:raise ValueError('confirmed interface stage has unrecognized task IDs')
if (set(CONFIRMED_INTERFACE_POLICIES)&set(DIRECT_DN_POLICIES))-set(IDENTITY_POLICIES):raise ValueError('confirmed interface direct DN recheck requires equipment identity stage')
if set(CONFIRMED_CIRCLE_POLICIES)-set(CONFIRMED_INTERFACE_POLICIES):raise ValueError('confirmed circle stage requires confirmed interface stage')
if set(CONFIRMED_CIRCLE_POLICIES)&(set(LOCAL_DN_POLICIES)|set(DN_INHERITANCE_POLICIES)|set(SEGMENT_DIMENSION_POLICIES)):raise ValueError('confirmed circle stage requires rebuilding later attribute policies')
if set(LOCAL_DN_POLICIES)-eligible or set(LOCAL_DN_POLICIES)-set(CONFIRMED_INTERFACE_POLICIES):raise ValueError('local DN stage requires a confirmed interface policy for each task')
if set(DN_INHERITANCE_POLICIES)-eligible or set(DN_INHERITANCE_POLICIES)-set(LOCAL_DN_POLICIES):raise ValueError('DN inheritance candidates require local DN observations for each task')
if set(SEGMENT_DIMENSION_POLICIES)-eligible or set(SEGMENT_DIMENSION_POLICIES)-set(DN_INHERITANCE_POLICIES):raise ValueError('segment dimension stage requires DN inheritance candidate stage for each task')
if set(DETAIL_GLYPH_POLICIES)-eligible or set(DETAIL_GLYPH_POLICIES)-set(DETAIL_POLICIES):raise ValueError('detail glyph comparison requires a detail policy for each task')
if set(FINAL_DIMENSION_SCREEN_POLICIES)-eligible:raise ValueError('dimension screen contains unrecognized ceiling task IDs')
if set(FINAL_ID_AUDITS)-eligible or set(FINAL_ID_AUDITS)-set(FINAL_DIMENSION_SCREEN_POLICIES):raise ValueError('final ID audit requires final dimension screen for each eligible task')
if set(FINAL_SOURCE_SEGMENT_DIMENSION_POLICIES)-eligible:raise ValueError('final source dimension policy contains unrecognized ceiling task IDs')
if set(CIRCLE_RIM_SCREEN_POLICIES)-eligible:raise ValueError('circle rim screen contains unrecognized ceiling task IDs')
for task in reg['tasks']:
 overlap_followup_graph=None
 sheet=task['sheet']
 if sheet not in ['08','09','10']:continue
 tid=task['task_id'];old=BATCH/'tasks'/tid;meta=json.loads((old/'task.json').read_text(encoding='utf-8'));src=(old/meta['source']['dxf']).resolve();out=OUT/'tasks'/tid/'topology';out.mkdir(parents=True,exist_ok=True);rep=out.parent/'reports';rep.mkdir(exist_ok=True);d,readability=read_source(src);m=d.modelspace();segments=[];circles=[];layercounts=collections.defaultdict(collections.Counter)
 for e in m:
  layercounts[e.dxf.layer][e.dxftype()]+=1
  sy={'空调冷冻水供水':'supply','空调冷冻水回水':'return'}.get(e.dxf.layer)
  if sy and e.dxftype()=='CIRCLE':circles.append({'handle':e.dxf.handle,'center':pt(e.dxf.center),'radius':e.dxf.radius,'system':sy})
  if e.dxftype()=='LINE' and (sy or e.dxf.layer=='空调立管、水平支管'):
   a,b=pt(e.dxf.start),pt(e.dxf.end)
   if distance(a,b)>TOL:segments.append({'id':len(segments),'handle':e.dxf.handle,'layer':e.dxf.layer,'system':sy,'a':a,'b':b,'cuts':{0.,1.}})
 for s in segments:
  if s['system'] is None and any(max(distance(s['a'],c['center']),distance(s['b'],c['center']))<=400 for c in circles):s['excluded_circle_local_geometry']=True
 expert_riser_policy=NORM[sheet].get('expert_riser_connection_policy',{})
 if expert_riser_policy and expert_riser_policy.get('source_sha256')!=readability['source_sha256']:raise ValueError('expert riser source hash mismatch')
 expert_riser_connections=apply_source_riser_connections(circles,segments,expert_riser_policy,TOL)
 # A circle explicitly lying on a same-system main can close a branch ending on its circumference.
 circle_bridges=[]
 riser_terminals=[]
 for c in circles:
  match=riser_terminal_candidate(c,segments,NORM[sheet].get('riser_terminal_radii',[]),TOL)
  if match:
   s,end,p=match;s['original_'+end]=p;s[end]=c['center'];riser_terminals.append(dict(circle=c,pipe_handle=s['handle'],original_endpoint=p,semantic_endpoint=c['center']))
 expert_circle_policy=NORM[sheet].get('expert_circle_tee_policy',{})
 if expert_circle_policy and expert_circle_policy.get('source_sha256')!=readability['source_sha256']:raise ValueError('expert circle source hash mismatch')
 expected_circles={x['circle_handle'] for x in expert_circle_policy.get('circles',[])}
 source_circle_policy=NORM[sheet].get('source_reviewed_circle_policy',{})
 reviewed_circles=load_circle_source_review(source_circle_policy,readability['source_sha256'])
 if expected_circles & set(reviewed_circles):raise ValueError('source review cannot override an expert circle policy')
 if len(expected_circles)!=len(expert_circle_policy.get('circles',[])):raise ValueError('duplicate expert circle')
 for c in circles:
  match=expert_circle_connection_candidate(c,segments,expert_circle_policy,TOL) if c['handle'] in expected_circles else reviewed_circle_candidate(d,c,segments,reviewed_circles,TOL) if c['handle'] in reviewed_circles else circle_connection_candidate(c,segments,TOL)
  if match is None:continue
  main,branch=match;mains=[main];branches=[branch];center=c['center']
  u,side,end=branches[0];u['original_'+side]=end;u[side]=center;u['circle_connection_evidence']=c['handle'];circle_bridges.append({'circle_handle':c['handle'],'circle_radius':c['radius'],'branch_handle':u['handle'],'main_handle':mains[0]['handle'],'system':c['system'],'original_endpoint':end,'semantic_endpoint':center,'bridge_length':distance(end,center),'rule':'circle-centered-main plus unique radial branch stopping at circumference',**({'expert_issue':expert_circle_policy['expert_issue']} if c['handle'] in expected_circles else {})})
 if expected_circles-{x['circle_handle'] for x in circle_bridges}:raise ValueError('configured expert circle missing from source')
 if set(reviewed_circles)-{x['circle_handle'] for x in circle_bridges}:raise ValueError('reviewed circle missing from source')
 for bridge in circle_bridges:
  if bridge['circle_handle'] in reviewed_circles:
   bridge['source_comparison']={'review_kind':'technical_native_source_comparison','review_manifest':source_circle_policy['review_manifest'],'review_sha256':source_circle_policy['review_sha256'],'pair_sha256':reviewed_circles[bridge['circle_handle']]['pair_sha256'],'human_accepted':False}
 # Shared source crossover normalization precedes junction and logical-edge construction.
 pg.set_tolerance(TOL)
 qualified=[dict(s,source_system=s['system'])for s in segments if s['system']and not s.get('excluded_circle_local_geometry')]
 normalized,near_audit=snap_near_junction_endpoints(qualified,NORM[sheet].get('near_junction'))
 for n in normalized:
  segments[n['id']].update({k:n[k] for k in ('a','b','original_a','original_b') if k in n})
 qualified=normalized
 circle_crossover_conflicts=[]
 bridges,crossover_audit=recover_straight_crossovers(qualified,[],NORM[ sheet ]['straight_crossovers'],source_circles=circles,circle_conflicts=circle_crossover_conflicts)
 for bridge in bridges:
  bridge.update(id=len(segments),layer=next(s['layer']for s in segments if s['system']==bridge['system']),cuts={0.,1.});segments.append(bridge)
 dump(out/'normalization_audit.json',{'near_junction':near_audit,'crossovers':crossover_audit,'configuration':NORM[sheet],'relative_elevation':'unknown'})
 # Only endpoint incidence connects. Interior/interior crossings remain independent.
 junction_pairs=[];contact_pairs=[]
 for i,s in enumerate(segments):
  for t in segments[i+1:]:
   if s.get('excluded_circle_local_geometry') or t.get('excluded_circle_local_geometry'):continue
   if s['system'] and t['system'] and s['system']!=t['system']:continue
   hits=[]
   for frac,p in [(0.,s['a']),(1.,s['b'])]:
    v=on(p,t['a'],t['b'])
    if v is not None and not(t.get('crossing_connectivity')and min(distance(p,t['a']),distance(p,t['b']))>TOL):s['cuts'].add(frac);t['cuts'].add(v);hits.append(p);contact_pairs.append(((s['id'],frac),(t['id'],v),p))
   for frac,p in [(0.,t['a']),(1.,t['b'])]:
    v=on(p,s['a'],s['b'])
    if v is not None and not(s.get('crossing_connectivity')and min(distance(p,s['a']),distance(p,s['b']))>TOL):t['cuts'].add(frac);s['cuts'].add(v);hits.append(p);contact_pairs.append(((t['id'],frac),(s['id'],v),p))
   if hits:junction_pairs.append((i,t['id']))
 parent=list(range(len(segments)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 def union(i,j):parent[find(i)]=find(j)
 # Only untyped components propagate type, never bridge supply/return.
 for i,j in junction_pairs:
  if segments[i]['system'] is None and segments[j]['system'] is None:union(i,j)
 anchors=collections.defaultdict(set)
 for i,j in junction_pairs:
  s,t=segments[i],segments[j]
  if s['system'] is None and t['system']:anchors[find(i)].add(t['system'])
  if t['system'] is None and s['system']:anchors[find(j)].add(s['system'])
 for s in segments:
  if s['system'] is None:
   ass=anchors[find(s['id'])] if not s.get('excluded_circle_local_geometry') else set();s['system']=next(iter(ass)) if len(ass)==1 else None;s['inference']='unique_component_anchor' if len(ass)==1 else ('conflicting_system_anchors' if len(ass)>1 else 'no_system_anchor')
 # Canonicalize only proven endpoint-incidence contacts, never arbitrary nearby crossings.
 contact_point=canonical_contact_points(segments,contact_pairs)
 dump(out/'accepted-contact-canonicalization.json',[dict(endpoint_segment=a[0],main_segment=b[0],endpoint_fraction=a[1],main_fraction=b[1],point=contact_point(segments[a[0]],a[1])) for a,b,p in contact_pairs])
 verts={};adj=collections.defaultdict(list);atomic=[]
 for s in segments:
  if not s['system']:continue
  vals=sorted(s['cuts']);pts=[contact_point(s,v) for v in vals]
  for a,b in zip(pts,pts[1:]):
   if distance(a,b)<=TOL:continue
   ka,kb=(s['system'],key(a)),(s['system'],key(b));verts.setdefault(ka,a);verts.setdefault(kb,b)
   if any(atomic[j]['b']==kb if atomic[j]['a']==ka else atomic[j]['a']==kb for j in adj[ka]):continue
   eid=len(atomic);atomic.append({'a':ka,'b':kb,'source_handle':s['handle'],'source_handles':s.get('source_handles',[s['handle']]),'source_segment':s['id'],'length':distance(a,b)});adj[ka].append(eid);adj[kb].append(eid)
 tee=[];pending=[]
 for k,eds in adj.items():
  if len(eds)<3:continue
  p=verts[k];near=[c['handle'] for c in circles if c['system']==k[0] and distance(c['center'],p)<=400 and c['handle'] not in {b['circle_handle'] for b in circle_bridges}]
  rays=[]
  for ae in eds:
   atom=atomic[ae];other=atom['b'] if atom['a']==k else atom['a'];q=verts[other];dx,dy=q[0]-p[0],q[1]-p[1];ln=math.hypot(dx,dy);v=(dx/ln,dy/ln)
   if not any(v[0]*r[0]+v[1]*r[1]>.999999 for r in rays):rays.append(v)
  centered=[c for c in circles if c['system']==k[0]and distance(c['center'],p)<=TOL]
  if len(eds)==3 and len(rays)==3 and(not near or centered):tee.append(k)
  else:pending.append({'system':k[0],'x':p[0],'y':p[1],'degree':len(eds),'reason':'riser_or_circle_symbol_contact' if near else 'non_three_way_intersection','circle_handles':near})
 tee.sort(key=lambda k:(k[0],verts[k][1],verts[k][0]));nodeid={k:f'T{i+1:03}' for i,k in enumerate(tee)}
 nodes=[{'node_id':nodeid[k],'node_type':'tee','subtype':'physical_tee','floor':int(sheet)-7,'system':k[0],'x':verts[k][0],'y':verts[k][1],'label':nodeid[k],'source_handles':sorted({atomic[x]['source_handle'] for x in adj[k]}),'evidence':'three endpoint-incidence rays; no interior-crossing join'} for k in tee]
 interface_evidence=[];virtual_ports=[]
 for r in riser_terminals:
  c=r['circle'];center=c['center'];k=(c['system'],key(center))
  if k not in verts or len(adj[k])!=1:continue
  vid=f'RIF{len(interface_evidence)+1:03}';nodeid[k]=vid;pid=vid+'-P1';interface_evidence.append(dict(interface_id=vid,circle_handle=c['handle'],pipe_handles=[r['pipe_handle']],center=center,original_endpoint=r['original_endpoint'],system=c['system'],semantic='out_of_plane_riser_terminal',evidence_state='source_profile_circle_and_unique_radial_pipe',equipment_association='unresolved'))
  nodes.append(dict(node_id=vid,node_type='virtual_equipment',subtype='out_of_plane_riser',floor=int(sheet)-7,system=c['system'],x=center[0],y=center[1],label=vid,source_handle=c['handle'],source_handles=[c['handle'],r['pipe_handle']],ports=[dict(port_id=pid,system=c['system'],x=center[0],y=center[1])],connection_status='riser_destination_unresolved'))
  virtual_ports.append(dict(virtual_equipment_id=vid,port_id=pid,system=c['system'],x=center[0],y=center[1]))
 glyphs=[u for u in segments if u['layer']=='空调立管、水平支管']
 for c in circles:
  match=match_out_of_plane_symbol(c,glyphs,TOL)
  if match is None:continue
  arms,bars=match;center=c['center'];vkey=(c['system'],key(center))
  if vkey not in verts or len(adj[vkey])!=1:continue
  vid=f'VIF{len(interface_evidence)+1:03}';nodeid[vkey]=vid;pid=vid+'-P1';evidence={'interface_id':vid,'circle_handle':c['handle'],'glyph_handles':[u['handle'] for u in arms+bars],'pipe_handles':sorted({atomic[j]['source_handle'] for j in adj[vkey]}),'center':center,'system':c['system'],'semantic':'out_of_plane_pipe_interface','evidence_state':'complete_native_circle_V_double_bar_pattern','equipment_association':'unresolved'};interface_evidence.append(evidence)
  nodes.append({'node_id':vid,'node_type':'virtual_equipment','subtype':'out_of_plane_interface','floor':int(sheet)-7,'system':c['system'],'x':center[0],'y':center[1],'label':vid,'source_handle':c['handle'],'source_handles':[c['handle']]+evidence['glyph_handles'],'ports':[{'port_id':pid,'system':c['system'],'x':center[0],'y':center[1]}],'connection_status':'equipment_beyond_interface_unresolved'})
  virtual_ports.append({'virtual_equipment_id':vid,'port_id':pid,'system':c['system'],'x':center[0],'y':center[1]})
 # Unproven source terminals remain explicit review boundaries, not discarded branches.
 for k,eds in sorted(adj.items(),key=lambda x:(x[0][0],verts[x[0]][1],verts[x[0]][0])):
  if k in nodeid or len(eds)==2:continue
  nid='UT'+str(sum(n['node_id'].startswith('UT')for n in nodes)+1).zfill(4);nodeid[k]=nid;p=verts[k]
  nodes.append({'node_id':nid,'node_type':'virtual_equipment','subtype':'unresolved_source_terminal'if len(eds)==1 else'pending_source_junction','boundary_type':'unresolved_source_terminal','floor':int(sheet)-7,'system':k[0],'x':p[0],'y':p[1],'label':nid,'review_required':True,'connection_status':'source_boundary_unconfirmed','source_handles':sorted({atomic[e]['source_handle']for e in eds})})
 edges=[];seen=set();used=set()
 for k in list(nodeid):
  for first in adj[k]:
   a=k;eid=first;path=[verts[k]];handles=[];walk=[];trail=set()
   while eid not in trail:
    trail.add(eid);atom=atomic[eid];b=atom['b'] if atom['a']==a else atom['a'];path.append(verts[b]);handles.extend(atom['source_handles']);walk.append(eid)
    if b in nodeid:
     signature=tuple(sorted((nodeid[k],nodeid[b])))+tuple(sorted(set(handles)))
     if b!=k and signature not in seen:
      seen.add(signature);used.update(walk);edges.append({'edge_id':f'E{len(edges)+1:04}','start_node_id':nodeid[k],'end_node_id':nodeid[b],'edge_type':('tee_to_virtual_equipment' if nodeid[k].startswith('VIF') or nodeid[b].startswith('VIF') else 'tee_to_tee'),'system':k[0],'start_floor':int(sheet)-7,'end_floor':int(sheet)-7,'path':path,'attribute_paths':[path],'path_length':sum(atomic[j]['length'] for j in walk),'source_handles':sorted(set(handles)),'equipment_counts':{},'equipment_names':[]})
     break
    if len(adj[b])!=2:break
    eid=next(j for j in adj[b] if j!=eid);a=b
 active_virtual_ids={v for edge in edges for v in [edge['start_node_id'],edge['end_node_id']] if v.startswith(('VIF','RIF','UT'))}
 pending_interface_nodes=[n for n in nodes if n['node_id'].startswith('VIF') and n['node_id'] not in active_virtual_ids]
 nodes=[n for n in nodes if n['node_type']!='virtual_equipment' or n['node_id'] in active_virtual_ids]
 virtual_ports=[v for v in virtual_ports if v['virtual_equipment_id'] in active_virtual_ids]
 for e in edges:
  e['path_points']=e['path']
  if e['start_node_id'].startswith(('VIF','RIF')):e['start_port_id']=e['start_node_id']+'-P1'
  if e['end_node_id'].startswith(('VIF','RIF')):e['end_port_id']=e['end_node_id']+'-P1'
 for i in interface_evidence:i['graph_state']='loaded_connected_interface' if i['interface_id'] in active_virtual_ids else 'source_candidate_no_completed_logical_edge'
 unbound_glyphs=identify_unbound_ceiling_symbols(circles,segments,{i['circle_handle'] for i in interface_evidence if i['graph_state']=='loaded_connected_interface'},tolerance=TOL,diagnostic_radius=1.0)
 dump(out/'unbound-complete-source-glyphs.json',{'source_sha256':readability['source_sha256'],'status':'source_comparison_pending' if unbound_glyphs else 'no_unbound_complete_glyphs_identified','scope':'complete source glyph inventory; near endpoints are not connectivity','glyphs':unbound_glyphs})
 riser_length_audit=correct_riser_source_lengths(edges,interface_evidence,TOL)
 expert_circle_length_audit=correct_circle_branch_lengths(nodes,edges,circle_bridges,TOL,crossovers=bridges)
 for connection in expert_riser_connections:
  if any(n['system']==connection['system'] and distance((n['x'],n['y']),connection['center'])<=TOL for n in nodes if n.get('system')):raise ValueError('expert riser connection unexpectedly became a node')
 expert_riser_connection_audit=separate_riser_source_path(edges,expert_riser_connections,TOL)
 wave_policy=NORM[sheet].get('expert_native_wave_terminal_policy',{})
 expert_wave_glyphs,expert_wave_audit=attach_expert_wave_terminals(d,nodes,edges,wave_policy,readability['source_sha256'])
 # Equipment identity is source bounded, not nearest graph/node attachment.
 inventory=json.loads((old/'enrichment/cad-elements.json').read_text(encoding='utf-8'));bounds={x['source_handle']:x['bounds'] for x in inventory};equipment=[]
 labels=[e for e in m.query('TEXT') if e.dxf.layer=='空调编号' and e.dxf.text.startswith('CRAH-')]
 eqblocks=[e for e in m.query('INSERT') if e.dxf.layer=='空调' and e.dxf.name in ['40kW','A$C478B2BA9']]
 for e in eqblocks:
  bb=bounds.get(e.dxf.handle)
  if not bb:continue
  lo,hi=bb;hits=[t for t in labels if lo[0]-600<=t.dxf.insert.x<=hi[0]+600 and lo[1]-600<=t.dxf.insert.y<=hi[1]+600]
  inside=[t for t in labels if lo[0]-TOL<=t.dxf.insert.x<=hi[0]+TOL and lo[1]-TOL<=t.dxf.insert.y<=hi[1]+TOL]
  if inside:hits=inside
  equipment.append({'source_handle':e.dxf.handle,'source_block':e.dxf.name,'bounds':bb,'label_candidates':[t.dxf.text for t in hits],'association_status':'unique_bounded_source_label' if len(hits)==1 else 'label_unresolved','connection_status':'ports_unresolved','parameter_candidates':['CRAH-40-BATTERY','CRAH-40-CARRIER'] if e.dxf.name=='40kW' else ['CRAH-155-DOWN','CRAH-155-UP'],'parameters_effective':False})
 # Keep unconnected identified equipment in graph only when unique label/block evidence.
 unique=collections.Counter(r['label_candidates'][0] for r in equipment if len(r['label_candidates'])==1)
 for r in equipment:
  if len(r['label_candidates'])==1 and unique[r['label_candidates'][0]]==1:
   lo,hi=r['bounds'];nodes.append({'node_id':r['label_candidates'][0],'node_type':'equipment','subtype':'CRAH','floor':int(sheet)-7,'label':r['label_candidates'][0],'x':(lo[0]+hi[0])/2,'y':(lo[1]+hi[1])/2,'source_handle':r['source_handle'],'source_block':r['source_block'],'connection_status':'ports_unresolved','parameter_candidates':r['parameter_candidates']})
 devices=[]
 for e in m.query('INSERT'):
  proto=proto_by_block.get(e.dxf.name)
  if proto is None:continue
  bb=bounds.get(e.dxf.handle)
  if not bb:continue
  lo,hi=bb;x,y=(lo[0]+hi[0])/2,(lo[1]+hi[1])/2
  native_signature='family_name_reference_only';native_center=None
  if e.dxf.name=='H-PICPNT-91':
   anchor=ball_valve_anchor(e)
   if anchor:native_center=anchor['center'];x,y=native_center;native_signature=anchor['signature']
  elif e.dxf.name=='平衡阀':
   anchor=balancing_valve_anchor(e)
   if anchor:native_center=anchor['center'];x,y=native_center;native_signature=anchor['signature']
  devices.append({'device_name' :f'{tid}-C-{e.dxf.handle}','equipment_type':{'H-PICPNT-91':'ball_valve','平衡阀':'balancing_valve'}.get(e.dxf.name,e.dxf.name),'type_code':proto['prototype_id'],'source_kind':'block_reference','source_block_name':e.dxf.name,'source_handle':e.dxf.handle,'x':x,'y':y,'edge_id':'','assignment_status':'unresolved','unresolved_reason':'source symbol exists; broken branch/device ports not yet proven','parameter_references':proto['parameter_references'],'native_signature':native_signature,'native_center':native_center})
 assigned_components=[]
 for dev in devices:
  if dev['native_center'] is None:continue
  center=dev['native_center'];matches=[ee for ee in edges if any(on(center,aa,bb,5.) is not None for aa,bb in zip(ee['path'],ee['path'][1:]))]
  if len(matches)!=1:continue
  ee=matches[0];dev['edge_id']=ee['edge_id'];dev['assignment_status']='assigned';dev['unresolved_reason']='';dev['edge_distance']=min(abs((bb[0]-aa[0])*(aa[1]-center[1])-(aa[0]-center[0])*(bb[1]-aa[1]))/distance(aa,bb) for aa,bb in zip(ee['path'],ee['path'][1:]) if on(center,aa,bb,5.) is not None);dev['assignment_tolerance_native_units']=5.;ee['equipment_counts'][dev['equipment_type']]=ee['equipment_counts'].get(dev['equipment_type'],0)+1;ee['equipment_names'].append(dev['device_name']);assigned_components.append(dev)
 aggregations=[]
 for ee in edges:
  for typ,num in ee['equipment_counts'].items():aggregations.append({'edge_id':ee['edge_id'],'start_node_id':ee['start_node_id'],'end_node_id':ee['end_node_id'],'equipment_type':typ,'device_count':num,'device_names':[v['device_name'] for v in devices if v['edge_id']==ee['edge_id'] and v['equipment_type']==typ]})
 contact_coverage=validate_junction_contacts(nodes,edges,circle_bridges+[c for c in near_audit if c.get('status')=='applied'],TOL)
 dump(out/'proven-contact-coverage.json',contact_coverage)
 gap_coverage=[]
 for i,bridge in enumerate(bridges,1):
  covered=[e['edge_id']for e in edges if any(on(bridge['a'],a,b,TOL*2)is not None and on(bridge['b'],a,b,TOL*2)is not None for a,b in zip(e['path'],e['path'][1:]))]
  if not covered:raise ValueError('Recovered crossover span missing from final logical edges')
  gap_coverage.append(dict(id='GAP-'+str(i).zfill(3),a=bridge['a'],b=bridge['b'],source_handles=bridge.get('source_handles',[]),edge_ids=covered,status='applied',crossing_connectivity='independent_pipes_no_junction'))
 dump(out/'source_gap_coverage.json',gap_coverage)
 graph={'schema_version':1,'project_id':tid,'status':'partial_unreviewed','nodes':nodes,'edges':edges,'virtual_equipment_ports':virtual_ports,'equipment_parameter_library':{'library_id':manifest.get('library_id'),'sha256':hashlib.sha256((lib/'catalog-manifest.json').read_bytes()).hexdigest()},'limitations':['Endpoint-incidence connections and source-proven crossover spans are used. Independent interior crossings are not joined.','Complete native interfaces and calibrated circle connections are resolved; unsupported valve and equipment gaps remain pending.','Unconfirmed source ends are explicit review-required virtual boundaries, not physical equipment ports.','Isolated source-identified equipment nodes are not connected by proximity.']}
 if circle_crossover_conflicts:
  graph['sourceCircleCrossoverConflicts']=circle_crossover_conflicts
  graph['preHilComparison']={'status':'pending','families':[{'id':'circle_crossover_conflict','status':'pending'}]}
 if wave_policy:
  graph.update(sourceTerminalGlyphs=expert_wave_glyphs,expertWaveNodeRepair={'issue':wave_policy['expert_issue'],'source_sha256':readability['source_sha256'],'nodes':expert_wave_audit,'scope':'Wave terminal identity only; remote continuation unconfirmed.'},metadata={'source_sha256':readability['source_sha256'],'hil_ready':False,'graph_complete':False})
 # Preserve hash-pinned legacy expert inputs; their later stages bind source independently.
 if not any(tid in policy for policy in (FLEX_POLICIES,WAVE_POLICIES,CIRCLE_PAIR_POLICIES,DETAIL_POLICIES,BOUNDARY_POLICIES,SIMILAR_BOUNDARY_POLICIES)):
  bind_graph_source(graph,readability['source_sha256'])
 total_length=sum(distance(s.get('original_a',s['a']),s.get('original_b',s['b'])) for s in segments);covered_length=sum(atomic[j]['length'] for j in used)-sum(x['graphic_radius_excluded'] for x in riser_length_audit+expert_circle_length_audit+expert_riser_connection_audit)-sum(x['graphic_crossover_spans_excluded'] for x in expert_circle_length_audit)
 summary={'task_id':tid,'status':'partial_unreviewed','nodes':len(nodes),'edges':len(edges),'tee_nodes':len(tee),'equipment_nodes':sum(n['node_type']=='equipment' for n in nodes),'virtual_equipment_nodes':len(active_virtual_ids),'source_interface_candidates':len(interface_evidence),'unconnected_interface_candidates':len(pending_interface_nodes),'unbound_complete_source_glyphs':len(unbound_glyphs),'circle_connections_recovered':len(circle_bridges),'circle_local_symbol_lines_withheld':sum(bool(s.get('excluded_circle_local_geometry')) for s in segments),'equipment_labels':len(labels),'equipment_symbols':len(eqblocks),'inline_components_detected':len(devices),'inline_components_assigned':len(assigned_components),'inline_components_unresolved':len(devices)-len(assigned_components),'pipe_source_line_entities':len(segments),'explicit_typed_source_lines':sum(s['layer']!='空调立管、水平支管' for s in segments),'branch_source_lines':sum(s['layer']=='空调立管、水平支管' for s in segments),'system_classified_lines':sum(bool(s['system']) for s in segments),'unclassified_lines':sum(not s['system'] for s in segments),'source_line_length':total_length,'accepted_edge_covered_length':covered_length,'accepted_edge_length_coverage':covered_length/total_length,'pending_non_tee_contacts':len(pending),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'tolerance_native_units':TOL,'unresolved_degree1_network_vertices':sum(len(v)==1 for v in adj.values()),'human_review':'unreviewed'}
 dump(out/'circle-connection-bridges.json',circle_bridges);dump(out/'expert-circle-source-length-audit.json',expert_circle_length_audit);dump(out/'expert-riser-connection-audit.json',expert_riser_connection_audit);dump(out/'expert-wave-terminal-audit.json',expert_wave_audit);dump(out/'out-of-plane-interface-evidence.json',interface_evidence);dump(out/'riser-source-length-audit.json',riser_length_audit);dump(out/'pending-interface-candidates.json',pending_interface_nodes);dump(out/'graph_with_edges.json',graph);dump(out/'edge_summary.json',summary);dump(out/'source-fragments.json',[{k:v for k,v in s.items() if k!='cuts'} for s in segments]);dump(out/'source-layer-inventory.json',layercounts);dump(out/'equipment-source-bindings.json',equipment);dump(out/'pending-junctions.json',pending);dump(out/'source-risers-and-circles.json',circles);dump(out/'unresolved-components.json',[v for v in devices if v['assignment_status']!='assigned']);dump(out/'native-component-assignment-evidence.json',assigned_components)
 table(out/'topology_nodes.csv',nodes,['node_id','node_type','subtype','floor','system','label','x','y','source_handle','source_handles','connection_status']);table(out/'edges.csv',edges,['edge_id','start_node_id','end_node_id','edge_type','system','start_floor','end_floor','path_length','path','source_handles']);table(out/'edge_device_instances.csv',devices,['device_name','equipment_type','type_code','x','y','source_kind','source_block_name','source_handle','edge_id','assignment_status','unresolved_reason']);table(out/'assigned_edge_device_instances.csv',assigned_components,['device_name','equipment_type','type_code','x','y','source_kind','source_block_name','source_handle','edge_id','edge_distance','assignment_status']);table(out/'edge_equipment_by_type.csv',aggregations,['edge_id','equipment_type','device_count','device_names']);table(out/'virtual_equipment_ports.csv',virtual_ports,['virtual_equipment_id','port_id','system','x','y'])
 # Overlay retains all pipe source geometry, so graph incompleteness remains visible.
 xs=[v for s in segments for v in [s['a'][0],s['b'][0]]];ys=[v for s in segments for v in [s['a'][1],s['b'][1]]];xmin,xmax=min(xs)-500,max(xs)+500;ymin,ymax=min(ys)-500,max(ys)+500
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{xmin} {-ymax} {xmax-xmin} {ymax-ymin}"><rect x="{xmin}" y="{-ymax}" width="{xmax-xmin}" height="{ymax-ymin}" fill="white"/>']
 for s in segments:svg.append(f'<path d="M{s["a"][0]} {-s["a"][1]} L{s["b"][0]} {-s["b"][1]}" fill="none" stroke="#c9ced4" stroke-width="40"/>')
 for edge in edges:
  points=' '.join(f'{x},{-y}' for x,y in edge['path']);color='#d34e4e' if edge['system']=='supply' else '#427ed0';svg.append(f'<polyline points="{points}" stroke="{color}" fill="none" stroke-width="85"/>')
 for n in nodes:
  svg.append(f'<circle cx="{n["x"]}" cy="{-n["y"]}" r="100" fill="#151f2a"/><text x="{n["x"]+140}" y="{-n["y"]}" font-size="340">{html.escape(n["node_id"])}</text>')
 svg.append('</svg>');(rep/'source-topology-overlay.svg').write_text(''.join(svg),encoding='utf-8')
 validation={'scope':'initial_topology_before_later_repair_stages','initial_graph_sha256':hashlib.sha256((out/'graph_with_edges.json').read_bytes()).hexdigest(),'checks':{'node_ids_unique':len(nodes)==len({n['node_id'] for n in nodes}),'edge_ids_unique':len(edges)==len({e['edge_id'] for e in edges}),'all_endpoints_exist':all(e['start_node_id'] in {n['node_id'] for n in nodes} and e['end_node_id'] in {n['node_id'] for n in nodes} for e in edges),'no_endpoint_nodes':all(n['node_type'] in ['tee','equipment','virtual_equipment'] for n in nodes),'all_unassigned_components_reported':len(devices)==summary['inline_components_unresolved']+summary['inline_components_assigned'],'no_human_confirmation':True},'acceptance':'partial_only_not_complete','source_coverage':summary};dump(rep/'validation-report.json',validation)
 (rep/'construction-report.md').write_text(f'# {tid} ceiling plan construction\n\nStatus: PARTIAL / UNREVIEWED. Source drawing: {src.name}.\n\nBuilt {len(tee)} three-ray junction nodes, {sum(n['node_type']=='equipment' for n in nodes)} uniquely source-bound CRAH nodes, {len(active_virtual_ids)} native interfaces and review-required boundary nodes ({len(unbound_glyphs)} further complete source glyphs remain pending outside the loaded graph; see unbound-complete-source-glyphs.json) and {len(edges)} logical edges. Recovered {len(circle_bridges)} unique circle-centered branch connections. Accepted paths cover {covered_length/total_length:.2%} of all candidate source pipe LINE length. {len(devices)} inline symbols reference the supplied family library; {len(assigned_components)} native ball-valve signatures lie within 5 native units of exactly one accepted edge and are assigned. All others remain explicitly unresolved. Bounded assignment (5 native units, approximately 2% of the source flange span; parallel pipes are hundreds of units apart) uses the native two-bulge circle center and the complete three-line/two-bulge signature; neither INSERT coordinates nor an unconstrained nearest edge is used.\n\nSupply/return layers: 空调冷冻水供水 / 空调冷冻水回水. Untyped branch layer: 空调立管、水平支管. Source lines: {len(segments)}; system-classified: {summary["system_classified_lines"]}. Classification propagates only within an untyped component that touches exactly one typed system.\n\nNo guessed physical equipment connections, unverified gap bridges or cross-drawing links. Unconfirmed source ends have explicit review-required virtual boundaries, not physical ports. Circle-centered main/radial-branch connections retain their exact source circle and pipe handles in circle-connection-bridges.json. Complete circle-V-double-bar glyphs with an actual typed pipe endpoint become explicit out-of-plane interfaces; plain circles and unsupported endpoints do not. Interior/interior crossings do not create nodes. Remaining unclassified circle/riser contacts are withheld. Equipment identity uses actual transformed block bounds and a unique label in a 600-native-unit expanded box. Modelspace INSERT coordinates are not used as equipment centers because block base coordinates differ. Capacity labels provide candidate schedule references only. Local overlay showed the untyped yellow branch layer includes triangular circle/riser symbol strokes; lines fully inside a 400-native-unit circle-centered neighborhood are withheld from physical connectivity, retaining their geometry as unresolved source evidence.\n\nRemaining work: resolve physical equipment ports, valve symbol gaps, riser circles and shared-color branch semantics; verify candidate T geometry by source overlay before accepting the whole graph. See source-fragments.json, pending-junctions.json and unresolved-components.json. Human Finish Review remains untouched.\n',encoding='utf-8')
 if tid in FLEX_POLICIES:
  policy=pathlib.Path(FLEX_POLICIES[tid]);policy=policy if policy.is_absolute() else args.flex_policy_map.parent/policy
  repaired=out.parent/'topology-expert-flex'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('repair_native_flexible_joints.py')),'--source',str(src),'--graph',str(out/'graph_with_edges.json'),'--devices',str(out/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(repaired)],check=True)
  dump(rep/'expert-flex-stage.json',{'status':'partial_unreviewed','source_sha256':readability['source_sha256'],'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'input_graph_sha256':hashlib.sha256((out/'graph_with_edges.json').read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((repaired/'graph_with_edges.json').read_bytes()).hexdigest(),'output':'../topology-expert-flex','hil_ready':False})
 if tid in WAVE_POLICIES:
  paths=WAVE_POLICIES[tid];policy=pathlib.Path(paths['policy']);issue=pathlib.Path(paths['issue']);policy=policy if policy.is_absolute() else args.wave_policy_map.parent/policy;issue=issue if issue.is_absolute() else args.wave_policy_map.parent/issue
  base=out.parent/'topology-expert-flex' if tid in FLEX_POLICIES else out;wave=out.parent/'topology-expert-wave'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('repair_expert_wave_scoped_09.py')),'--source',str(src),'--graph',str(base/'graph_with_edges.json'),'--devices',str(base/'assigned_edge_device_instances.csv'),'--issue',str(issue),'--policy',str(policy),'--output',str(wave)],check=True)
  dump(rep/'expert-wave-stage.json',{'status':'partial_unreviewed','source_sha256':readability['source_sha256'],'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'input_graph_sha256':hashlib.sha256((base/'graph_with_edges.json').read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((wave/'graph_with_edges.json').read_bytes()).hexdigest(),'output':'../topology-expert-wave','hil_ready':False})
 if tid in CIRCLE_PAIR_POLICIES:
  paths=CIRCLE_PAIR_POLICIES[tid];policy=pathlib.Path(paths['policy']);issue=pathlib.Path(paths['issue']);policy=policy if policy.is_absolute() else args.circle_pair_policy_map.parent/policy;issue=issue if issue.is_absolute() else args.circle_pair_policy_map.parent/issue
  base=out.parent/'topology-expert-wave' if tid in WAVE_POLICIES else out.parent/'topology-expert-flex' if tid in FLEX_POLICIES else out;circles=out.parent/'topology-expert-circle-pair'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('repair_expert_circle_pair_scoped_09.py')),'--source',str(src),'--graph',str(base/'graph_with_edges.json'),'--devices',str(base/'assigned_edge_device_instances.csv'),'--issue',str(issue),'--policy',str(policy),'--evidence-dir',str(out),'--output',str(circles)],check=True)
  dump(rep/'expert-circle-pair-stage.json',{'status':'partial_unreviewed_lower_inferred','source_sha256':readability['source_sha256'],'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'input_graph_sha256':hashlib.sha256((base/'graph_with_edges.json').read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((circles/'graph_with_edges.json').read_bytes()).hexdigest(),'output':'../topology-expert-circle-pair','hil_ready':False})
 if tid in DETAIL_POLICIES:
  paths=DETAIL_POLICIES[tid];policy=pathlib.Path(paths['policy']);issue=pathlib.Path(paths['issue']);policy=policy if policy.is_absolute() else args.detail_policy_map.parent/policy;issue=issue if issue.is_absolute() else args.detail_policy_map.parent/issue
  base=out.parent/'topology-expert-circle-pair' if tid in CIRCLE_PAIR_POLICIES else out.parent/'topology-expert-wave' if tid in WAVE_POLICIES else out.parent/'topology-expert-flex' if tid in FLEX_POLICIES else out;detail=out.parent/'topology-expert-detail-comparison'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('compare_expert_detail_scoped_09.py')),'--source',str(src),'--graph',str(base/'graph_with_edges.json'),'--devices',str(base/'assigned_edge_device_instances.csv'),'--issue',str(issue),'--policy',str(policy),'--output',str(detail)],check=True)
  dump(rep/'expert-detail-comparison-stage.json',{'status':'algorithm_pending','source_sha256':readability['source_sha256'],'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'input_graph_sha256':hashlib.sha256((base/'graph_with_edges.json').read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((detail/'graph_with_edges.json').read_bytes()).hexdigest(),'output':'../topology-expert-detail-comparison','hil_ready':False})
 if tid in BOUNDARY_POLICIES:
  paths=BOUNDARY_POLICIES[tid];policy=pathlib.Path(paths['policy']);issue=pathlib.Path(paths['issue']);policy=policy if policy.is_absolute() else args.boundary_policy_map.parent/policy;issue=issue if issue.is_absolute() else args.boundary_policy_map.parent/issue
  base=out.parent/'topology-expert-detail-comparison' if tid in DETAIL_POLICIES else out.parent/'topology-expert-circle-pair' if tid in CIRCLE_PAIR_POLICIES else out.parent/'topology-expert-wave' if tid in WAVE_POLICIES else out.parent/'topology-expert-flex' if tid in FLEX_POLICIES else out;boundary=out.parent/'topology-expert-boundaries'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('convert_expert_non_node_boundaries.py')),'--source',str(src),'--graph',str(base/'graph_with_edges.json'),'--devices',str(base/'assigned_edge_device_instances.csv'),'--issue',str(issue),'--policy',str(policy),'--output',str(boundary)],check=True)
  dump(rep/'expert-boundary-stage.json',{'status':'experimental_unreviewed','source_sha256':readability['source_sha256'],'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'input_graph_sha256':hashlib.sha256((base/'graph_with_edges.json').read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((boundary/'graph_with_typed_boundaries.json').read_bytes()).hexdigest(),'output':'../topology-expert-boundaries','hil_ready':False})
 if tid in SIMILAR_BOUNDARY_POLICIES:
  paths=SIMILAR_BOUNDARY_POLICIES[tid];policy=pathlib.Path(paths['policy']);issue=pathlib.Path(paths['issue']);policy=policy if policy.is_absolute() else args.similar_boundary_policy_map.parent/policy;issue=issue if issue.is_absolute() else args.similar_boundary_policy_map.parent/issue
  base=out.parent/'topology-expert-boundaries';similar=out.parent/'topology-expert-similar-boundaries'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('convert_expert_non_node_boundaries.py')),'--source',str(src),'--graph',str(base/'graph_with_typed_boundaries.json'),'--devices',str(base/'assigned_edge_device_instances.csv'),'--issue',str(issue),'--policy',str(policy),'--output',str(similar)],check=True)
  dump(rep/'expert-similar-boundary-stage.json',{'status':'inferred_unreviewed','source_sha256':readability['source_sha256'],'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'input_graph_sha256':hashlib.sha256((base/'graph_with_typed_boundaries.json').read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((similar/'graph_with_typed_boundaries.json').read_bytes()).hexdigest(),'output':'../topology-expert-similar-boundaries','hil_ready':False})
 if args.endpoint_semantics:
  stage='topology-expert-similar-boundaries' if tid in SIMILAR_BOUNDARY_POLICIES else 'topology-expert-boundaries' if tid in BOUNDARY_POLICIES else 'topology-expert-detail-comparison' if tid in DETAIL_POLICIES else 'topology-expert-circle-pair' if tid in CIRCLE_PAIR_POLICIES else 'topology-expert-wave' if tid in WAVE_POLICIES else 'topology-expert-flex' if tid in FLEX_POLICIES else 'topology'
  base=out.parent/stage; filename='graph_with_typed_boundaries.json' if tid in BOUNDARY_POLICIES else 'graph_with_edges.json'; source_graph=base/filename; dest=out.parent/'topology-endpoint-semantics'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('edge_endpoint_semantics.py')),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--output',str(dest)],check=True)
  dump(rep/'endpoint-semantics-stage.json',{'status':'partial_unreviewed','input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_endpoint_semantics.json').read_bytes()).hexdigest(),'output':'../topology-endpoint-semantics','hil_ready':False})
 if args.source_glyph_conflicts and any(x['source_system_conflict']=='exact_opposite_system_endpoint' for x in unbound_glyphs):
  base=out.parent/'topology-endpoint-semantics';dest=out.parent/'topology-source-glyph-conflicts';source_graph=base/'graph_with_endpoint_semantics.json'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('source_glyph_system_conflicts.py')),'--source',str(src),'--graph',str(source_graph),'--inventory',str(out/'unbound-complete-source-glyphs.json'),'--devices',str(base/'assigned_edge_device_instances.csv'),'--output',str(dest)],check=True)
  dump(rep/'source-glyph-conflicts-stage.json',{'status':'algorithm_pending','source_sha256':readability['source_sha256'],'input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_source_glyph_conflicts.json').read_bytes()).hexdigest(),'output':'../topology-source-glyph-conflicts','hil_ready':False})
 if args.source_main_continuity and pending:
  conflict=out.parent/'topology-source-glyph-conflicts';base=conflict if args.source_glyph_conflicts and conflict.exists() else out.parent/'topology-endpoint-semantics';filename='graph_with_source_glyph_conflicts.json' if base==conflict else 'graph_with_endpoint_semantics.json';source_graph=base/filename;dest=out.parent/'topology-source-main-continuity'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('source_pending_main_continuity.py')),'--source',str(src),'--graph',str(source_graph),'--pending',str(out/'pending-junctions.json'),'--devices',str(base/'assigned_edge_device_instances.csv'),'--output',str(dest)],check=True)
  dump(rep/'source-main-continuity-stage.json',{'status':'algorithm_pending','source_sha256':readability['source_sha256'],'input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_main_continuity.json').read_bytes()).hexdigest(),'output':'../topology-source-main-continuity','hil_ready':False})
 if tid in DIRECT_DN_POLICIES:
  candidates=[(out.parent/'topology-source-main-continuity','graph_with_main_continuity.json'),(out.parent/'topology-source-glyph-conflicts','graph_with_source_glyph_conflicts.json'),(out.parent/'topology-endpoint-semantics','graph_with_endpoint_semantics.json')]
  existing=[folder/name for folder,name in candidates if (folder/name).is_file()]
  if not existing:raise ValueError('direct DN stage requires a completed endpoint semantics graph')
  source_graph=existing[0];policy=pathlib.Path(DIRECT_DN_POLICIES[tid]);dest=rep/'source-direct-dn-candidates.json'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('source_direct_dn_evidence.py')),'--source',str(src),'--graph',str(source_graph),'--policy',str(policy),'--output',str(dest)],check=True)
  policy_data=json.loads(policy.read_text(encoding='utf8'));text_layers=policy_data.get('text_layers',[])
  if not isinstance(text_layers,list) or not text_layers or any(not isinstance(x,str) or not x for x in text_layers):raise ValueError('invalid direct DN text layers')
  risks=rep/'source-dn-annotation-risks.json';risk_cmd=[sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('source_dn_annotation_risks.py')),'--source',str(src),'--graph',str(source_graph),'--output',str(risks)]
  for layer in text_layers:risk_cmd.extend(['--text-layer',layer])
  subprocess.run(risk_cmd,check=True)
  dump(rep/'source-direct-dn-stage.json',{'status':'candidate_not_accepted','source_sha256':readability['source_sha256'],'input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'risk_report_sha256':hashlib.sha256(risks.read_bytes()).hexdigest(),'risk_report':'source-dn-annotation-risks.json','output':'source-direct-dn-candidates.json','hil_ready':False})
 if tid in IDENTITY_POLICIES:
  candidates=[(out.parent/'topology-source-main-continuity','graph_with_main_continuity.json'),(out.parent/'topology-source-glyph-conflicts','graph_with_source_glyph_conflicts.json'),(out.parent/'topology-endpoint-semantics','graph_with_endpoint_semantics.json')]
  existing=[folder/name for folder,name in candidates if (folder/name).is_file()]
  if not existing:raise ValueError('equipment identity stage requires a completed endpoint semantics graph')
  source_graph=existing[0];policy=pathlib.Path(IDENTITY_POLICIES[tid]);dest=out.parent/'topology-equipment-identity'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('recover_verified_equipment_identity.py')),'--source',str(src),'--graph',str(source_graph),'--bindings',str(out/'equipment-source-bindings.json'),'--policy',str(policy),'--output',str(dest)],check=True)
  shutil.copyfile(source_graph.parent/'assigned_edge_device_instances.csv',dest/'assigned_edge_device_instances.csv')
  # Equipment-only identity restoration changes the graph hash. Re-run the
  # selected source annotation checks against the new graph only if every old
  # edge and node is byte-for-byte semantically unchanged.
  if tid in DIRECT_DN_POLICIES:
   prior=json.loads(source_graph.read_text(encoding='utf8'));new_graph=dest/'graph_with_equipment_identity.json';updated=json.loads(new_graph.read_text(encoding='utf8'))
   prior_policy=pathlib.Path(DIRECT_DN_POLICIES[tid]);policy_bytes=prior_policy.read_bytes();old_hash=hashlib.sha256(source_graph.read_bytes()).hexdigest()
   dp=prepare_identity_dn_recheck(prior,updated,policy_bytes,readability['source_sha256'],old_hash,hashlib.sha256(new_graph.read_bytes()).hexdigest())
   new_policy=dest/'direct_dn_recheck_policy.json';new_policy.write_text(json.dumps(dp,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
   dn_output=dest/'source-direct-dn-candidates.json';risk_output=dest/'source-dn-annotation-risks.json'
   subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('source_direct_dn_evidence.py')),'--source',str(src),'--graph',str(new_graph),'--policy',str(new_policy),'--output',str(dn_output)],check=True)
   risk_cmd=[sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('source_dn_annotation_risks.py')),'--source',str(src),'--graph',str(new_graph),'--output',str(risk_output)]
   for layer in dp['text_layers']:risk_cmd.extend(['--text-layer',layer])
   subprocess.run(risk_cmd,check=True)
  dump(rep/'equipment-identity-stage.json',{'status':'source_equipment_recovered_ports_unresolved','source_sha256':readability['source_sha256'],'input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_equipment_identity.json').read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'hil_ready':False})
 if tid in CONFIRMED_INTERFACE_POLICIES:
  candidates=[(out.parent/'topology-equipment-identity','graph_with_equipment_identity.json'),(out.parent/'topology-source-main-continuity','graph_with_main_continuity.json'),(out.parent/'topology-source-glyph-conflicts','graph_with_source_glyph_conflicts.json'),(out.parent/'topology-endpoint-semantics','graph_with_endpoint_semantics.json')]
  existing=[folder/name for folder,name in candidates if (folder/name).is_file()]
  if not existing:raise ValueError('confirmed interfaces require a source-bound endpoint graph')
  source_graph=existing[0];base=source_graph.parent;dest=out.parent/'topology-confirmed-interfaces'
  selected=CONFIRMED_INTERFACE_POLICIES[tid];policy=pathlib.Path(selected['policy']);inv_policy=pathlib.Path(selected['inventory_policy'])
  if not policy.is_absolute():policy=args.confirmed_interface_policy_map.parent/policy
  if not inv_policy.is_absolute():inv_policy=args.confirmed_interface_policy_map.parent/inv_policy
  confirmed_cmd=[sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('confirmed_equipment_interfaces.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--inventory-policy',str(inv_policy),'--output',str(dest)]
  if tid in DIRECT_DN_POLICIES:confirmed_cmd.extend(['--direct-dn-policy',str(base/'direct_dn_recheck_policy.json')])
  subprocess.run(confirmed_cmd,check=True)
  dump(rep/'confirmed-interface-stage.json',{'status':'confirmed_interfaces_source_comparison_pending','source_sha256':readability['source_sha256'],'input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_confirmed_interfaces.json').read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'hil_ready':False})
 if tid in CONFIRMED_CIRCLE_POLICIES:
  base=out.parent/'topology-confirmed-interfaces';source_graph=base/'graph_with_confirmed_interfaces.json';dest=out.parent/'topology-confirmed-circle-junctions';selected=CONFIRMED_CIRCLE_POLICIES[tid]
  policy=pathlib.Path(selected['policy']);screen=pathlib.Path(selected['screen'])
  if not policy.is_absolute():policy=args.confirmed_circle_policy_map.parent/policy
  if not screen.is_absolute():screen=args.confirmed_circle_policy_map.parent/screen
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('repair_confirmed_circle_junctions.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--screen',str(screen),'--policy',str(policy),'--output',str(dest)],check=True)
  dump(rep/'confirmed-circle-junction-stage.json',{'status':'confirmed_source_comparison_pending','source_sha256':readability['source_sha256'],'input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_confirmed_circle_junctions.json').read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'hil_ready':False})
 if tid in CONFIRMED_OVERLAP_POLICIES:
  if tid in CONFIRMED_GAP_TEE_POLICIES or tid in LOCAL_DN_POLICIES or tid in DN_INHERITANCE_POLICIES or tid in SEGMENT_DIMENSION_POLICIES:
   raise ValueError('overlap repair with selected gap or hash-pinned DN/dimension stages requires explicit rebase')
  base=out.parent/'topology-confirmed-circle-junctions';source_graph=base/'graph_with_confirmed_circle_junctions.json';dest=out.parent/'topology-confirmed-overlapping-branches';selected=CONFIRMED_OVERLAP_POLICIES[tid]
  policy=pathlib.Path(selected['policy']);evidence=pathlib.Path(selected['evidence_manifest'])
  if not policy.is_absolute():policy=args.confirmed_overlap_branch_policy_map.parent/policy
  if not evidence.is_absolute():evidence=args.confirmed_overlap_branch_policy_map.parent/evidence
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('repair_confirmed_overlapping_branches.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--evidence-manifest',str(evidence),'--output',str(dest)],check=True)
  dump(rep/'confirmed-overlapping-branch-stage.json',{'status':'user_confirmed_source_comparison_pending','source_sha256':readability['source_sha256'],'input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_confirmed_overlapping_branches.json').read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'hil_ready':False})
 if tid in FOLLOWUP_OVERLAP_POLICIES:
  base=out.parent/'topology-confirmed-overlapping-branches';source_graph=base/'graph_with_confirmed_overlapping_branches.json'
  for index,selected in enumerate(FOLLOWUP_OVERLAP_POLICIES[tid],1):
   dest=out.parent/('topology-overlap-followup-%02d'%index);policy=pathlib.Path(selected['policy']);evidence=pathlib.Path(selected['evidence_manifest'])
   if not policy.is_absolute():policy=args.followup_overlap_policy_map.parent/policy
   if not evidence.is_absolute():evidence=args.followup_overlap_policy_map.parent/evidence
   subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('repair_confirmed_overlapping_branches.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--evidence-manifest',str(evidence),'--output',str(dest)],check=True)
   base=dest;source_graph=dest/'graph_with_confirmed_overlapping_branches.json'
  overlap_followup_graph=source_graph
  dump(rep/'followup-overlap-stage.json',{'status':'user_confirmed_source_comparison_pending','source_sha256':readability['source_sha256'],'output_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'count':len(FOLLOWUP_OVERLAP_POLICIES[tid]),'hil_ready':False})
 if tid in CONFIRMED_GAP_TEE_POLICIES:
  if tid in LOCAL_DN_POLICIES or tid in DN_INHERITANCE_POLICIES or tid in SEGMENT_DIMENSION_POLICIES:
   raise ValueError('gap-tee repair with hash-pinned DN or dimension stages requires explicit rebase')
  base=out.parent/'topology-confirmed-circle-junctions';source_graph=base/'graph_with_confirmed_circle_junctions.json';dest=out.parent/'topology-confirmed-gap-tee';selected=CONFIRMED_GAP_TEE_POLICIES[tid]
  policy=pathlib.Path(selected['policy']);evidence=pathlib.Path(selected['evidence'])
  if not policy.is_absolute():policy=args.confirmed_gap_tee_policy_map.parent/policy
  if not evidence.is_absolute():evidence=args.confirmed_gap_tee_policy_map.parent/evidence
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('repair_user_confirmed_gap_tee.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--evidence',str(evidence),'--output',str(dest)],check=True)
  dump(rep/'confirmed-gap-tee-stage.json',{'status':'user_confirmed_source_comparison_pending','source_sha256':readability['source_sha256'],'input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_confirmed_gap_tee.json').read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'hil_ready':False})
 if tid in SOURCE_REVIEW_CIRCLE_POLICIES:
  base=out.parent/'topology-confirmed-interfaces';source_graph=base/'graph_with_confirmed_interfaces.json';dest=out.parent/'topology-source-reviewed-circles';policy=pathlib.Path(SOURCE_REVIEW_CIRCLE_POLICIES[tid])
  if not policy.is_absolute():policy=args.source_reviewed_circle_policy_map.parent/policy
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('reconstruct_source_reviewed_circle_junctions.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  dump(rep/'source-reviewed-circle-stage.json',{'status':'technical_source_comparison_rebuilt_unreviewed','input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_source_reviewed_circles.json').read_bytes()).hexdigest(),'source_sha256':readability['source_sha256'],'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'hil_ready':False})
 if tid in LOCAL_DN_POLICIES:
  base=out.parent/('topology-source-reviewed-circles' if tid in SOURCE_REVIEW_CIRCLE_POLICIES else 'topology-confirmed-interfaces');source_graph=base/('graph_with_source_reviewed_circles.json' if tid in SOURCE_REVIEW_CIRCLE_POLICIES else 'graph_with_confirmed_interfaces.json');dest=out.parent/'topology-local-dn-observations';policy=pathlib.Path(LOCAL_DN_POLICIES[tid])
  if not policy.is_absolute():policy=args.local_dn_policy_map.parent/policy
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('attach_local_dn_observations.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  dump(rep/'local-dn-observation-stage.json',{'status':'local_observations_not_edgewide','source_sha256':readability['source_sha256'],'input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_local_dn_observations.json').read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'hil_ready':False})
 if tid in DN_INHERITANCE_POLICIES:
  base=out.parent/'topology-local-dn-observations';source_graph=base/'graph_with_local_dn_observations.json';dest=out.parent/'topology-dn-inheritance-candidates';policy=pathlib.Path(DN_INHERITANCE_POLICIES[tid])
  if not policy.is_absolute():policy=args.dn_inheritance_policy_map.parent/policy
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('infer_local_dn_candidates.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--direct-dn-policy',str(base/'direct_dn_recheck_policy.json'),'--output',str(dest)],check=True)
  dump(rep/'dn-inheritance-candidate-stage.json',{'status':'unaccepted_candidates','source_sha256':readability['source_sha256'],'input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_dn_inheritance_candidates.json').read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'hil_ready':False})
 if tid in SEGMENT_DIMENSION_POLICIES:
  base=out.parent/'topology-dn-inheritance-candidates';source_graph=base/'graph_with_dn_inheritance_candidates.json';dest=out.parent/'topology-source-segment-dimensions';policy=pathlib.Path(SEGMENT_DIMENSION_POLICIES[tid]);inheritance_policy=pathlib.Path(DN_INHERITANCE_POLICIES[tid])
  if not policy.is_absolute():policy=args.segment_dimension_policy_map.parent/policy
  if not inheritance_policy.is_absolute():inheritance_policy=args.dn_inheritance_policy_map.parent/inheritance_policy
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('attach_source_segment_dimensions.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--dn-inheritance-policy',str(inheritance_policy),'--direct-dn-policy',str(base/'direct_dn_recheck_policy.json'),'--output',str(dest)],check=True)
  dump(rep/'source-segment-dimension-stage.json',{'status':'source_segment_dimensions_pending_comparison','source_sha256':readability['source_sha256'],'input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_source_segment_dimensions.json').read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'hil_ready':False})
 if tid in PARTIAL_SOURCE_LENGTH_POLICIES:
  candidates=[(out.parent/'topology-confirmed-overlapping-branches','graph_with_confirmed_overlapping_branches.json'),(out.parent/'topology-confirmed-gap-tee','graph_with_confirmed_gap_tee.json'),(out.parent/'topology-confirmed-circle-junctions','graph_with_confirmed_circle_junctions.json'),(out.parent/'topology-source-segment-dimensions','graph_with_source_segment_dimensions.json'),(out.parent/'topology-dn-inheritance-candidates','graph_with_dn_inheritance_candidates.json'),(out.parent/'topology-local-dn-observations','graph_with_local_dn_observations.json'),(out.parent/'topology-source-reviewed-circles','graph_with_source_reviewed_circles.json'),(out.parent/'topology-confirmed-interfaces','graph_with_confirmed_interfaces.json'),(out.parent/'topology-equipment-identity','graph_with_equipment_identity.json'),(out.parent/'topology-source-main-continuity','graph_with_main_continuity.json'),(out.parent/'topology-source-glyph-conflicts','graph_with_source_glyph_conflicts.json'),(out.parent/'topology-endpoint-semantics','graph_with_endpoint_semantics.json')]
  if overlap_followup_graph:candidates.insert(0,(overlap_followup_graph.parent,overlap_followup_graph.name))
  existing=[folder/name for folder,name in candidates if (folder/name).is_file()]
  if not existing:raise ValueError('partial source length requires a source-bound endpoint graph')
  source_graph=existing[0];base=source_graph.parent;dest=out.parent/'topology-partial-source-length';selected=PARTIAL_SOURCE_LENGTH_POLICIES[tid]
  policy=pathlib.Path(selected['policy']);coverage=pathlib.Path(selected['coverage'])
  if not policy.is_absolute():policy=args.partial_source_length_policy_map.parent/policy
  if not coverage.is_absolute():coverage=args.partial_source_length_policy_map.parent/coverage
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('apply_partial_source_length_status.py')),'--source',str(src),'--graph',str(source_graph),'--coverage',str(coverage),'--policy',str(policy),'--output',str(dest)],check=True)
  shutil.copyfile(base/'assigned_edge_device_instances.csv',dest/'assigned_edge_device_instances.csv')
  dump(rep/'partial-source-length-stage.json',{'status':'partial_source_lengths_physical_unknown','source_sha256':readability['source_sha256'],'input_graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'output_graph_sha256':hashlib.sha256((dest/'graph_with_edges.json').read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'coverage_sha256':hashlib.sha256(coverage.read_bytes()).hexdigest(),'hil_ready':False})
 if tid in CIRCLE_CONFLICT_RECONCILIATION_POLICIES:
  base=out.parent/'topology-partial-source-length';source_graph=base/'graph_with_edges.json';dest=out.parent/'topology-circle-conflict-reconciled'
  if not source_graph.is_file():raise ValueError('conflict reconciliation requires the final partial-source-length stage; other stage orders need explicit integration')
  selected=CIRCLE_CONFLICT_RECONCILIATION_POLICIES[tid]
  command=[sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('reconcile_resolved_circle_crossovers.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--output',str(dest)]
  for key in ('policy','repair-policy','evidence-manifest'):
   value=pathlib.Path(selected[key])
   if not value.is_absolute():value=args.circle_conflict_reconciliation_policy_map.parent/value
   command.extend(['--'+key,str(value)])
  subprocess.run(command,check=True)
  shutil.copyfile(dest/'reconciliation-audit.json',rep/'circle-conflict-reconciliation-stage.json')
 if tid in FOLLOWUP_SOURCE_REVIEWED_POLICIES:
  base=out.parent/'topology-circle-conflict-reconciled';source_graph=base/'graph_with_edges.json';dest=out.parent/'topology-followup-source-reviewed-circles'
  if not source_graph.is_file():raise ValueError('followup source review requires the explicitly ordered conflict reconciliation stage')
  policy=pathlib.Path(FOLLOWUP_SOURCE_REVIEWED_POLICIES[tid])
  if not policy.is_absolute():policy=args.followup_source_reviewed_circle_policy_map.parent/policy
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('reconstruct_source_reviewed_circle_junctions.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'source-reviewed-circle-audit.json',rep/'followup-source-reviewed-circle-stage.json')
 calibrated_source_graph=None
 if tid in CALIBRATED_SOURCE_CIRCLE_POLICIES:
  base=out.parent/'topology-followup-source-reviewed-circles';source_graph=base/'graph_with_source_reviewed_circles.json'
  if not source_graph.is_file():raise ValueError('calibrated source review requires the ordered followup source review stage')
  paths=CALIBRATED_SOURCE_CIRCLE_POLICIES[tid]
  if isinstance(paths,str):paths=[paths]
  if not isinstance(paths,list) or not paths or any(not isinstance(p,str) or not p for p in paths):raise ValueError('invalid ordered calibrated circle policies')
  for index,value in enumerate(paths):
   suffix='' if index==0 else '-'+str(index+1).zfill(2)
   dest=out.parent/('topology-calibrated-source-circles'+suffix);policy=pathlib.Path(value)
   if not policy.is_absolute():policy=args.calibrated_source_circle_policy_map.parent/policy
   subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('reconstruct_source_reviewed_circle_junctions.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
   shutil.copyfile(dest/'source-reviewed-circle-audit.json',rep/('calibrated-source-circle-stage'+suffix+'.json'))
   base=dest;source_graph=dest/'graph_with_source_reviewed_circles.json'
  calibrated_source_graph=source_graph
 if tid in FOLLOWUP_CONFIRMED_CIRCLE_POLICIES:
  if calibrated_source_graph is None:raise ValueError('followup confirmed circles require the ordered calibrated circle stage')
  selected=FOLLOWUP_CONFIRMED_CIRCLE_POLICIES[tid]
  policy=pathlib.Path(selected['policy']);screen=pathlib.Path(selected['screen'])
  if not policy.is_absolute():policy=args.followup_confirmed_circle_policy_map.parent/policy
  if not screen.is_absolute():screen=args.followup_confirmed_circle_policy_map.parent/screen
  dest=out.parent/'topology-followup-confirmed-circles'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('repair_confirmed_circle_junctions.py')),'--source',str(src),'--graph',str(calibrated_source_graph),'--devices',str(calibrated_source_graph.parent/'assigned_edge_device_instances.csv'),'--screen',str(screen),'--policy',str(policy),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'confirmed-circle-junction-audit.json',rep/'followup-confirmed-circle-stage.json')
  calibrated_source_graph=dest/'graph_with_confirmed_circle_junctions.json'
 if tid in POST_CONFIRMED_SOURCE_CIRCLE_POLICIES:
  policy=pathlib.Path(POST_CONFIRMED_SOURCE_CIRCLE_POLICIES[tid])
  if not policy.is_absolute():policy=args.post_confirmed_source_circle_policy_map.parent/policy
  dest=out.parent/'topology-post-confirmed-source-circles'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('reconstruct_source_reviewed_circle_junctions.py')),'--source',str(src),'--graph',str(calibrated_source_graph),'--devices',str(calibrated_source_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'source-reviewed-circle-audit.json',rep/'post-confirmed-source-circle-stage.json')
  calibrated_source_graph=dest/'graph_with_source_reviewed_circles.json'
 if tid in EXPERT_DUPLICATE_CIRCLE_POLICIES:
  values={k:pathlib.Path(v) for k,v in EXPERT_DUPLICATE_CIRCLE_POLICIES[tid].items()}
  values={k:(v if v.is_absolute() else args.expert_duplicate_circle_policy_map.parent/v) for k,v in values.items()}
  prepared=out.parent/'expert-duplicate-circle-prepared';dest=out.parent/'topology-expert-duplicate-circles'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('prepare_expert_duplicate_circle_screen.py')),'--source',str(src),'--graph',str(calibrated_source_graph),'--screen',str(values['screen']),'--issue',str(values['issue']),'--policy',str(values['screen_policy']),'--output',str(prepared)],check=True)
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('repair_confirmed_circle_junctions.py')),'--source',str(src),'--graph',str(calibrated_source_graph),'--devices',str(calibrated_source_graph.parent/'assigned_edge_device_instances.csv'),'--screen',str(prepared/'expert-scoped-circle-screen.json'),'--policy',str(values['repair_policy']),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'confirmed-circle-junction-audit.json',rep/'expert-duplicate-circle-stage.json')
  calibrated_source_graph=dest/'graph_with_confirmed_circle_junctions.json'
 if tid in CALIBRATED_DUPLICATE_CIRCLE_POLICIES:
  values={k:pathlib.Path(v) for k,v in CALIBRATED_DUPLICATE_CIRCLE_POLICIES[tid].items()}
  values={k:(v if v.is_absolute() else args.calibrated_duplicate_circle_policy_map.parent/v) for k,v in values.items()}
  prepared=out.parent/'calibrated-duplicate-circle-screen.json';dest=out.parent/'topology-calibrated-duplicate-circles'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('calibrate_duplicate_circle_screen.py')),'--source',str(src),'--graph',str(calibrated_source_graph),'--screen',str(values['screen']),'--review',str(values['review']),'--policy',str(values['calibration_policy']),'--output',str(prepared)],check=True)
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('repair_confirmed_circle_junctions.py')),'--source',str(src),'--graph',str(calibrated_source_graph),'--devices',str(calibrated_source_graph.parent/'assigned_edge_device_instances.csv'),'--screen',str(prepared),'--policy',str(values['repair_policy']),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'confirmed-circle-junction-audit.json',rep/'calibrated-duplicate-circle-stage.json')
  calibrated_source_graph=dest/'graph_with_confirmed_circle_junctions.json'
 post_dimension_interface_graph=None
 if tid in POST_DIMENSION_INTERFACE_POLICIES:
  base=out.parent/'topology-source-segment-dimensions';source_graph=base/'graph_with_source_segment_dimensions.json'
  if not source_graph.is_file() or calibrated_source_graph is not None:raise ValueError('post-dimension interface stage requires unmodified dimension graph and explicit stage order')
  selected=POST_DIMENSION_INTERFACE_POLICIES[tid];policy=pathlib.Path(selected['policy']);inventory=pathlib.Path(selected['inventory_policy'])
  if not policy.is_absolute():policy=args.post_dimension_confirmed_interface_policy_map.parent/policy
  if not inventory.is_absolute():inventory=args.post_dimension_confirmed_interface_policy_map.parent/inventory
  dest=out.parent/'topology-post-dimension-confirmed-interfaces'
  command=[sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('confirmed_equipment_interfaces.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--inventory-policy',str(inventory),'--output',str(dest)]
  if (base/'direct_dn_recheck_policy.json').is_file():command.extend(['--direct-dn-policy',str(base/'direct_dn_recheck_policy.json')])
  subprocess.run(command,check=True)
  shutil.copyfile(dest/'confirmed-interface-audit.json',rep/'post-dimension-confirmed-interface-stage.json')
  post_dimension_interface_graph=dest/'graph_with_confirmed_interfaces.json'
 if tid in CONFIRMED_TERMINAL_BOUNDARY_POLICIES:
  if post_dimension_interface_graph is None:raise ValueError('terminal boundaries require post-dimension confirmed interfaces')
  selected=CONFIRMED_TERMINAL_BOUNDARY_POLICIES[tid];paths={k:pathlib.Path(v) for k,v in selected.items()}
  paths={k:(v if v.is_absolute() else args.confirmed_terminal_boundary_policy_map.parent/v) for k,v in paths.items()}
  dest=out.parent/'topology-confirmed-terminal-boundaries'
  command=[sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('convert_user_confirmed_terminal_boundaries.py')),'--source',str(src),'--graph',str(post_dimension_interface_graph),'--devices',str(post_dimension_interface_graph.parent/'assigned_edge_device_instances.csv')]
  for k,v in paths.items():command.extend(['--'+k,str(v)])
  command.extend(['--output',str(dest)]);subprocess.run(command,check=True)
  shutil.copyfile(dest/'boundary-stage.json',rep/'confirmed-terminal-boundary-stage.json')
  post_dimension_interface_graph=dest/'graph_with_typed_boundaries.json'
 if tid in PENDING_MAIN_RECONCILIATION_POLICIES:
  if post_dimension_interface_graph is None:raise ValueError('pending main reconciliation requires current graph')
  policy=pathlib.Path(PENDING_MAIN_RECONCILIATION_POLICIES[tid])
  if not policy.is_absolute():policy=args.pending_main_reconciliation_policy_map.parent/policy
  dest=out.parent/'topology-reconciled-pending-main'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('reconcile_pending_main_continuity.py')),'--source',str(src),'--graph',str(post_dimension_interface_graph),'--pending',str(out/'pending-junctions.json'),'--devices',str(post_dimension_interface_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'main-continuity-reconciliation-audit.json',rep/'main-continuity-reconciliation-stage.json')
  post_dimension_interface_graph=dest/'graph_with_main_continuity.json'
 if tid in LATE_FLEX_POLICIES:
  if post_dimension_interface_graph is not None or calibrated_source_graph is not None:raise ValueError('late flexible joint repair requires explicit stage ordering for this graph')
  base=out.parent/'topology-endpoint-semantics';source_graph=base/'graph_with_endpoint_semantics.json'
  if not source_graph.is_file():raise ValueError('late flexible joint repair requires endpoint graph')
  policy=pathlib.Path(LATE_FLEX_POLICIES[tid])
  if not policy.is_absolute():policy=args.late_flex_policy_map.parent/policy
  dest=out.parent/'topology-late-flexible-joints';sem=out.parent/'topology-late-flex-endpoint-semantics'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('repair_native_flexible_joints.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(base/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('edge_endpoint_semantics.py')),'--graph',str(dest/'graph_with_edges.json'),'--devices',str(dest/'assigned_edge_device_instances.csv'),'--output',str(sem)],check=True)
  shutil.copyfile(dest/'repair-audit.json',rep/'late-flexible-joint-stage.json')
  post_dimension_interface_graph=sem/'graph_with_endpoint_semantics.json'
 if tid in CALIBRATED_WAVE_POLICIES:
  if post_dimension_interface_graph is None:raise ValueError('calibrated wave repair requires current graph')
  policy=pathlib.Path(CALIBRATED_WAVE_POLICIES[tid])
  if not policy.is_absolute():policy=args.calibrated_wave_policy_map.parent/policy
  dest=out.parent/'topology-calibrated-wave-omissions'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('repair_calibrated_wave_omissions.py')),'--source',str(src),'--graph',str(post_dimension_interface_graph),'--devices',str(post_dimension_interface_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'repair-audit.json',rep/'calibrated-wave-omission-stage.json')
  post_dimension_interface_graph=dest/'graph_with_edges.json'
 if tid in UNPAIRED_WAVE_POLICIES:
  if post_dimension_interface_graph is None:raise ValueError('unpaired wave evidence requires current graph')
  policy=pathlib.Path(UNPAIRED_WAVE_POLICIES[tid])
  if not policy.is_absolute():policy=args.unpaired_wave_evidence_policy_map.parent/policy
  dest=out.parent/'topology-unpaired-wave-evidence'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('attach_unpaired_wave_evidence.py')),'--source',str(src),'--graph',str(post_dimension_interface_graph),'--devices',str(post_dimension_interface_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'audit.json',rep/'unpaired-wave-evidence-stage.json')
  post_dimension_interface_graph=dest/'graph_with_wave_evidence.json'
 if tid in WAVE_CONVENTION_CONFIRMATIONS:
  if post_dimension_interface_graph is None:raise ValueError('wave convention confirmation requires current graph')
  spec=WAVE_CONVENTION_CONFIRMATIONS[tid];paths={k:pathlib.Path(v) for k,v in spec.items()}
  paths={k:(v if v.is_absolute() else args.wave_convention_confirmation_map.parent/v) for k,v in paths.items()}
  dest=out.parent/'topology-expert-wave-convention'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('confirm_wave_drawing_convention.py')),'--graph',str(post_dimension_interface_graph),'--devices',str(post_dimension_interface_graph.parent/'assigned_edge_device_instances.csv'),'--confirmation',str(paths['confirmation']),'--image',str(paths['image']),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'audit.json',rep/'expert-wave-convention-stage.json')
  post_dimension_interface_graph=dest/'graph_with_wave_convention.json'
 if tid in FINAL_SOURCE_SEGMENT_DIMENSION_POLICIES:
  if post_dimension_interface_graph is None:raise ValueError('final segment dimension attachment requires an explicit final graph stage')
  policy=pathlib.Path(FINAL_SOURCE_SEGMENT_DIMENSION_POLICIES[tid]);policy=policy if policy.is_absolute() else args.final_source_segment_dimension_policy_map.parent/policy
  dest=out.parent/'topology-final-source-segment-dimensions'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('attach_final_source_segment_dimensions.py')),'--source',str(src),'--graph',str(post_dimension_interface_graph),'--devices',str(post_dimension_interface_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'audit.json',rep/'final-source-segment-dimension-attachment.json')
  post_dimension_interface_graph=dest/'graph_with_source_segment_dimensions.json'
 if tid in FINAL_CROSSOVER_POLICIES:
  source_graph=post_dimension_interface_graph or calibrated_source_graph
  if source_graph is None or not source_graph.is_file():raise ValueError('crossover correction requires explicit final topology graph')
  policy=pathlib.Path(FINAL_CROSSOVER_POLICIES[tid]);policy=policy if policy.is_absolute() else args.final_crossover_length_policy_map.parent/policy
  dest=out.parent/'topology-crossover-length-status'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('correct_plan_crossover_lengths.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(source_graph.parent/'assigned_edge_device_instances.csv'),'--gaps',str(out/'source_gap_coverage.json'),'--fragments',str(out/'source-fragments.json'),'--policy',str(policy),'--output',str(dest)],check=True)
  if post_dimension_interface_graph is not None:post_dimension_interface_graph=dest/'graph_with_crossover_length_status.json'
  else:calibrated_source_graph=dest/'graph_with_crossover_length_status.json'
 if tid in FINAL_UNIDENTIFIED_EQUIPMENT_POLICIES:
  source_graph=post_dimension_interface_graph or calibrated_source_graph
  if source_graph is None or not source_graph.is_file():raise ValueError('equipment preservation requires explicit final topology graph')
  policy=pathlib.Path(FINAL_UNIDENTIFIED_EQUIPMENT_POLICIES[tid]);policy=policy if policy.is_absolute() else args.final_unidentified_equipment_policy_map.parent/policy
  dest=out.parent/'topology-pending-source-equipment'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('preserve_unidentified_equipment.py')),'--source',str(src),'--graph',str(source_graph),'--bindings',str(out/'equipment-source-bindings.json'),'--devices',str(source_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'audit.json',rep/'pending-source-equipment-preservation.json')
  if post_dimension_interface_graph is not None:post_dimension_interface_graph=dest/'graph_with_pending_equipment.json'
  else:calibrated_source_graph=dest/'graph_with_pending_equipment.json'
 if tid in FINAL_LOCAL_DN_POLICIES:
  source_graph=post_dimension_interface_graph or calibrated_source_graph
  if source_graph is None or not source_graph.is_file():raise ValueError('final local DN observations require explicit final topology graph')
  policy=pathlib.Path(FINAL_LOCAL_DN_POLICIES[tid]);policy=policy if policy.is_absolute() else args.final_local_dn_policy_map.parent/policy
  dest=out.parent/'topology-final-local-dn-observations'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('attach_local_dn_observations.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(source_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'local-dn-observation-audit.json',rep/'final-local-dn-observation-audit.json')
  if post_dimension_interface_graph is not None:post_dimension_interface_graph=dest/'graph_with_local_dn_observations.json'
  else:calibrated_source_graph=dest/'graph_with_local_dn_observations.json'
 if tid in FINAL_NEAR_TEE_STATE_POLICIES:
  source_graph=post_dimension_interface_graph or calibrated_source_graph
  if source_graph is None or not source_graph.is_file():raise ValueError('near-tee state requires current graph')
  policy=pathlib.Path(FINAL_NEAR_TEE_STATE_POLICIES[tid]);policy=policy if policy.is_absolute() else args.final_near_tee_state_policy_map.parent/policy
  dest=out.parent/'topology-pending-near-tee-state'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('attach_applied_near_tee_state.py')),'--source',str(src),'--graph',str(source_graph),'--normalization',str(out/'normalization_audit.json'),'--devices',str(source_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'near-tee-state-audit.json',rep/'pending-near-tee-state-audit.json')
  if post_dimension_interface_graph is not None:post_dimension_interface_graph=dest/'graph_with_pending_near_tees.json'
  else:calibrated_source_graph=dest/'graph_with_pending_near_tees.json'
 if tid in FINAL_EQUIPMENT_PAIR_CANDIDATES:
  source_graph=post_dimension_interface_graph or calibrated_source_graph
  if source_graph is None or not source_graph.is_file():raise ValueError('paired equipment candidates require current graph')
  spec=FINAL_EQUIPMENT_PAIR_CANDIDATES[tid];paths={k:pathlib.Path(v) for k,v in spec.items()};paths={k:(v if v.is_absolute() else args.final_equipment_pair_candidates_map.parent/v) for k,v in paths.items()}
  if set(paths)!={'axis_source','axis_graph','axis_receipt','policy'}:raise ValueError('invalid paired equipment candidate inputs')
  dest=out.parent/'topology-equipment-pair-candidates'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('attach_equipment_pair_label_candidates.py')),'--plan-source',str(src),'--axis-source',str(paths['axis_source']),'--plan-graph',str(source_graph),'--axis-graph',str(paths['axis_graph']),'--axis-receipt',str(paths['axis_receipt']),'--devices',str(source_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(paths['policy']),'--output',str(dest)],check=True)
  shutil.copyfile(dest/'pair-candidate-audit.json',rep/'equipment-pair-candidate-audit.json')
  if post_dimension_interface_graph is not None:post_dimension_interface_graph=dest/'graph_with_equipment_pair_candidates.json'
  else:calibrated_source_graph=dest/'graph_with_equipment_pair_candidates.json'
 if tid in BATCH_CONFIRMED_CIRCLES:
  source_graph=post_dimension_interface_graph or calibrated_source_graph
  if source_graph is None or not source_graph.is_file():raise ValueError('batch confirmed circles require current graph')
  policy=pathlib.Path(BATCH_CONFIRMED_CIRCLES[tid]);policy=policy if policy.is_absolute() else args.batch_confirmed_circle_policy_map.parent/policy
  dest=out.parent/'topology-batch-confirmed-circles'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('reconstruct_batch_circle_junctions.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(source_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  from reconstruct_batch_circle_junctions import verify_output as verify_batch_circles
  audit=verify_batch_circles(dest)
  shutil.copyfile(dest/'batch-confirmed-circle-audit.json',rep/'batch-confirmed-circle-audit.json')
  dump(rep/'batch-confirmed-circle-stage.json',{'status':'source_pinned_batch_circle_reconstruction','source_sha256':readability['source_sha256'],'graph_sha256':audit['output_graph_sha256'],'artifact_directory':str(dest.resolve()),'audit_sha256':hashlib.sha256((dest/'batch-confirmed-circle-audit.json').read_bytes()).hexdigest(),'hil_ready':False})
  if post_dimension_interface_graph is not None:post_dimension_interface_graph=dest/'graph_with_batch_confirmed_circles.json'
  else:calibrated_source_graph=dest/'graph_with_batch_confirmed_circles.json'
 if tid in CONFIRMED_SIDEVIEWS:
  if tid not in FINAL_DIMENSION_SCREEN_POLICIES:raise ValueError('confirmed side-view replacement requires final graph source screens')
  source_graph=post_dimension_interface_graph or calibrated_source_graph
  if source_graph is None or not source_graph.is_file():raise ValueError('confirmed side-views require current graph')
  paths={k:pathlib.Path(v) for k,v in CONFIRMED_SIDEVIEWS[tid].items()}
  paths={k:(p if p.is_absolute() else args.confirmed_sideview_policy_map.parent/p) for k,p in paths.items()}
  dest=out.parent/'topology-confirmed-sideviews'
  command=[sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('canonicalize_confirmed_sideviews.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(source_graph.parent/'assigned_edge_device_instances.csv'),'--output',str(dest)]
  for name,path in paths.items():command.extend(['--'+name,str(path)])
  subprocess.run(command,check=True)
  from canonicalize_confirmed_sideviews import verify_output as verify_sideviews
  audit=verify_sideviews(dest)
  shutil.copyfile(dest/'sideview-canonicalization-audit.json',rep/'sideview-canonicalization-audit.json')
  dump(rep/'confirmed-sideview-stage.json',{'status':'source_pinned_confirmed_sideview_canonicalization','source_sha256':readability['source_sha256'],'graph_sha256':audit['output_graph_sha256'],'artifact_directory':str(dest.resolve()),'audit_sha256':hashlib.sha256((dest/'sideview-canonicalization-audit.json').read_bytes()).hexdigest(),'hil_ready':False})
  if post_dimension_interface_graph is not None:post_dimension_interface_graph=dest/'graph_with_canonical_sideviews.json'
  else:calibrated_source_graph=dest/'graph_with_canonical_sideviews.json'
 if tid in CONFIRMED_EQUIPMENT_PAIRS:
  if tid not in FINAL_DIMENSION_SCREEN_POLICIES:raise ValueError('equipment pair reconstruction requires final source screens')
  source_graph=post_dimension_interface_graph or calibrated_source_graph
  if source_graph is None or not source_graph.is_file():raise ValueError('equipment pair reconstruction requires current graph')
  paths={k:pathlib.Path(v) for k,v in CONFIRMED_EQUIPMENT_PAIRS[tid].items()}
  paths={k:(p if p.is_absolute() else args.confirmed_equipment_pairs_policy_map.parent/p) for k,p in paths.items()}
  dest=out.parent/'topology-confirmed-equipment-pairs'
  cmd=[sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('reconstruct_confirmed_equipment_pairs.py')),'--source',str(src),'--graph',str(source_graph),'--devices',str(source_graph.parent/'assigned_edge_device_instances.csv'),'--output',str(dest)]
  for name,path in paths.items():cmd+=['--'+name.replace('_','-'),str(path)]
  subprocess.run(cmd,check=True)
  from reconstruct_confirmed_equipment_pairs import verify_output as verify_equipment_pairs
  audit=verify_equipment_pairs(dest)
  shutil.copyfile(dest/'equipment-pair-reconstruction-audit.json',rep/'equipment-pair-reconstruction-audit.json')
  dump(rep/'confirmed-equipment-pair-stage.json',{'status':'source_pinned_confirmed_equipment_pair_reconstruction','source_sha256':readability['source_sha256'],'graph_sha256':audit['output_graph_sha256'],'artifact_directory':str(dest.resolve()),'audit_sha256':hashlib.sha256((dest/'equipment-pair-reconstruction-audit.json').read_bytes()).hexdigest(),'hil_ready':False})
  if post_dimension_interface_graph is not None:post_dimension_interface_graph=dest/'graph_with_edges.json'
  else:calibrated_source_graph=dest/'graph_with_edges.json'
 if tid in CONFIRMED_NEAR_TEES:
  if tid not in FINAL_DIMENSION_SCREEN_POLICIES:raise ValueError('near-tee confirmation requires final source screens')
  source_graph=post_dimension_interface_graph or calibrated_source_graph
  if source_graph is None or not source_graph.is_file():raise ValueError('near-tee confirmation requires current graph')
  policy=pathlib.Path(CONFIRMED_NEAR_TEES[tid]);policy=policy if policy.is_absolute() else args.confirmed_near_tee_policy_map.parent/policy
  dest=out.parent/'topology-confirmed-near-tees'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('confirm_normalized_near_tees.py')),'--source',str(src),'--graph',str(source_graph),'--normalization',str(out/'normalization_audit.json'),'--devices',str(source_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  from confirm_normalized_near_tees import verify_output as verify_near_tees
  verify_near_tees(dest)
  audit=json.loads((dest/'near-tee-confirmation-audit.json').read_text(encoding='utf8'))
  shutil.copyfile(dest/'near-tee-confirmation-audit.json',rep/'near-tee-confirmation-audit.json')
  dump(rep/'confirmed-near-tee-stage.json',{'status':'source_pinned_normalized_near_tee_confirmation','source_sha256':readability['source_sha256'],'graph_sha256':audit['output_graph_sha256'],'artifact_directory':str(dest.resolve()),'audit_sha256':hashlib.sha256((dest/'near-tee-confirmation-audit.json').read_bytes()).hexdigest(),'hil_ready':False})
  if post_dimension_interface_graph is not None:post_dimension_interface_graph=dest/'graph_with_confirmed_near_tees.json'
  else:calibrated_source_graph=dest/'graph_with_confirmed_near_tees.json'
 if any(x.get('status')=='applied' for x in near_audit):
  from normalized_near_tee_state_gate import check as check_near_tee_state
  source_graph=post_dimension_interface_graph or calibrated_source_graph or out/'graph_with_edges.json'
  near_state=check_near_tee_state(json.loads(source_graph.read_text(encoding='utf8')),near_audit,readability['source_sha256'],confirmed_directory=source_graph.parent if tid in CONFIRMED_NEAR_TEES else None)
  near_state.update(graph_sha256=hashlib.sha256(source_graph.read_bytes()).hexdigest(),normalization_sha256=hashlib.sha256((out/'normalization_audit.json').read_bytes()).hexdigest())
  dump(rep/'normalized-near-tee-state-gate.json',near_state)
 if tid in FINAL_DN_RECHECK_POLICIES:
  if post_dimension_interface_graph is None:raise ValueError('final DN recheck requires current graph')
  spec=FINAL_DN_RECHECK_POLICIES[tid];paths={k:pathlib.Path(v) for k,v in spec.items()}
  paths={k:(v if v.is_absolute() else args.final_dn_recheck_policy_map.parent/v) for k,v in paths.items()}
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('recheck_dn_inheritance.py')),'--source',str(src),'--graph',str(post_dimension_interface_graph),'--policy',str(paths['policy']),'--direct-policy',str(paths['direct_policy']),'--output',str(rep/'final-dn-inheritance-recheck.json')],check=True)
 if tid in FINAL_DIMENSION_RECHECK_POLICIES:
  if post_dimension_interface_graph is None:raise ValueError('final dimension recheck requires current graph')
  policy=pathlib.Path(FINAL_DIMENSION_RECHECK_POLICIES[tid])
  if not policy.is_absolute():policy=args.final_dimension_recheck_policy_map.parent/policy
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('recheck_source_segment_dimensions.py')),'--source',str(src),'--graph',str(post_dimension_interface_graph),'--policy',str(policy),'--output',str(rep/'final-source-segment-dimension-recheck.json')],check=True)
 if tid in FINAL_DIMENSION_SCREEN_POLICIES:
  choices=[post_dimension_interface_graph,calibrated_source_graph]
  if tid in FOLLOWUP_SOURCE_REVIEWED_POLICIES:choices.append(out.parent/'topology-followup-source-reviewed-circles'/'graph_with_source_reviewed_circles.json')
  if tid in CIRCLE_CONFLICT_RECONCILIATION_POLICIES:choices.append(out.parent/'topology-circle-conflict-reconciled'/'graph_with_edges.json')
  choices.append(overlap_followup_graph)
  if tid in SOURCE_REVIEW_CIRCLE_POLICIES:choices.append(out.parent/'topology-source-reviewed-circles'/'graph_with_source_reviewed_circles.json')
  choices += [out.parent/folder/name for folder,name in [('topology-partial-source-length','graph_with_edges.json'),('topology-confirmed-overlapping-branches','graph_with_confirmed_overlapping_branches.json'),('topology-confirmed-gap-tee','graph_with_confirmed_gap_tee.json'),('topology-confirmed-circle-junctions','graph_with_confirmed_circle_junctions.json'),('topology-source-segment-dimensions','graph_with_source_segment_dimensions.json'),('topology-dn-inheritance-candidates','graph_with_dn_inheritance_candidates.json'),('topology-local-dn-observations','graph_with_local_dn_observations.json'),('topology-confirmed-interfaces','graph_with_confirmed_interfaces.json'),('topology-equipment-identity','graph_with_equipment_identity.json'),('topology-source-main-continuity','graph_with_main_continuity.json'),('topology-source-glyph-conflicts','graph_with_source_glyph_conflicts.json'),('topology-endpoint-semantics','graph_with_endpoint_semantics.json'),('topology-expert-detail-comparison','graph_with_edges.json'),('topology','graph_with_edges.json')]]
  screen_graph=next((v for v in choices if v is not None and v.is_file()),None)
  if screen_graph is None:raise ValueError('dimension screen requires current graph')
  policy=pathlib.Path(FINAL_DIMENSION_SCREEN_POLICIES[tid]);policy=policy if policy.is_absolute() else args.final_dimension_screen_policy_map.parent/policy
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('native_dimension_segment_screen.py')),'--source',str(src),'--graph',str(screen_graph),'--policy',str(policy),'--output',str(rep/'final-native-dimension-segment-screen.json')],check=True)
  if tid in FINAL_PLAN_LINE_POLICIES:
   line_policy=pathlib.Path(FINAL_PLAN_LINE_POLICIES[tid]);line_policy=line_policy if line_policy.is_absolute() else args.final_plan_line_policy_map.parent/line_policy
   line_dest=rep/'final-plan-line-inventory.json';subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('final_plan_line_coverage.py')),'--source',str(src),'--graph',str(screen_graph),'--policy',str(line_policy),'--output',str(line_dest)],check=True)
   coincident_dest=rep/'final-coincident-source-segments.json';subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('coincident_plan_source_segments.py')),'--source',str(src),'--graph',str(screen_graph),'--inventory',str(line_dest),'--output',str(coincident_dest)],check=True)
   families_dest=rep/'final-micro-line-families.json';subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('group_micro_line_circle_context.py')),'--source',str(src),'--graph',str(screen_graph),'--inventory',str(line_dest),'--output',str(families_dest)],check=True)
   line_report=json.loads(line_dest.read_text(encoding='utf8'));dump(rep/'final-plan-line-stage.json',{'status':'final_plan_line_handle_inventory_not_acceptance','source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(screen_graph.read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256(line_dest.read_bytes()).hexdigest(),'coincident_evidence_sha256':hashlib.sha256(coincident_dest.read_bytes()).hexdigest(),'micro_family_evidence_sha256':hashlib.sha256(families_dest.read_bytes()).hexdigest(),'candidate_count':sum(x['status']!='source_handle_referenced' for x in line_report['records']),'hil_ready':False})
   dump(rep.parent/'plan-line-required.json',{'status':'required_plan_line_screen','source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(screen_graph.read_bytes()).hexdigest(),'policy_map_sha256':hashlib.sha256(args.final_plan_line_policy_map.read_bytes()).hexdigest(),'evidence_path':'reports/final-plan-line-inventory.json','stage_path':'reports/final-plan-line-stage.json','coincident_path':'reports/final-coincident-source-segments.json','hil_ready':False})
  if tid in FINAL_COMPOUND_DN_POLICIES:
   spec=FINAL_COMPOUND_DN_POLICIES[tid]
   if spec['source_sha256']!=readability['source_sha256'] or spec['graph_sha256']!=hashlib.sha256(screen_graph.read_bytes()).hexdigest():raise ValueError('stale final compound DN source or graph')
   compound_dest=rep/'final-compound-dn-evidence.json';cmd=[sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('source_compound_dn_evidence.py')),'--source',str(src),'--graph',str(screen_graph),'--output',str(compound_dest)]
   for layer in spec['text_layers']:cmd.extend(['--text-layer',layer])
   subprocess.run(cmd,check=True)
   compound=json.loads(compound_dest.read_text(encoding='utf8'));dump(rep/'final-compound-dn-stage.json',{'status':'compound_dn_text_evidence_not_binding','source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(screen_graph.read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256(compound_dest.read_bytes()).hexdigest(),'candidate_count':len(compound['records']),'hil_ready':False})
   dump(rep.parent/'compound-dn-required.json',{'status':'required_compound_dn_screen','source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(screen_graph.read_bytes()).hexdigest(),'policy_map_sha256':hashlib.sha256(args.final_compound_dn_policy_map.read_bytes()).hexdigest(),'evidence_path':'reports/final-compound-dn-evidence.json','stage_path':'reports/final-compound-dn-stage.json','hil_ready':False})
  from final_graph_integrity import audit as audit_final_graph
  final_integrity=audit_final_graph(screen_graph,screen_graph.parent/'assigned_edge_device_instances.csv',src)
  dump(rep/'final-graph-structural-audit.json',final_integrity)
  if not all(final_integrity['checks'].values()):raise ValueError('final graph structural audit failed; inspect report')
  if tid in FINAL_ID_AUDITS:
   from audit_graph_id_reuse import audit_bound
   spec=FINAL_ID_AUDITS[tid];previous=pathlib.Path(spec['previous_graph']);previous=previous if previous.is_absolute() else args.final_id_audit_map.parent/previous
   id_audit=audit_bound(previous,screen_graph,readability['source_sha256'],spec)
   dump(rep/'final-id-reuse-audit.json',id_audit)
  if tid in FINAL_EXPERT_NODE_POLICIES:
   spec=FINAL_EXPERT_NODE_POLICIES[tid];paths={k:pathlib.Path(v) for k,v in spec.items()};paths={k:(v if v.is_absolute() else args.final_expert_node_reconciliation_map.parent/v) for k,v in paths.items()}
   subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('expert_node_reconciliation.py')),'--source',str(src),'--graph',str(screen_graph),'--issue',str(paths['issue']),'--context',str(paths['context']),'--policy',str(paths['policy']),'--output',str(rep/'final-expert-node-reconciliation.json')],check=True)

  if tid in FINAL_COMPONENT_POLICIES:
   spec=FINAL_COMPONENT_POLICIES[tid];component_policy=pathlib.Path(spec['policy']);component_policy=component_policy if component_policy.is_absolute() else args.final_component_conservation_policy_map.parent/component_policy
   flex_stage=spec['repair_stage']
   if flex_stage=='topology-expert-flex' and tid not in FLEX_POLICIES or flex_stage=='topology-late-flexible-joints' and tid not in LATE_FLEX_POLICIES:raise ValueError('component audit repair stage was not enabled for task')
   subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('component_conservation_audit.py')),'--source',str(src),'--graph',str(screen_graph),'--initial',str(out/'assigned_edge_device_instances.csv'),'--final',str(screen_graph.parent/'assigned_edge_device_instances.csv'),'--repair',str(out.parent/flex_stage/'repair-audit.json'),'--policy',str(component_policy),'--output',str(rep/'final-component-conservation.json')],check=True)

  if tid in FINAL_NAMED_LEADER_POLICIES:
   named_policy=pathlib.Path(FINAL_NAMED_LEADER_POLICIES[tid]);named_policy=named_policy if named_policy.is_absolute() else args.final_named_leader_policy_map.parent/named_policy
   named_dest=rep/'named-endpoint-leader-screen.json'
   subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('screen_named_endpoint_leaders.py')),'--source',str(src),'--graph',str(screen_graph),'--policy',str(named_policy),'--output',str(named_dest)],check=True)
   named_result=json.loads(named_dest.read_text(encoding='utf8'))
   dump(rep/'named-endpoint-leader-screen-stage.json',{'status':'candidate_screen_not_acceptance','source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(screen_graph.read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256(named_dest.read_bytes()).hexdigest(),'candidate_count':len(named_result['selections']),'hil_ready':False})
  if tid in FINAL_NEAR_ENDPOINT_POLICIES:
   near_policy=pathlib.Path(FINAL_NEAR_ENDPOINT_POLICIES[tid]);near_policy=near_policy if near_policy.is_absolute() else args.final_near_endpoint_policy_map.parent/near_policy
   near_dest=rep/'near-endpoint-crossing-screen.json'
   subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('near_endpoint_crossing_screen.py')),'--source',str(src),'--graph',str(screen_graph),'--policy',str(near_policy),'--output',str(near_dest)],check=True)
   near_result=json.loads(near_dest.read_text(encoding='utf8'))
   dump(rep/'near-endpoint-crossing-screen-stage.json',{'status':'candidate_screen_not_acceptance','source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(screen_graph.read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256(near_dest.read_bytes()).hexdigest(),'candidate_count':near_result['counts']['candidates'],'hil_ready':False})
 if args.endpoint_semantics:
  from reconcile_pending_main_continuity import validate_references
  candidates=[out.parent/folder/name for folder,name in [('topology-partial-source-length','graph_with_edges.json'),('topology-confirmed-overlapping-branches','graph_with_confirmed_overlapping_branches.json'),('topology-confirmed-gap-tee','graph_with_confirmed_gap_tee.json'),('topology-confirmed-circle-junctions','graph_with_confirmed_circle_junctions.json'),('topology-source-segment-dimensions','graph_with_source_segment_dimensions.json'),('topology-dn-inheritance-candidates','graph_with_dn_inheritance_candidates.json'),('topology-local-dn-observations','graph_with_local_dn_observations.json'),('topology-source-reviewed-circles','graph_with_source_reviewed_circles.json'),('topology-confirmed-interfaces','graph_with_confirmed_interfaces.json'),('topology-equipment-identity','graph_with_equipment_identity.json'),('topology-source-main-continuity','graph_with_main_continuity.json'),('topology-source-glyph-conflicts','graph_with_source_glyph_conflicts.json'),('topology-endpoint-semantics','graph_with_endpoint_semantics.json')]]
  if overlap_followup_graph:candidates.insert(1,overlap_followup_graph)
  if tid in CIRCLE_CONFLICT_RECONCILIATION_POLICIES:candidates.insert(0,out.parent/'topology-circle-conflict-reconciled'/'graph_with_edges.json')
  if tid in FOLLOWUP_SOURCE_REVIEWED_POLICIES:candidates.insert(0,out.parent/'topology-followup-source-reviewed-circles'/'graph_with_source_reviewed_circles.json')
  if calibrated_source_graph:candidates.insert(0,calibrated_source_graph)
  if post_dimension_interface_graph:candidates.insert(0,post_dimension_interface_graph)
  current=next((x for x in candidates if x is not None and x.is_file()),None)
  if current is None:raise ValueError('pending-main reference gate requires current graph')
  checked=validate_references(json.loads(current.read_text(encoding='utf8')))
  dump(rep/'pending-main-reference-gate.json',{'status':'references_current_not_branch_acceptance','graph_sha256':hashlib.sha256(current.read_bytes()).hexdigest(),'checked_nodes':checked,'hil_ready':False})
 if tid in HIDDEN_BRANCH_SCREEN_POLICIES:
  candidates=[(out.parent/'topology-partial-source-length','graph_with_edges.json'),(out.parent/'topology-confirmed-overlapping-branches','graph_with_confirmed_overlapping_branches.json'),(out.parent/'topology-confirmed-gap-tee','graph_with_confirmed_gap_tee.json'),(out.parent/'topology-confirmed-circle-junctions','graph_with_confirmed_circle_junctions.json'),(out.parent/'topology-source-segment-dimensions','graph_with_source_segment_dimensions.json'),(out.parent/'topology-dn-inheritance-candidates','graph_with_dn_inheritance_candidates.json'),(out.parent/'topology-local-dn-observations','graph_with_local_dn_observations.json'),(out.parent/'topology-source-reviewed-circles','graph_with_source_reviewed_circles.json'),(out.parent/'topology-confirmed-interfaces','graph_with_confirmed_interfaces.json'),(out.parent/'topology-equipment-identity','graph_with_equipment_identity.json'),(out.parent/'topology-source-main-continuity','graph_with_main_continuity.json'),(out.parent/'topology-source-glyph-conflicts','graph_with_source_glyph_conflicts.json'),(out.parent/'topology-endpoint-semantics','graph_with_endpoint_semantics.json')]
  if overlap_followup_graph:candidates.insert(1,(overlap_followup_graph.parent,overlap_followup_graph.name))
  if tid in CIRCLE_CONFLICT_RECONCILIATION_POLICIES:candidates.insert(0,(out.parent/'topology-circle-conflict-reconciled','graph_with_edges.json'))
  if tid in FOLLOWUP_SOURCE_REVIEWED_POLICIES:candidates.insert(0,(out.parent/'topology-followup-source-reviewed-circles','graph_with_source_reviewed_circles.json'))
  if calibrated_source_graph:candidates.insert(0,(calibrated_source_graph.parent,calibrated_source_graph.name))
  if post_dimension_interface_graph:candidates.insert(0,(post_dimension_interface_graph.parent,post_dimension_interface_graph.name))
  existing=[folder/name for folder,name in candidates if (folder/name).is_file()]
  if not existing:raise ValueError('hidden branch screen requires source-bound endpoint graph')
  source_graph=existing[0];policy=pathlib.Path(HIDDEN_BRANCH_SCREEN_POLICIES[tid]);dest=rep/'hidden-branch-circle-screen.json'
  if not policy.is_absolute():policy=args.hidden_branch_screen_policy_map.parent/policy
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('plan_hidden_branch_circle_screen.py')),'--source',str(src),'--graph',str(source_graph),'--policy',str(policy),'--output',str(dest)],check=True)
  evidence=json.loads(dest.read_text(encoding='utf8'))
  dump(rep/'hidden-branch-circle-screen-stage.json',{'status':'candidate_screen_not_connection_confirmation','source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'candidate_relations':len(evidence['candidates']),'hil_ready':False})
 if tid in DETAIL_GLYPH_POLICIES:
  candidates=[(out.parent/'topology-partial-source-length','graph_with_edges.json'),(out.parent/'topology-confirmed-overlapping-branches','graph_with_confirmed_overlapping_branches.json'),(out.parent/'topology-confirmed-gap-tee','graph_with_confirmed_gap_tee.json'),(out.parent/'topology-confirmed-circle-junctions','graph_with_confirmed_circle_junctions.json'),(out.parent/'topology-source-segment-dimensions','graph_with_source_segment_dimensions.json'),(out.parent/'topology-dn-inheritance-candidates','graph_with_dn_inheritance_candidates.json'),(out.parent/'topology-local-dn-observations','graph_with_local_dn_observations.json'),(out.parent/'topology-source-reviewed-circles','graph_with_source_reviewed_circles.json'),(out.parent/'topology-confirmed-interfaces','graph_with_confirmed_interfaces.json'),(out.parent/'topology-equipment-identity','graph_with_equipment_identity.json'),(out.parent/'topology-source-main-continuity','graph_with_main_continuity.json'),(out.parent/'topology-source-glyph-conflicts','graph_with_source_glyph_conflicts.json'),(out.parent/'topology-endpoint-semantics','graph_with_endpoint_semantics.json'),(out.parent/'topology-expert-detail-comparison','graph_with_edges.json')]
  if overlap_followup_graph:candidates.insert(1,(overlap_followup_graph.parent,overlap_followup_graph.name))
  if tid in CIRCLE_CONFLICT_RECONCILIATION_POLICIES:candidates.insert(0,(out.parent/'topology-circle-conflict-reconciled','graph_with_edges.json'))
  if tid in FOLLOWUP_SOURCE_REVIEWED_POLICIES:candidates.insert(0,(out.parent/'topology-followup-source-reviewed-circles','graph_with_source_reviewed_circles.json'))
  if calibrated_source_graph:candidates.insert(0,(calibrated_source_graph.parent,calibrated_source_graph.name))
  if post_dimension_interface_graph:candidates.insert(0,(post_dimension_interface_graph.parent,post_dimension_interface_graph.name))
  existing=[folder/name for folder,name in candidates if (folder/name).is_file()]
  if not existing:raise ValueError('detail glyph comparison requires a detail graph')
  source_graph=existing[0];policy=pathlib.Path(DETAIL_GLYPH_POLICIES[tid]);dest=rep/'source-detail-glyph-ambiguity.json'
  if not policy.is_absolute():policy=args.detail_glyph_policy_map.parent/policy
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('detail_glyph_ambiguity.py')),'--source',str(src),'--graph',str(source_graph),'--policy',str(policy),'--output',str(dest)],check=True)
  dump(rep/'source-detail-glyph-ambiguity-stage.json',{'status':'individual_mapping_unverified','source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'hil_ready':False})
  if tid in DETAIL_FRAME_POLICIES:
   frame_policy=pathlib.Path(DETAIL_FRAME_POLICIES[tid]);frame_policy=frame_policy if frame_policy.is_absolute() else args.detail_frame_policy_map.parent/frame_policy
   frame_dest=rep/'source-detail-frame-context.json'
   subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('source_detail_frame_links.py')),'--source',str(src),'--graph',str(source_graph),'--glyphs',str(dest),'--policy',str(frame_policy),'--output',str(frame_dest)],check=True)
   frame=json.loads(frame_dest.read_text(encoding='utf8'))
   dump(rep/'source-detail-frame-context-stage.json',{'status':frame['status'],'source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256(frame_dest.read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(frame_policy.read_bytes()).hexdigest(),'candidate_count':len(frame['candidate_rows']),'mapping_ready':False,'hil_ready':False})
   subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('detail_frame_relative_candidates.py')),'--frames',str(frame_dest),'--glyphs',str(dest),'--graph',str(source_graph),'--output',str(rep/'source-detail-frame-relative-candidates.json')],check=True)
   frame_stage=rep/'source-detail-frame-context-stage.json';stage_data=json.loads(frame_stage.read_text(encoding='utf8'));stage_data.update(relative_evidence_sha256=hashlib.sha256((rep/'source-detail-frame-relative-candidates.json').read_bytes()).hexdigest(),relative_script_sha256=hashlib.sha256(pathlib.Path(__file__).with_name('detail_frame_relative_candidates.py').read_bytes()).hexdigest());dump(frame_stage,stage_data)
  if tid in DETAIL_SCOPE_POLICIES:
   scope_policy=pathlib.Path(DETAIL_SCOPE_POLICIES[tid]);scope_policy=scope_policy if scope_policy.is_absolute() else args.detail_scope_policy_map.parent/scope_policy
   subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('detail_scope_coverage.py')),'--source',str(src),'--graph',str(source_graph),'--glyphs',str(dest),'--policy',str(scope_policy),'--output',str(rep/'detail-scope-coverage.json')],check=True)
   if tid in DETAIL_BOUNDARY_POLICIES:
    boundary_policy=pathlib.Path(DETAIL_BOUNDARY_POLICIES[tid]);boundary_policy=boundary_policy if boundary_policy.is_absolute() else args.detail_boundary_policy_map.parent/boundary_policy
    subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('detail_boundary_scope.py')),'--source',str(src),'--graph',str(source_graph),'--scope',str(rep/'detail-scope-coverage.json'),'--policy',str(boundary_policy),'--output',str(rep/'detail-boundary-coverage.json')],check=True)
    if tid in DETAIL_FRAME_POLICIES:
     boundary_frame_dest=rep/'source-detail-frame-boundary-candidates.json'
     subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('detail_frame_boundary_candidates.py')),'--frames',str(frame_dest),'--scope',str(rep/'detail-scope-coverage.json'),'--boundaries',str(rep/'detail-boundary-coverage.json'),'--graph',str(source_graph),'--output',str(boundary_frame_dest)],check=True)
     frame_stage=rep/'source-detail-frame-context-stage.json';stage_data=json.loads(frame_stage.read_text(encoding='utf8'));stage_data.update(boundary_evidence_sha256=hashlib.sha256(boundary_frame_dest.read_bytes()).hexdigest(),boundary_script_sha256=hashlib.sha256(pathlib.Path(__file__).with_name('detail_frame_boundary_candidates.py').read_bytes()).hexdigest());dump(frame_stage,stage_data)
  if tid in DETAIL_EVIDENCE_ISLANDS:
   islands=pathlib.Path(DETAIL_EVIDENCE_ISLANDS[tid]);islands=islands if islands.is_absolute() else args.detail_evidence_islands_map.parent/islands
   gate=rep/'detail-evidence-gate.json'
   subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('detail_evidence_gate.py')),'--source',str(src),'--graph',str(source_graph),'--islands',str(islands),'--glyphs',str(dest),'--output',str(gate)],check=True)
   gate_result=json.loads(gate.read_text(encoding='utf8'))
   dump(rep/'detail-evidence-gate-stage.json',{'status':gate_result['status'],'source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256(gate.read_bytes()).hexdigest(),'candidate_count':gate_result['candidate_count'],'mapping_ready':gate_result['mapping_ready'],'hil_ready':False})
 if tid in CIRCLE_RIM_SCREEN_POLICIES:
  candidates=[(out.parent/'topology-partial-source-length','graph_with_edges.json'),(out.parent/'topology-confirmed-overlapping-branches','graph_with_confirmed_overlapping_branches.json'),(out.parent/'topology-confirmed-gap-tee','graph_with_confirmed_gap_tee.json'),(out.parent/'topology-confirmed-circle-junctions','graph_with_confirmed_circle_junctions.json'),(out.parent/'topology-source-segment-dimensions','graph_with_source_segment_dimensions.json'),(out.parent/'topology-dn-inheritance-candidates','graph_with_dn_inheritance_candidates.json'),(out.parent/'topology-local-dn-observations','graph_with_local_dn_observations.json'),(out.parent/'topology-source-reviewed-circles','graph_with_source_reviewed_circles.json'),(out.parent/'topology-confirmed-interfaces','graph_with_confirmed_interfaces.json'),(out.parent/'topology-equipment-identity','graph_with_equipment_identity.json'),(out.parent/'topology-source-main-continuity','graph_with_main_continuity.json'),(out.parent/'topology-source-glyph-conflicts','graph_with_source_glyph_conflicts.json'),(out.parent/'topology-endpoint-semantics','graph_with_endpoint_semantics.json')]
  if overlap_followup_graph:candidates.insert(1,(overlap_followup_graph.parent,overlap_followup_graph.name))
  if tid in CIRCLE_CONFLICT_RECONCILIATION_POLICIES:candidates.insert(0,(out.parent/'topology-circle-conflict-reconciled','graph_with_edges.json'))
  if tid in FOLLOWUP_SOURCE_REVIEWED_POLICIES:candidates.insert(0,(out.parent/'topology-followup-source-reviewed-circles','graph_with_source_reviewed_circles.json'))
  if calibrated_source_graph:candidates.insert(0,(calibrated_source_graph.parent,calibrated_source_graph.name))
  if post_dimension_interface_graph:candidates.insert(0,(post_dimension_interface_graph.parent,post_dimension_interface_graph.name))
  existing=[folder/name for folder,name in candidates if (folder/name).is_file()]
  if not existing:raise ValueError('circle rim screen requires an endpoint graph')
  source_graph=existing[0];policy=pathlib.Path(CIRCLE_RIM_SCREEN_POLICIES[tid]);dest=rep/'source-circle-rim-screen.json'
  if not policy.is_absolute():policy=args.circle_rim_screen_policy_map.parent/policy
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('source_circle_rim_tee_screen.py')),'--source',str(src),'--graph',str(source_graph),'--policy',str(policy),'--output',str(dest)],check=True)
  evidence=json.loads(dest.read_text(encoding='utf8'));pending=sum(x['status']!='existing_graph_connection_unreviewed' for x in evidence['candidates'])+len(evidence['ambiguous_native_geometry'])+len(evidence['unsupported_circle_transforms'])
  dump(rep/'source-circle-rim-screen-stage.json',{'status':'source_shape_comparison_pending' if pending else 'no_unresolved_supported_shapes_found','source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),'unresolved_shapes':pending,'hil_ready':False})
  if tid in EXTRA_CIRCLE_POLICIES:
   screens=[];radii={evidence['circle_radius']}
   for index,relative in enumerate(EXTRA_CIRCLE_POLICIES[tid],1):
    extra_policy=pathlib.Path(relative);extra_policy=extra_policy if extra_policy.is_absolute() else args.additional_circle_rim_policy_map.parent/extra_policy
    extra_dest=rep/f'source-circle-rim-extra-{index}.json'
    subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('source_circle_rim_tee_screen.py')),'--source',str(src),'--graph',str(source_graph),'--policy',str(extra_policy),'--output',str(extra_dest)],check=True)
    extra=json.loads(extra_dest.read_text(encoding='utf8'));radius=extra['circle_radius']
    if radius in radii:raise ValueError('duplicate circle screen radius')
    radii.add(radius);screens.append({'path':f'reports/{extra_dest.name}','radius':radius,'evidence_sha256':hashlib.sha256(extra_dest.read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(extra_policy.read_bytes()).hexdigest()})
   dump(rep/'source-circle-rim-additional-stage.json',{'status':'additional_circle_screens_required','source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'policy_map_sha256':hashlib.sha256(args.additional_circle_rim_policy_map.read_bytes()).hexdigest(),'screens':screens,'hil_ready':False})
  if tid in NEAR_OFFSET_CIRCLE_POLICIES:
   near_policy=pathlib.Path(NEAR_OFFSET_CIRCLE_POLICIES[tid]);near_policy=near_policy if near_policy.is_absolute() else args.near_offset_circle_policy_map.parent/near_policy
   near_dest=rep/'near-offset-circle-screen.json';subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('near_offset_circle_candidates.py')),'--source',str(src),'--graph',str(source_graph),'--policy',str(near_policy),'--output',str(near_dest)],check=True)
   near=json.loads(near_dest.read_text(encoding='utf8'));dump(rep/'near-offset-circle-stage.json',{'status':'near_offset_circle_screen_required','source_sha256':readability['source_sha256'],'graph_sha256':hashlib.sha256(source_graph.read_bytes()).hexdigest(),'policy_map_sha256':hashlib.sha256(args.near_offset_circle_policy_map.read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256(near_policy.read_bytes()).hexdigest(),'evidence_sha256':hashlib.sha256(near_dest.read_bytes()).hexdigest(),'candidate_count':len(near['candidates']),'ambiguous_count':len(near['ambiguous_native_geometry']),'hil_ready':False})
 if tid in DUPLICATE_MAIN_TASKS:
  if tid not in CIRCLE_RIM_SCREEN_POLICIES:raise ValueError('duplicate main diagnostics require the current circle rim screen')
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('duplicate_native_main_diagnostics.py')),'--source',str(src),'--graph',str(source_graph),'--screen',str(rep/'source-circle-rim-screen.json'),'--output',str(rep/'duplicate-native-main-diagnostics.json')],check=True)
 if tid in PROJECT_KNOWN_ERRATA:
  settings={key:pathlib.Path(value) for key,value in PROJECT_KNOWN_ERRATA[tid].items()}
  settings={key:value if value.is_absolute() else args.project_known_erratum_policy_map.parent/value for key,value in settings.items()}
  parent_graph=source_graph;dest=out.parent/'topology-project-known-erratum'
  command=[sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('apply_known_project_pipe_erratum.py')),'--source',str(src),'--graph',str(parent_graph),'--devices',str(parent_graph.parent/'assigned_edge_device_instances.csv'),'--output',str(dest)]
  for flag,path in settings.items():command+=['--'+flag.replace('_','-'),str(path)]
  subprocess.run(command,check=True)
  audit=json.loads((dest/'project-known-erratum-audit.json').read_text(encoding='utf8'))
  dump(rep/'project-known-erratum-stage.json',dict(status='explicit_project_known_erratum_source_checked',source_sha256=readability['source_sha256'],parent_graph_sha256=hashlib.sha256(parent_graph.read_bytes()).hexdigest(),graph_sha256=audit['output_graph_sha256'],artifact_directory=str(dest.resolve()),audit_sha256=hashlib.sha256((dest/'project-known-erratum-audit.json').read_bytes()).hexdigest(),hil_ready=False))
  summary['project_known_erratum_graph']=str((dest/'graph_with_edges.json').resolve());source_graph=dest/'graph_with_edges.json'
 if tid in ROTATED_EQUIPMENT_IDENTITIES:
  policy=pathlib.Path(ROTATED_EQUIPMENT_IDENTITIES[tid]);policy=policy if policy.is_absolute() else args.rotated_equipment_identity_policy_map.parent/policy
  dest=out.parent/'topology-rotated-equipment-identity';parent_graph=source_graph
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('resolve_rotated_equipment_labels.py')),'--source',str(src),'--graph',str(parent_graph),'--devices',str(parent_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  identity_audit=json.loads((dest/'equipment-identity-layout-audit.json').read_text(encoding='utf8'))
  dump(rep/'equipment-layout-identity-stage.json',{'status':'isolated_equipment_identities_source_checked','source_sha256':readability['source_sha256'],'parent_graph_sha256':hashlib.sha256(parent_graph.read_bytes()).hexdigest(),'graph_sha256':identity_audit['output_graph_sha256'],'artifact_directory':str(dest.resolve()),'audit_sha256':hashlib.sha256((dest/'equipment-identity-layout-audit.json').read_bytes()).hexdigest(),'hil_ready':False})
  summary['source_checked_equipment_identity_graph']=str((dest/'graph_with_edges.json').resolve());summary['equipment_identity_aliases']={r['old_node_id']:r['new_node_id'] for r in identity_audit['records']}
  source_graph=dest/'graph_with_edges.json'
 if tid in LAYOUT_EQUIPMENT_OWNERSHIPS:
  settings={key:pathlib.Path(value) for key,value in LAYOUT_EQUIPMENT_OWNERSHIPS[tid].items()}
  settings={key:value if value.is_absolute() else args.source_layout_equipment_ownership_policy_map.parent/value for key,value in settings.items()}
  parent_graph=source_graph;dest=out.parent/'topology-source-layout-equipment-ownership'
  from calibrated_ownership_scope_composition import entry_for_policy
  ownership_script=entry_for_policy(json.loads(settings['policy'].read_text(encoding='utf8')))
  command=[sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name(ownership_script)),'--source',str(src),'--graph',str(parent_graph),'--devices',str(parent_graph.parent/'assigned_edge_device_instances.csv'),'--output',str(dest)]
  for ownership_flag,ownership_path in settings.items():command+=['--'+ownership_flag.replace('_','-'),str(ownership_path)]
  subprocess.run(command,check=True)
  ownership_audit=json.loads((dest/'calibrated-equipment-ownership-audit.json').read_text(encoding='utf8'))
  dump(rep/'source-layout-equipment-ownership-stage.json',{'status':'native_calibrated_logical_ownership_source_checked','source_sha256':readability['source_sha256'],'parent_graph_sha256':hashlib.sha256(parent_graph.read_bytes()).hexdigest(),'graph_sha256':ownership_audit['output_graph_sha256'],'artifact_directory':str(dest.resolve()),'audit_sha256':hashlib.sha256((dest/'calibrated-equipment-ownership-audit.json').read_bytes()).hexdigest(),'hil_ready':False})
  summary['source_layout_equipment_ownership_graph']=str((dest/'graph_with_edges.json').resolve());summary['source_layout_owned_equipment']=len({r['equipment_id'] for r in ownership_audit['records']})
  source_graph=dest/'graph_with_edges.json'
 if tid in SIDEVIEW_EQUIPMENT_OWNERSHIPS:
  source_graph,sideview_owner_audit=run_sideview_ownership_stage(src,source_graph,SIDEVIEW_EQUIPMENT_OWNERSHIPS[tid],out.parent)
  summary['source_sideview_equipment_ownership_graph']=str(source_graph.resolve());summary['source_sideview_owned_equipment']=len({r['equipment_id'] for r in sideview_owner_audit['records']})
 if tid in FINAL_CIRCLE_PATHS:
  policy=pathlib.Path(FINAL_CIRCLE_PATHS[tid]);policy=policy if policy.is_absolute() else args.final_circle_path_policy_map.parent/policy
  parent_graph=source_graph;dest=out.parent/'topology-native-circle-path-normalization'
  subprocess.run([sys.executable,'-X','utf8',str(pathlib.Path(__file__).with_name('normalize_plan_circle_paths.py')),'--source',str(src),'--graph',str(parent_graph),'--devices',str(parent_graph.parent/'assigned_edge_device_instances.csv'),'--policy',str(policy),'--output',str(dest)],check=True)
  circle_audit=json.loads((dest/'circle-path-normalization-audit.json').read_text(encoding='utf8'))
  dump(rep/'circle-path-normalization-stage.json',{'status':'native_circle_radius_excluded_local_topology_unchanged','source_sha256':readability['source_sha256'],'parent_graph_sha256':hashlib.sha256(parent_graph.read_bytes()).hexdigest(),'graph_sha256':circle_audit['output_graph_sha256'],'artifact_directory':str(dest.resolve()),'audit_sha256':hashlib.sha256((dest/'circle-path-normalization-audit.json').read_bytes()).hexdigest(),'hil_ready':False})
  summary['native_circle_path_graph']=str((dest/'graph_with_edges.json').resolve());summary['native_circle_radii_excluded']=len(circle_audit['records'])
 if tid in INHERITED_WAVE_CONTINUITIES:
  source_graph,wave_audit=run_inherited_wave_stage(src,source_graph,INHERITED_WAVE_CONTINUITIES[tid],out.parent)
  summary['source_inherited_wave_graph']=str(source_graph.resolve());summary['source_inherited_wave_pairs']=wave_audit['proof']['pairs']
  summary['dependent_mapping_attributes_and_HIL_invalidated']=True
  from final_source_graph_summary import refresh as refresh_final_summary
  summary=refresh_final_summary(summary,source_graph)
 if tid in PLAN_CIRCLE_CONTINUITIES:
  source_graph,circle_stage_receipts=run_plan_circle_stage(src,source_graph,PLAN_CIRCLE_CONTINUITIES[tid],out.parent)
  summary['source_plan_circle_continuity_graph']=str(source_graph.resolve());summary['source_plan_circle_continuity_stages']=len(circle_stage_receipts)
  summary['dependent_mapping_attributes_and_HIL_invalidated']=True
  from final_source_graph_summary import refresh as refresh_final_summary
  summary=refresh_final_summary(summary,source_graph)
 if tid in REVIEWED_INTERFACE_OWNERS:
  owner_parent=pathlib.Path(summary.get('source_inherited_wave_graph',summary.get('native_circle_path_graph',str(source_graph))))
  source_graph,owner_audit=run_reviewed_owner_stage(src,owner_parent,REVIEWED_INTERFACE_OWNERS[tid],out.parent)
  summary['source_reviewed_interface_owner_graph']=str(source_graph.resolve());summary['source_reviewed_interface_owner_links']=len(owner_audit['proof']['records'])
  summary['dependent_mapping_attributes_and_HIL_invalidated']=True
  from final_source_graph_summary import refresh as refresh_final_summary
  summary=refresh_final_summary(summary,source_graph)
 if tid in REVIEWED_PLAN_GAPS:
  source_graph,gap_audit=run_reviewed_gap_stage(src,source_graph,REVIEWED_PLAN_GAPS[tid],out.parent)
  summary['source_reviewed_drawing_gap_graph']=str(source_graph.resolve());summary['source_reviewed_gap_continuations']=len(gap_audit['proof']['source_pairs'])
  summary['dependent_mapping_attributes_and_HIL_invalidated']=True
  from final_source_graph_summary import refresh as refresh_final_summary
  summary=refresh_final_summary(summary,source_graph)
 if tid in WAVE_MAIN_COHORTS:
  wave_main_parent=source_graph
  source_graph,wave_main_audit=run_wave_main_cohort_stage(src,source_graph,WAVE_MAIN_COHORTS[tid],out.parent)
  summary['source_wave_main_cohort_graph']=str(source_graph.resolve());summary['source_wave_main_cohort_connections']=wave_main_audit['proof']['connections']
  summary['dependent_mapping_attributes_and_HIL_invalidated']=True
  from final_source_graph_summary import refresh as refresh_final_summary
  summary=refresh_final_summary(summary,source_graph)
 if tid in CAPPED_BRANCH_ANNOTATIONS:
  annotation_graph=pathlib.Path(summary.get('source_reviewed_drawing_gap_graph',summary.get('source_reviewed_interface_owner_graph',summary.get('source_plan_circle_continuity_graph',summary.get('source_inherited_wave_graph',summary.get('native_circle_path_graph',str(source_graph)))))))
  annotation_policy=CAPPED_BRANCH_ANNOTATIONS[tid]
  if tid in WAVE_MAIN_COHORTS:
   from wave_main_cohort_stage import rebase_unchanged_annotation_policy
   annotation_policy=rebase_unchanged_annotation_policy(src,wave_main_parent,source_graph,annotation_policy,out.parent)
   annotation_graph=source_graph
  annotation_stage=run_capped_annotation_stage(src,annotation_graph,annotation_policy,out.parent)
  summary['native_capped_branch_annotation_records']=annotation_stage['records'];summary['native_capped_branch_annotation_stage']=str((rep/'native-capped-branch-annotations-stage.json').resolve())
 print(json.dumps(summary,ensure_ascii=False),flush=True)
