# Component-qualified DN and unmeasured detail topology

Use these entries after independent local topology and correspondence checks. Keep ordinary pipe DN, component nominal labels, physical pipe lengths and drawing spans separate.

## A qualified component label is not a pipe DN seed

`qualified_inline_DN_evidence.collect` handles an explicitly scoped two-line native label (`金属软管` / scalar DN) and its shared-hub LINE leader. Pin source/graph, text handles, leader handles, the existing flexible-joint template fingerprint and the complete expected component population. Reproduce text alignment and rotation, one underline, every leader leaf and all transformed native joint contacts. Check every same-template native instance before resolving a leaf, then require its unique graph component owner, original contacts and canonical name. Keep systems independent. A plain pipe DN, a nearby qualifier, an unbound/competing leaf, changed Z, unsupported glyph or duplicate owner cannot consume annotation text.

The output preserves source nominal labels on components with `physical_parameter_verified=false`, unknown length and unknown resistance. It never assigns the component DN to the pipe, derives DN from graphic span, or fills a missing hydraulic parameter with zero. The original CAD label may differ from the pipe DN; retain both evidence roles.

Only after this replay may `plan_calibrated_DN_scopes.py` remove the exact consumed DN text from its pipe-annotation catalog and exempt the exact proved leader strokes from `group_evidence`'s long-leader guard. The evidence remains in `source_annotation_inventory.qualified_component_DN`. Do not use an arbitrary ignore list or disable the guard. The old plain plan DN entry retains its default strict behavior.

## Replayed sideview owner parents

The calibrated DN entry dispatches `sourceSideviewEquipmentOwnership` before inherited ownership. A retained older root cannot prove a newer graph. Independently replay the new stage and compare its exact output hash. Old ownership parents keep their original verifier; a missing or stale new schema fails closed. New endpoint semantics invalidate affected mapping and attribute receipts, even when native pipe coordinates are unchanged.

## Detail topology has no automatic physical scale

The ordinary `native_plan_projection_lengths.lengths` entry continues to reject `source_view_context`. A verified detail correspondence may use `allow_confirmed_detail_topology_only=true` through the single or grouped source-checked attribute entry. `confirmed_detail_projection.py` requires the current confirmed-view owner root, original alias hash, same floor/service, declared detail-edge population and unique native LINE coverage. Mixed/stale roles and unsupported coverage fail.

All physical projection values stay null. Preserve each native drawing span as drawing evidence, its source handle and a hashed detail context; never label that span as millimetres of physical pipe. Detail-only scopes do not borrow global INSUNITS or floor dimensions as a scale. Real floor-plan records continue through the original unit/dimension and path measurement rules.

## Diameter and length completeness are independent

A source-checked T-to-T horizontal main can have a complete mapped DN scope while its detail-derived physical length remains unknown. After the established direct-label/T-inheritance rule and exact mapping checks, `fuse_plan_DN_scopes.py` may emit `source_checked_whole_horizontal_main_DN_length_unknown` only with the explicit nonmetric detail context. It preserves the known DN and null physical length. Unshown equipment connectors, multi-edge allocation, unresolved changes, source conflicts and net cut lengths remain separate unknowns. Do not withhold a proven DN merely because length is unknown, or manufacture a length to pass the old coupled interface.

The viewer validates the detail context and source DN rows before selecting this DN. Chinese properties explain the detail scope and unknown actual length; CSV exports known nominal DN and blank physical lengths, with the metric status and source context. Legacy measured-main and projection-only behavior remains unchanged.

## Regression and formal entry

Run `test_qualified_inline_DN_evidence.py` (rotated/mirrored joints, qualifier/leader/contact/owner/Z negatives), `test_sideview_plan_DN_parent.py`, `test_confirmed_detail_projection.py`, `test_confirmed_detail_attributes.mjs`, and the old direct/calibrated DN, F, T inheritance, flexible-joint, projection, single/group composition, pipeline and viewer tests. Perform source-bound replay, not just synthetic tests.

Rebuild every affected attribute child on the identical current confirmed-attribute parent, reissue mappings against the current local graph hashes, and compose without overlapping writers or local geometry/component changes. Preserve old values and their source lineage; independently report measured floor-plan lengths, nonmetric detail mappings, complete main DN and unknown connectors. Native/technical checks never imply whole-plan or human acceptance. LF20 remains the later test set after SH16 correctness.
