# Two-arm circle continuations before cross-view mapping

A drafting circle can join two visible pipe arms without adding a T. A pipe
may end at the circle rim while its continuation starts at its centre. The
ordinary three-ray T reader does not cover this case; proximity snapping alone
also loses the marker and source-length evidence.

Use `normalize_two_arm_circle_continuity.py` on an explicit native marker scope.
Its collector requires exactly two radial centre/rim LINE contacts, matching
pipe systems and effective colours, qualified planar Z, unique unresolved graph
endpoints and a straight or right-angle continuation. It supports planar
rotation, reflection and negative OCS. The pipe owners determine the system;
a misplaced circle layer does not change both pipe owners.

Do not apply the rule to ordinary crossings, three/four-arm junctions,
equipment/out-of-plane glyphs, reviewed boundaries, coincident marker copies,
source Z disagreements or additional nearby unsupported pipe geometry. Those
cases need their own source evidence. This entry never invents a third arm.

Reconstruct the complete chain of affected edges together: two circles can
share the same intermediate fragment. Preserve old edges as scoped lineage,
publish old-to-new IDs, retain all unrelated objects and reassign every inline
component exactly once. The connector inside a marker is drawing evidence;
raw `attribute_paths` remain separate and its physical length stays unknown.
Recompute endpoint roles and invalidate source comparison, T/port checks,
branch inventory, cross-view mapping, DN/length fusion and HIL before adopting
the new local graph. Old answers remain history rather than new acceptance.

```
python normalize_two_arm_circle_continuity.py --source SOURCE --graph GRAPH --devices CSV --policy POLICY --output OUTPUT
```

The policy pins `source_sha256`, `graph_sha256`, `devices_sha256` and selected
`circle_handles`. The current standalone owner independently replays the
confirmed-sideview ownership parent and its component table. Its
`verify_output(OUTPUT)` repeats parent/native collection and exact output checks.
This standalone entry does not claim that a family rebuild, cross-view source
gate or viewer already consumes the new root; record those integration stages
separately and keep publication pending until they pass.

The formal ceiling entry accepts `--plan-circle-continuity-map MAP.json`.
Each task maps to `{continuity_policy: POLICY}` and, optionally,
`pending_junction_policy`. `plan_circle_continuity_family_stage.py` owns the
current task graph, component table and output directories; policies cannot
override them. It rebuilds and independently replays each selected stage before
refreshing the final graph summary. The source-comparison dispatcher consumes
the most recent continuity/junction root before its retained ownership ancestor.
Native full-family equality, the new graph's branch inventory and cross-view
mapping remain separate required evidence; merely adding this flag is not a
completed full-family regression.

Before rebuilding correspondences, use `two_arm_circle_branch_inventory.py`
with the original complete v2 branch inventory and the circle reconstruction.
It independently replays both parents, checks their exact source/graph ancestry,
and reads every plan service again against the new graph hash. Retain axis
evidence only on its identical replayed inputs. A formerly ready service that
now fails blocks adoption; unchanged geometry alone does not validate an old
graph-bound receipt. This inventory assigns no mapping or physical values.

```
python two_arm_circle_branch_inventory.py --parent-inventory OLD_INVENTORY --circle-run CIRCLE_RUN --policy POLICY --output NEW_INVENTORY
```

The inventory policy pins `parent_inventory_sha256`, `parent_receipt_sha256`,
`circle_graph_sha256` and `circle_receipt_sha256`. Run
`test_two_arm_circle_branch_inventory.py` for readiness-regression, caption,
parent-mode and acceptance guards, then independently replay the real output.

SH16 09 has six scoped examples, including one marker on the opposite pipe
layer. They reconstruct four paths from ten old edges, preserve168 components
and retire12 source-proved temporary endpoints. These are case results, not
generic thresholds. Run `test_normalize_two_arm_circle_continuity.py`, current
native parent replay and affected historical tests. Never use a node-count
decrease as evidence of correctness.
