# Independently anchored whole-floor main correspondence

Use `match_anchored_floor_main_network.py` when previously checked equipment
corridors do not cover the connecting main network. This is a separate mapping
mode; do not apply a single linear corridor's `4*N-2` count to a branched or
ringed floor network, or change the historical common-order mapper.

Replay the complete v2 native branch inventory. Equipment labels supply
candidates, while source-checked ownership and one unique service route supply
the fixed T anchors. Require both services, matching floor, no shared T anchors,
and at least three distinct equipment anchors in every independent same-system
main component. Derive the complete same-floor true-T network in both views.
Do not include cross-floor edges or infer physical vertical direction from a
drawing stroke.

Joint colour refinement must resolve every T into one cross-view class.
Unresolved symmetries, conflicting labels, unmatched nodes, parallel edges,
extra branches or incomplete components block this conservative entry. Native
source checks then replay every T and every mapped main path. Ordinary paths
reuse the unchanged LINE auditor; inline spans require the separately replayed
`native_inline_joint_path_coverage` receipt. A structurally unique match alone
is not source proof, physical pipe identity or an expert confirmation.

```
python match_anchored_floor_main_network.py --inventory-run INVENTORY --plan-inline-run PLAN_INLINE --iso-inline-run AXIS_INLINE --policy POLICY --output MAPPING
python pipeline.py validate-source-crossview --mapping-run MAPPING
```

The policy pins `inventory`, `inventory_receipt`, `plan_inline`,
`plan_inline_receipt`, `iso_inline` and `iso_inline_receipt` SHA256, plus `floor`,
`equipment_ids`, `mapping_prefix` and explicit `previous_mappings` (group ID,
path, SHA256). `preserved_axis_attributes` optionally pins an immutable published
attribute snapshot to protect known floor scopes. It is history only, never an
anchor or native source seed. A stale graph/source or a missing prior scope
requires reconciliation rather than relabelling a receipt.

Compare all previous branch/main path snapshots and current owners. Require
old main endpoint correspondence to agree with the full network. Protect named
riser approach segments at their exact original axis indices; a complete named
main must also agree with the new T-to-T mapping. Archive known values without
changing them. Report retained old main paths separately from additional paths,
including named-main paths already known outside the equipment corridor groups.

This stage preserves all local graphs, components, old mapping IDs/receipts and
human history. It assigns no DN, physical length, ports or flow direction.
Native/formal success stays pending/exit2 for plan-attribute reconstruction,
whole source comparison, publication and HIL. Rebuild those later layers on the
new mapping version; do not patch final axis values by hand.

Tests: `test_match_anchored_floor_main_network.py`, historical source/order tests,
`test_anchored_floor_main_mapping_gate.py`, and inline-coverage regressions.
SH16 floor1 has 16 paired equipment anchors, 52 Ts and 56 main paths. Its old
24 corridor main paths plus two named mains leave 30 additional paths; retain
all56 historical corridor scopes and all4 named segments. These are case counts,
not generic topology thresholds. Actual native replay is a separate checkpoint.
