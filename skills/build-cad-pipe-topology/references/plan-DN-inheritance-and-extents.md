# Plan DN inheritance and dual-view extents

Use `plan_pipe_diameter_scopes.py` after scoped local topology has independently passed native checks. This is additive to existing F/LWPOLYLINE and local DN recognition; it does not replace them. It emits a separate read-only interpretation, not an edited local graph.

## Establish the source before inheriting

Require strict readable native text, source/graph pins and a replayed local topology parent. Inspect modelspace and transformed nested text. Unsupported nested DN, visible proxies, xrefs, general diameter notes or ambiguous leader/compound labels affecting the scope must stop or withhold interpretation. Object-section proxy metadata may be classified and retained as opaque; do not claim its payload was decoded or use that classification to ignore visible entities.

Bind direct scalar DN to a unique same-system native pipe LINE on the current route. Parenthesized source values remain original text, never pipe length. Search for competing changes along the selected route, including nearby unbound labels and leaders whose text lies outside the usual nearest-text radius. A text near another pipe is not evidence for changing this one.

## T inheritance is directional in scope

Use a genuine source-witnessed three-arm same-system T, never a plain crossing or a pending junction. Verify both through-main arms use the same unique native LINE corridor and the source covers every selected path. Inherit along the proved main and into its branch until an explicit new DN. A branch-specific new DN overrides that branch; it must not back-propagate into the main. Conflicting main observations remain unresolved instead of choosing the nearest or most common size.

An unselected feeder may supply the direct seed only on its continuously source-covered portion to the proved T. Clip that portion in the read-only evidence graph; synthetic clipping anchors are not physical nodes. Do not assign a seed across disconnected omission paths or claim the rest of the bent feeder has a known DN. Every result records exact `scope_paths`, the source text/LINE and inheritance edge path. Unshown equipment connectors and drops are outside this scope.

## Exploded LINE F annotations

The existing `pipe_annotation_attributes.py` F entry supports compatible LWPOLYLINE frames. A visually identical F may be exploded into independent LINEs: use the additive `native_line_f_diameter_evidence.py` entry, not a larger nearest-text threshold or an exception to the leader guard.

Pin the native stem, two same-side perpendicular bars and two readable DN texts. Require unambiguous text-to-bar assignment using the actual text pose, exactly two distinct typed pipe contacts on the stem, and unique current graph owners. Rank bars and pipe contacts along the same WCS stem so reversal, rotation and mirror preserve correspondence. Support the tested positive/negative Z OCS and glyph mirror flags explicitly; reject unsupported poses, competing bars/text/pipes, duplicate owners and different source Z. Diagonal ticks are drawing strokes, not extra bars; their approximate positions must not snap or connect pipes. Both services remain independent. Only those independently verified strokes may be removed from the unclassified-leader screen.

SH16 08 supplied the historical coverage gap: BA64 stem, BA65/BA66 bars and BA62/BA63 DN100 texts were independent LINE/TEXT, while the earlier parser expected LWPOLYLINE. Preserve the old entry and its tests when adding this case.

## Fuse extents into the axis graph

`attach_source_checked_plan_attribute_groups.py --diameter-run ...` pins and independently replays `plan-DN-scopes.json` plus its receipt, then checks that source, local graph, systems and exact scope paths match the current correspondences. `fuse_plan_DN_scopes.py` preserves canonical local nodes, edges and component bytes, all historical attributes, original evidence and human-review history.

- Store positive `plan_drawn_nominal_mm` and lineage even when the mapped axis branch includes unshown connector/drop portions. Keep whole-axis `nominal_mm` and physical length unknown there.
- Upgrade a horizontal main only for a one-plan-edge/one-axis-edge relation between independently verified same-floor physical Ts, a single straight source route in each view, and explicitly configured drawing-family horizontal bearings. A plumb stroke cannot be declared horizontal; equal floor numbers alone are insufficient.
- Its length is the native plan **T-to-T centerline route**, corroborated by the existing millimetre/dimension unit evidence. It is not net pipe cut length: component spans are not deducted. Record `whole_edge_length_kind=floor_plan_horizontal_main_centerline_route` and leave `pipe_net_cut_length_mm=null`.
- Mixed paths, one-to-many unallocated paths, omissions, unknown ports and unseen equipment connections keep partial scope. Horizontal attributes come from the plan; axis annotations remain comparison evidence. Inter-floor vertical DN/length still require a separate native axis proof.

Source comparison and viewer ancestry replay the newest stage before inherited stages. The viewer and CSV must expose scope and lineage, use the centerline label, leave unknowns blank and never infer acceptance from a positive value. Local topology changes invalidate mapping, DN inheritance and fusion; semantic changes invalidate prior human confirmation while preserving history.

## Entries and regression

1. `plan_pipe_diameter_scopes.py --source ... --graph ... --policy ... --output ...`
2. `pipeline.py validate-plan-DN --diameter-run ...` independently replays it; the report remains pending for mapping, unshown portions and human acceptance.
3. Batch attribute attachment with pinned evidence hashes, then the shared source comparison gate and viewer build.

Run `test_plan_pipe_diameter_scopes.py`, `test_native_line_f_diameter_evidence.py`, `test_fuse_plan_DN_scopes.py`, inherited `test_diameter_tee_inheritance.py`, `test_source_direct_dn_evidence.py`, `test_dn_source_annotations.py`, both attachment tests, pipeline DN/source-attribute gates and viewer edge/CSV/ancestry tests. Include native SH16 replay and negative branch-override, crossed-system, unknown feeder, F rotation/mirror/negative-OCS, competing annotation and many-to-one allocation cases. Related passing tests do not certify the complete historical matrix or LF20.
