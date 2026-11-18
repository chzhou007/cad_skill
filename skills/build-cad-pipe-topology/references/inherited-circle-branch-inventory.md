# Versioned inherited-circle branch inventory

`inherited_circle_branch_inventory.py` extends a complete `source_endpoint_branch_inventory_v2` inventory after independently replaying that exact parent. It adds source readers for explicitly selected expert/calibrated circle frontiers; it does not change either graph, add a connection or establish a cross-view match.

```
python inherited_circle_branch_inventory.py --parent-inventory ... --policy ... --output ...
python pipeline.py validate-crossview-inventory --inventory-run ...
```

The receipt mode is `inherited_circle_endpoint_branch_inventory_v3`. The preserved base `inventory_mode` and exploded-endpoint evidence still describe the v2 parent; the new extension has its own mode, records, implementation hashes and input receipt. Do not overwrite or relabel the historical entry.

The policy pins `parent_inventory_sha256`, `parent_receipt_sha256`, `plan_source_sha256`, `plan_graph_sha256` and nonempty unique `selections` of `equipment_id`, `system`, `node_id`, `edge_id`. Legacy edge-only circles additionally need the external issue/control binding described in [inherited circle evidence](inherited-duplicate-circle-source-evidence.md).

Each selected service must previously be pending on that same unique branch-to-T route. Recheck current calibrated ownership snapshots, source-system and floor agreement, inherited circle rays and all native path pieces. Replay every excluded opposite-system crossover through the existing source crossover kernel. For the older gap schema without IDs/hashes, build an explicitly current private metadata projection and hash it; keep original gap metadata unchanged and never impersonate the original historical artifact. An unexplained extra path, moved crossing, changed owner or claimed connector blocks the extension.

Keep unselected branches, axis source evidence and all previously ready services byte-equivalent. Recompute equipment readiness from both services in both views; one newly checked branch cannot promote an incomplete equipment pair. Physical ports, unshown connectors, installed lengths, mapping and HIL remain unknown/pending.

Use `test_inherited_circle_branch_inventory.py`, `test_inherited_circle_inventory_gate.py` and the registered historical/new regression union. Then run native production and independent root reconstruction. The root is never memoized: within one process, only the complete v2 child verifier may reuse its freshly checked dependency closure. Standalone verification always replays it. Technical success remains pipeline `pending`/exit 2 for mapping and human acceptance.
