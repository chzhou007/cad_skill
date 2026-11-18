# Native junction correspondence within paired corridors

Use this stage when a checked paired-main interval still contains several local
edges and its total cannot be allocated because intermediate T identities have
not been matched. Do not allocate by drawing position, spacing or length ratio.
Do not invent a third equipment to satisfy the legacy order matcher.

`native_paired_junction_correspondence.collect` replays each existing intermediate
T, identifies its unique non-through branch from native source rays, and traces
that exact branch in the other checked pair's native LINE corridor. Require a
unique bridge path with complete native coverage to the **first already checked
equipment-branch main T**. That target is not a physical equipment port. A nearer
unproved point, ordinary opposite-system crossing, missing source LINE, duplicate
caption, another floor or unresolved T cannot provide this evidence.

Match the two views using the same target pair and literal source equipment
identity. Recheck current graph service ownership and unique native captions.
Intermediate source topology along a link must agree. Require a bijection and
consistent main order; unresolved or competing targets remain unmatched. This
does not connect either local graph or map unexamined outside branches.

`refine_paired_service_path_correspondence.py` first independently replays its base
paired mapping, then recollects the native junction evidence. Only explicitly
required complete groups are refined. Split the **correspondence paths** at the
existing matched Ts, retain original records as superseded history and preserve
all other records. Newly proved connector paths use
`main_between_matched_junctions`; do not label a network T as an equipment.
Reject duplicate path writers in either view. Native node/edge IDs and geometry
remain unchanged because these local edges already end at the physical Ts.

The receipt mode is `paired_service_junction_refined_paths_v1`.
`pipeline.py validate-source-crossview` independently replays that stage and
keeps DN/length fusion and HIL pending. Mapping refinement does not itself set
an edge length or DN. Recompute affected source DN extents, projection allocation
and attributes before publishing it; do not patch final fields or reuse manual
acceptance from an older dataset.

Tests cover first-known-target selection, rotations, literal source identity,
missing/changed source rays, floor/system/review boundaries, incomplete or
duplicated matches, correspondence cuts, overlaps and unchanged unrelated
records. Follow them with the current native source replay and formal pipeline
entry. LF20 remains a later generalization test rather than a development input.

## DN and metric recomputation

`refined_paired_plan_DN_scopes.py` freshly replays the previous paired DN stage,
then reproduces this exact refinement from its already replayed base mapping.
It does not accept a receipt's success flag as a substitute for native replay.
The new link must be a separately normalized, fully source-covered edge whose
target T shares its native through LINE, while the parent T classifies that
same edge as a non-through branch frontier. Both endpoints need the checked
cross-view junction identity. A truncated annotation frontier is insufficient.

Rerun the inherited attribution kernel with the link included in the target
pair's main scope and the parent T excluded from propagation. Recheck every
local label, F binding, leader and compound/ambiguous mark on the expanded
scope. Retain the parent's branch exclusion: DN200 on a branch must not flow
back into a DN300 parent main. Previously checked records and inheritance
chains must remain exact; a newly discovered change/conflict requires the
earlier scope to be rebuilt rather than silently overwritten. This stage still
assigns no physical length and has mode
`paired_service_junction_refined_plan_DN_scopes_v1`.
`pipeline.py validate-plan-DN` dispatches to its native verifier.

`attach_refined_paired_plan_attributes.py` uses this replayed DN stage and the
common confirmed-attribute parent. Measure the refined plan paths using the
existing source coverage and native dimension corroboration. Only a proven
one-to-one, same-floor straight T-to-T route with a configured horizontal
axis bearing can obtain whole horizontal-main DN and centerline route length.
The inherited physical-main classifier is reused internally; stored kinds
remain `main_between_matched_junctions`, with actual junction evidence, never
fake equipment IDs. Unshown connectors, mixed/vertical paths and pipe net cut
length remain unknown. Preserve every local node, edge and inline component.

`compose_refined_paired_plan_attributes.py` replays the unchanged nonpaired
presentation and the replacement child against their exact common parent.
This new child **replaces** its earlier coarse paired child during composition;
do not append both and double-count their common edges. The composer rejects an
already paired presentation and preserves every inherited attribute value,
source root and component. Its audit mode is
`paired_junction_refined_attribute_composition_v1`; its root is
`pairedJunctionCrossViewAttributeFusion`. It is not yet a source-comparison or
viewer acceptance. Rebuild source comparison and viewer,
invalidate affected HIL confirmations, and retain historical annotations.

Source comparison and the viewer dispatch this composed root before inherited
attribute roots and independently reproduce the refined composition. Only then
may they reuse the exact nonpaired base comparison/audit, with its graph hash
and every existing issue retained. A standalone child or combined coarse and
refined presentation is rejected. In the viewer, whole-main DN/length for the
generic junction kind additionally requires the native junction mapping basis
and unique nonempty junction evidence IDs; do not broaden all generic kinds.

Run `test_refined_paired_plan_DN_scopes.py` and
`test_attach_refined_paired_plan_attributes.py`,
`test_compose_refined_paired_plan_attributes.py`, the inherited paired/kernel,
F, T, projection and fusion cases, and the formal DN dispatch tests. Cover
different link/main DN, partial frontiers, new change marks, compound labels,
unequal per-edge lengths after a cut, wrong floor and plumb counterexamples.
Also run `test_refined_paired_attribute_gate.py`,
`test_refined_paired_attribute_viewer.py` and
`test_refined_paired_plan_attributes.mjs` with inherited gate/viewer tests.
