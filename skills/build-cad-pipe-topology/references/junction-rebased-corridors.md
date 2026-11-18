# Fresh corridor correspondence after local circle/T reconstruction

Use `match_junction_rebased_corridors.py` after the independently replayed
`pending_native_junction_rebased_branch_inventory_v1` inventory. This is a
separate mode; historical unique-LINE and whole-floor rules remain unchanged.

Each explicitly scoped group requires at least three independently owned
equipment service anchors, both supply/return services and one unique native
LINE corridor in each view. Reuse the native corridor, mutual main-order and
LINE coverage kernels. Compare all equipment pairs' order, not just adjacent
labels. Preserve every intermediate T and source segment in path snapshots;
do not assign by proximity or by shortest route through a ring.

The source inventory must replay its original local parents and latest native
junction descendant. Each policy group pins its old mapping artifact, floor,
equipment IDs and a distinct mapping prefix. Old mappings provide versioned
history, not current acceptance: native branches, main paths and source coverage
are read anew on the current graph. Require the same old semantic record keys,
local edge IDs, endpoints and snapshots. Any changed path requires separate
reconciliation. Never transfer old human acceptance to the new receipt.

```
python match_junction_rebased_corridors.py --inventory-run INVENTORY --policy POLICY --output MAPPING
python pipeline.py validate-source-crossview --mapping-run MAPPING
```

The policy pins `inventory_sha256`, `inventory_receipt_sha256` and groups of
`{group_id, mapping_prefix, floor, equipment_ids, previous_mapping:{path,sha256}}`.
Keep each group independent: no equipment or local edge writers may overlap.
A complete paired-service group has `4*N-2` records, including `2*N` equipment
branches and `2*(N-1)` intervening mains. Paths may have multiple local edges;
node/edge counts in the two original views need not match.

The actual pipeline validator independently replays the complete mapping,
checks all groups, native main-order evidence and historical lineage, and
returns pending for DN/length reconstruction, fusion and HIL. Current
correspondence does not establish missing continuations between drawing
subviews or whole-floor hydraulic connectivity. In particular, preserve
SH16 09's unresolved subview ends and two existing equipment-owner cases.

Run `test_match_junction_rebased_corridors.py`, inherited source-correspondence
tests and `test_junction_rebased_corridor_gate.py`. Keep stale-source, changed
snapshot, wrong-service, repeated writer and promoted-history negative cases.
Then replay the actual SH16 group output through the formal pipeline. For the
initial09 scope, four historical groups contain30 equipment and112 paths;
paired intermediate-T, named-riser and earlier manual mappings retain separate
contracts. Reconstruct DN/metrics on the new graph before adopting any values.
