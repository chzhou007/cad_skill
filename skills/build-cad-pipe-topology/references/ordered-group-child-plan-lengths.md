# Native T order and child plan lengths

Use this after a qualified multi-edge path group has uniform known DN, fixed
independent outer junction anchors and current independently checked local
topologies. A group-level metric is not a child-edge metric.

`scripts/ordered_group_plan_lengths.py --manifest MANIFEST --output NEW` selects
all eligible groups from the qualified parent manifest. Replay both complete
native corridors and every T, verify exact selected snapshots, equal interval
counts and orientation fixed by mappings outside the selected groups. Match
internal main junctions by that unique native order. This does not assign
equipment/interface identity or recover an unproved parallel member.

Read each actual plan child with the existing `native_plan_projection_lengths`
unit/source reader. Qualified inline paths reuse `native_inline_joint_path_coverage`
and `anchored_floor_main_plan_attributes.inline_projection`. Preserve source LINE
pieces, actual plan/axis T pairs, hashes, original component owners and unknowns.
Do not divide a group total or use axis-drawing distances/ratios. Do not let a
selected group prove its own outer anchors. Reject changed branch counts,
reversed orientation, a competing native corridor and stale selected snapshots.

A full continuous native child ending at its two proven Ts can expose complete
horizontal run centerline, including valve extents represented by the line.
For inline joints, known drawn pipe XY excludes marker/interior spans. Keep full
run unknown unless those interior extents have independent physical evidence.
Never add a symbolic joint span, infer cut-pipe length from run centerline or
substitute native Z for a physical elevation. Net pipe and installed whole-edge
length stay unknown in this feature. Vertical/cross-floor and detail-only geometry
remain with their separate owners.

`pipeline.py validate-ordered-group-plan-lengths --length-run RUN` independently
replays the native producer and retains pending semantics/HIL. Extend regression
with fixed-end order, reversal, unequal native segmentation, axis-scale changes,
duplicate source coverage, inline unknowns and unchanged local graphs/components.

For an unchanged qualified viewer artifact, use the versioned viewer owner
`refresh_ordered_group_attributes.py` and
`validate-ordered-group-attribute-refresh --bundle VIEWER`. Preserve the original
refresh owners/audits. The prior member-plan context may be retained only after
its original output, source/graph/policy, implementation and receipt bindings
still match. Explicitly call this artifact retention, not fresh reconstruction
of all old mappings. Freshly replay the ordered metric producer. Add compatible
source-bound context and new CSV columns; retain old effective values as history.
Invalidate effective-value HIL even when raw/rendered graph bytes are unchanged.

Before publication, check actual browser properties and actual selected-edge
CSV export for every new child; compare all prior effective values and components,
readable Chinese, source-CAD coordinates, unknown inline/cut lengths, old comments
and new dataset identity. Technical replay and source agreement do not constitute
expert acceptance or LF20 generalization.
