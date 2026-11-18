# Map a confirmed T back to its main, then rebuild edges

Main/detail, side-view or cross-view correspondence is a relation between source
expressions. A confirmed lower/detail T mapped onto a main changes that main's
segmentation. An identity link or diameter annotation on an unchanged edge is
not a reconstruction of that T.

1. Preserve both source views, native handles, current graph hashes and the
   scoped confirmation. Establish the same-system main path and exact landing
   position. A nearby caption, circle or projected crossing alone is insufficient.
2. Re-enter connectivity before deriving final edge attributes. Split the main
   at every distinct mapped physical T and attach its proven branch. A T has
   three distinct incident same-system edges. Separate supply and return, and
   retain source-specific non-node boundaries and ordinary crossing exclusions.
3. Rebuild the node/edge inventory after all landing positions are known. Record
   old-main-to-child-edge and retired-interface-to-T mappings. Preserve parallel
   pipes, every source path and all actual equipment; do not target old counts.
4. Reassign inline instances uniquely to the rebuilt children using native
   positions. A component exactly at a cut remains unresolved until its ownership
   is proved. Preserve native symbol identity and check component conservation.
5. Recompute diameter inheritance, segment/floor attributes and physical-length
   evidence against the rebuilt edges. Transfer a dimension only to its witnessed
   source extent; unshown connectors remain unknown. Existing attribute-bearing
   edges require explicit remapping or re-entry before attribute extraction.
6. Invalidate affected cross-view mappings, derived values and human acceptance.
   Preserve old annotations as history. Compare source, pre-repair and rebuilt
   paths before submitting HIL.

When multiple confirmed Ts land on one main, collect and order all distinct cuts
before reconstruction: N interior Ts produce N+1 main children, plus their branch
edges. Check each T separately for three incident edges and check component
ownership across all children. Reusing a parent ID for one child must never mean
retaining the parent's original whole path. Regression
`test_two_mapped_tees_rebuild_one_main_into_three_component_owned_edges` covers
two cuts, three uniquely owned valves and invalidation of prior acceptance.

A projected plan stroke can represent overlapping mains. A compound caption
such as `DN300(3.600)/DN200(3.000)` does not identify which physical main receives
the branch. Preserve the native side-view topology and establish main identity
before cutting; neither a shared colour nor proximity permits attaching the T
to every coincident same-system main. Independent axis evidence may expose this
ambiguity, but formal cross-view mapping still requires the source checks.

If the confirmed detail already contains that same physical T and the two main
children, reuse its source-verified segmentation rather than retaining a second
isolated copy of the abbreviated branch. `canonicalize_confirmed_sideviews.py`
checks the three native rays, exact Pair replies and component conservation,
then stores the removed drawing expression as representation history with ID
aliases. It never removes actual equipment or promotes non-node boundaries.
The SH16-09 application leaves projected DN300 main edges unchanged; the DN200
detail ends still require their own main-connection proof. The fewer active
nodes/edges represent deduplication, not removal of unknown physical endpoints.

Historical glyph/frame diagnostics use `source_expression_context` to read the
archived drawing geometry. This context is read-only and cannot feed physical
reconstruction. The source-comparison gate classifies archived LINEs separately
only after replaying the canonicalization and comparing the entire current graph
with that output. Keep the raw LINE inventory; do not suppress unrelated missing
lines, short fragments, system conflicts or unresolved network ends.

`reconstruct_batch_circle_junctions.py` implements explicitly answered native
circle cases through `repair_confirmed_circle_junctions.py`. A main may turn at
the circle, with its two rays witnessed by different native LINEs. All three
directions must be distinct; explicit Pair response and unique same-system ray
witnesses are required. This is not an automatic circle-connection detector.
Run `test_reconstruct_batch_circle_junctions.py`,
`test_repair_confirmed_circle_junctions.py`, and the affected full family entry.
SH16-10's separately confirmed 100-unit corner drawing erratum remains a
project known issue, not this general T reconstruction rule.

For explicitly confirmed equipment pairs, `reconstruct_confirmed_equipment_pairs.py`
uses the same reconstruction order through `split_native_main_paths.py`. The
SH16-09 source case has eight interior cuts on each of two independent mains:
each main becomes nine children. Verify every T's two incident main children
and one branch, complete old-main-to-children mappings, conserved native paths,
and unique component ownership. A small explicitly bounded circle offset keeps
its original source center but places the T at the proven branch/main
intersection; the unshown connector is not a measured pipe. Preserve existing
side-view history and unrelated projected mains. `test_split_native_main_paths.py`
and `test_reconstruct_confirmed_equipment_pairs.py` cover this shared code;
`work/feature-regression-registry/verify_sh16_09_equipment_main_edges_v1.py` is the
project regression entry, not a portable skill dependency. Attribute fusion and
cross-view acceptance remain pending until recalculated on those child edges.
