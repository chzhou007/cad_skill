# Source-checked dual-view paths and attributes

Use these entries after local branches in both drawings have independently passed source checks. This is scoped technical correspondence, not a fabricated expert answer or whole-drawing acceptance. Keep the original expert-confirmed mapping entry for explicit reviewed cases.

`match_source_checked_crossview_paths.py` pins the native inventory, its receipt, both sources and both local graphs. Independently replay the inventory and select an explicit floor/equipment group. Every selected device must have both services source-checked. Matching a name, position or shaft label alone is insufficient.

## Mutual topology and native geometry

For each service, require at least three distinct main T anchors. In each native view, find one uniquely witnessed modelspace same-system LINE containing those anchors. Restrict the main correspondence to graph segments actually covered by that LINE; keep the rest of each original graph intact. Compare all pairwise sequences of selected branch identities and require a single mutually corroborated chain in that corridor. Adjacent selected intervals may contain several local edges; record path-to-path correspondence rather than forcing equal edge counts.

A hydraulic ring can have other routes outside this native corridor. Do not call the whole system a unique route or select a shortest path to resolve it. Duplicate native lines, parallel/cyclic alternatives inside the corridor, wrong branch order, shared T anchors, another floor, missing local evidence or ambiguous coverage must stop acceptance. Ordinary crossings never become graph connections from correspondence alone.

Independently check native LINE coverage on each adjacent main path, and retain the local branch/T source evidence. Mapped main edges must already be segmented at the verified Ts; if mapping introduces a new landing point, return to local reconstruction and split/reassign/recompute before proceeding. Preserve both local node/edge graphs and their hashes.

Output `mapping.json` plus `source-mapping-receipt.json`. Records distinguish equipment branches from intervals between their main Ts, retain full selected snapshots, and explicitly set `expert_confirmation_claimed=false` and `human_accepted=false`. `pipeline.py validate-source-crossview --mapping-run ...` independently replays this proof and remains pending for attributes and broader review.

## Attribute composition

For checked whole-main DN or centerline route extents, use the additive [plan DN inheritance stage](plan-DN-inheritance-and-extents.md). The default projection-only entry below keeps its earlier unknown-value behavior. The optional replayed DN stage may upgrade only independently proved whole horizontal T-to-T main scopes; branch connectors, net cut lengths and human acceptance remain separate.

`attach_source_checked_plan_attributes.py` consumes that replayed correspondence and a separately replayed parent containing the earlier confirmed attributes. Their underlying local axis hashes must agree. Recheck the millimetre floor-plan header, native floor title and at least two independently directed native dimensions with actual rendered numeric text and unit factor. Dimensions corroborate units; pipe lengths come from uniquely covered native plan LINE geometry.

Attach only plan XY projection. A one-to-many axis path retains a route total until allocation is proved; never repeat that total on every child edge. Keep installed whole-edge lengths, omitted connectors, drops and physical ports unknown. Preserve all earlier attributes and component bytes; reject overlapping writers, including an empty existing attribute object.

Re-read any local plan DN observation from its exact native text, same-system source LINE and mapped source point. Keep its local scope, original parenthesized source value and `nominal_mm=null` for the edge. A confirmed physical edge-wide DN still requires explicit extent/inheritance evidence. Do not replace the plan DN with an axis annotation on horizontal paths.

Output a separate `sourceCheckedCrossViewAttributeFusion` layer; edge `cross_view_attributes` retains the common partial-source schema and records `mapping_basis=native_source_and_main_branch_order`. The viewer states this technical basis and local DN scope; CSV keeps unknown nominal DN/whole length blank. Source comparison/viewer ancestry replay this newest layer before the earlier confirmed fusion, native block reconstruction and older repairs. Preserve parent pending issues and all old annotations under their old dataset identities.

## Regression

For multiple disjoint groups on the same local plan/axis versions and floor, `attach_source_checked_plan_attribute_groups.py` independently replays every mapping and the common confirmed-attribute parent. Pin each mapping/receipt in a group manifest, prefix group-local mapping IDs, reject duplicate pipe ownership across either view, and preserve original mapping IDs and receipt hashes. Recompute native plan coverage, units and local DN on the combined scope before calling the shared attribute attachment. Its audit uses `mode=batch_source_checked_mapping_groups`; the common attribute verifier dispatches to the batch verifier before assuming single-mapping inputs. Parent blockers, unknown physical values and historical confirmed attributes remain unchanged. Run `test_attach_source_checked_plan_attribute_groups.py`, the single-group and historical attribute tests, pipeline/viewer dispatch tests and a real combined build.

- `test_match_source_checked_crossview_paths.py`: opposite geometric orientation, wrong branch order, duplicate/parallel/cyclic ambiguity, a source corridor inside a real ring, floor/system errors and insufficient/shared anchors.
- `test_attach_source_checked_plan_attributes.py`: preserved prior fusion, one-to-many allocation, stale snapshots, overlapping writers, native local DN and no physical length from parenthesized text.
- Native plan projection/coverage, old confirmed correspondence and attribute tests remain required.
- Pipeline `test_source_checked_crossview_gate.py`, viewer `test_source_checked_attribute_viewer.py`, common edge attribute tests and a real combined viewer build verify stage order and fail-closed source replay.

SH16's first group covers four 08/11 first-floor devices: eight service branches and six adjacent main intervals. The earlier two 09/11 reviewed routes remain separately identifiable. Additional groups, shaft/riser mapping, accepted DN, installed lengths, full SH16 comparison, LF20 and HIL remain separate completion requirements.

## Separate plan paths and multiple floor scopes

`source_checked_plan_path_coverage.py` preserves the old audit result exactly for single paths. A multi-path plan branch requires the replayed historical circle branch and every excluded opposite-service crossover from [plan circle source paths](plan-circle-source-paths.md). The metric retains each native segment's path index and counts only its source-drawn projection, never the crossing gap or an unshown equipment connector. Arbitrary disconnected paths, missing crossover evidence and competing source LINEs fail. `attach_source_checked_plan_attributes.py` and the existing same-floor group entry use this source audit; physical whole length and DN stay separately scoped.

`compose_source_checked_plan_scopes.py` combines completed independently replayed attribute stages from different plans onto one axis presentation. Build every child on the exact same current confirmed-attribute parent and component inventory. Pin the manifest, child graph/receipt hashes, common parent and components. Each child may only add its recorded attributes: all nodes, edge IDs, local source geometry, components, old confirmed attributes and other evidence roots must be identical. Scopes may not write the same axis edge. Namespace mapping IDs while retaining their original scope IDs, input receipts and DN lineage. A graph generated on an older local version must be rebuilt; composition never copies attributes across differing topology hashes.

The common pipeline/viewer verifier dispatches `composed_source_checked_plan_scopes` before earlier attribute modes, independently replays each child and then returns the common confirmed parent for ancestry checks. Keep all pre-existing pending issues and human review false. Tests: `test_source_checked_plan_path_coverage.py`, `test_compose_source_checked_plan_scopes.py`, old projection/group tests, pipeline `test_multifloor_source_attribute_gate.py`, viewer `test_multifloor_source_attribute_viewer.py`, followed by a real combined source gate and viewer build.
