# Plan circle contacts and native source paths

Use after the drawing's local circle conventions and same-system branch contact have been established. A line ending at a connection circle's rim may already be logically attached to a T at the center. Requiring the native pipe LINE itself to reach the center rejects a valid symbol expression. Conversely, extending that LINE to the center and counting the radius creates unmeasured pipe length.

Preserve three distinct things: the logical T at the main, the source pipe path ending at the rim, and the symbolic contact between them. A circle is neither an extra device nor a measured connector. An unreviewed circle or ordinary crossing does not establish this relation.

## Source proof

`native_circle_rim_junction_evidence.py` reuses the independently hashed technical source review, original Pair, `source_reviewed_circle_connections.candidate`, native circle transform, radial contact, source LINE uniqueness, system isolation, Z and interface-interference guards. Each T must have exactly three same-system graph arms: two main rays on the same uniquely witnessed native LINE and one reviewed radial branch. Verify native coverage from rim to branch, without adding a center-to-rim pipe. Rotations/mirrors use source vectors rather than a preferred orientation. Unsupported geometry stays pending.

`crossview_equipment_branch_inventory.native_tee` dispatches these explicitly evidenced circles to that collector. Straight T and selected INSERT-ray checks remain unchanged. This fixes an entry-coverage gap; it does not repair connectivity or accept a cross-view mapping. Do not increase the global snap tolerance or manufacture an imaginary source LINE to make the old straight-ray checker pass.

## Existing paths that include the radius

`normalize_plan_circle_paths.py` handles explicit source-reviewed circles whose logical T is already present but whose branch source path still includes a graphic radius. Pin the source, calibrated ownership parent, component CSV, review manifest and Pair hashes. Reuse `correct_circle_branch_lengths` to remove only the radius; preserve endpoints, IDs, main segmentation, equipment ownership evidence and all component bytes. Reject an already normalized circle, ambiguous native contacts or overlapping fused attributes.

Keep the original calibrated ownership snapshot bound to its immutable parent. The new edge record retains both the old and current snapshots, independently replayed by the normalization stage. Inventory may use that prior snapshot only for the unchanged logical owner; current path coverage uses the corrected path. Never edit the old confirmation or claim a newly measured physical port/connector.

The full ceiling entry is `build_ceiling_family.py --final-circle-path-policy-map`, after local source checks and calibrated ownership, before cross-view mapping. Each task maps to a pinned normalization policy. The pipeline and viewer replay this newest local stage before inherited ownership and caption stages, preserving the original parent comparison and its unresolved scopes. Changed paths invalidate downstream mapping, diameter, length fusion and human acceptance; old annotations remain historical.

## Regression and scope

Run `test_normalize_plan_circle_paths.py`, branch inventory, historical source-reviewed circle/length, native T, equipment ownership and cross-view tests. Include the circle-path pipeline/viewer gates and full builder. Check positive rotated/mirrored contacts and negative duplicate mains, opposite-system contacts, Z differences, stale review/Pair, four-arm incidence, retained-radius paths and repeated normalization. Run the affected full family entry and compare its output with isolated reconstruction.

SH16 08 exposed two separate cases: eight already-trimmed radius-80 contacts rejected by a straight-only cross-view entry, and eight radius-100 spans still included in drawing lengths. Verify and report both separately. Preserving connectivity while excluding drawing length does not complete physical installed length, whole-plan acceptance, LF20 or HIL.

## Historical reconstructed-circle schema

Some earlier formal reconstruction outputs retain node `source_reviewed_circle`, edge `source_reviewed_circle_connection`, and root `sourceReviewedCircleJunctionRepair`. These are distinct from `source_circle_connection`; dispatch by the actual schema rather than assuming a missing straight graph ray means an unconnected source pipe.

`source_reviewed_circle_branch_evidence.collect` reloads the original hashed review and Pair, reuses `source_reviewed_circle_connections.candidate`, and checks the root/node/branch bindings, unique branch identity, recorded main children and three distinct same-system native rays. The source path still ends at the rim. It neither rewrites the old graph nor counts the radius as a pipe. Unsupported 3-D control replay remains pending rather than flattening Z.

For a branch divided by a previously excluded opposite-system crossing, `branch_coverage` audits each actual path under its own projection hash. It reuses `correct_plan_crossover_lengths.apply` to recheck actual native tails, the opposite-system crossing and unique current edge ownership. Derived current gap/fragment projections carry their own hashes; they do not impersonate the historical artifacts named by the edge. Every path must belong to one connected chain and every discontinuity must be accounted for. No new node is introduced at the crossing, and omitted physical length stays unknown.

The existing branch-inventory entry dispatches this schema and records source-evidence implementation hashes in its output so changing a dependency invalidates native replay. Run `test_source_reviewed_circle_branch_evidence`, the old circle/inventory/crossover tests, native-block reconstruction and source-checked mapping tests, then rebuild the affected local/inventory/mapping stages. SH16 09's six east equipment pairs exposed this entry gap; local success is not cross-view or HIL acceptance.

## Repair history, confirmed controls and later main splits

For both `sourceReviewedCircleJunctionRepair` and `userConfirmedCircleJunctionRepair`, walk `previous_repair` and require exactly one matching circle/T, original source binding and comparison/confirmation. A newer unrelated repair must not hide the earlier control. Duplicate or conflicting memberships fail. Explicit user confirmation of a source circle with a wrong service colour or inconsistent Z permits only that original scoped drawing relation: recheck the real two pipe layers, radial contact, three current graph rays, glyph/crossing guards and recorded finite XYZ. Never assign service from the circle alone.

For technically matched 3D circles, the earlier checker expects an unresolved rim terminal. After reconstruction that terminal is properly gone. Reload the real before graph through the review manifest, require its content hash to equal both the repair parent and the node's original source graph, reproduce the retired terminal/floor/branch, and run the original 3D signature rule there. Independently recheck the current user-confirmed control and current branch/main source geometry. Do not create a fake terminal or loosen the original rule.

If a reviewed main child was later split, accept its descendant only with the recorded later repair, original hashed native Pair/review and parent graph, exact source interval sliced by the old path primitive, unchanged service/source ownership, and current native T rays. Mere ID similarity or a `split_source_edge` flag is insufficient.

Tests include `test_historical_circle_branch_controls.py`, earlier circle/3D/control and crossover tests, plus native inventory and full selected source scopes. SH16 10 first twelve equipment pairs exposed buried controls and later splits; fixing this entry does not itself repair every remaining plan interface or prove cross-view identity.
