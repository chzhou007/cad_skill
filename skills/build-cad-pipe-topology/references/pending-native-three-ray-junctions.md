# Pending junctions with exact native LINE contacts

A pending interface may already have three graph edges: two main fragments and
a branch. A marker centre slightly offset from their actual native intersection
does not require snapping the pipe to that centre. Read the original LINE
endpoint/interior contacts first, at their existing coordinates.

Use `resolve_pending_native_junctions.py` only for explicitly scoped
`virtual_equipment / pending_source_junction` objects with an independently
replayed main-continuation record. Require its exact main/branch witnesses,
three uniquely sourced rays, opposite through arms, an orthogonal endpoint
branch, matching pipe system/effective colour and source Z. The declared native
pipe circle must contain the actual intersection. Preserve its different centre
as evidence; do not enlarge a global tolerance or relocate any source endpoint.

Equipment/out-of-plane glyphs, reviewed boundaries, unsupported nearby pipe
entities, ambiguous circles, a fourth same-system ray, colour/Z conflicts or
changed owners block this rule. The ordinary crossing and ring-overlap readers
retain their own contracts. Opposite-system contacts remain separate.

Reclassify the proven node using its stable ID and rebuild every incident edge's
endpoint semantics and edge type. Preserve source paths, physical uncertainties,
all actual equipment and component-table bytes. The old pending node is a
versioned snapshot, not a still-current interface. Invalidate branch inventory,
mapping, DN inheritance, length fusion, source comparison and HIL.

```
python resolve_pending_native_junctions.py --source SOURCE --graph GRAPH --devices CSV --policy POLICY --output OUTPUT
```

The policy pins `source_sha256`, `graph_sha256`, `devices_sha256` and selections
of `{node_id, circle_handle}`. The current native entry supports the independently
replayed two-arm-circle parent. `verify_output(OUTPUT)` repeats that complete
parent, native reading and exact output/component checks. This is not a claim
that a family dispatcher, cross-view mapping or published viewer has adopted it.

After a resolved junction changes the local graph, use
`pending_junction_branch_inventory.py --parent-inventory OLD_V2 --junction-run RUN --policy POLICY --output NEW_INVENTORY`.
The policy pins `parent_inventory_sha256`, `parent_receipt_sha256`,
`junction_graph_sha256` and `junction_receipt_sha256`. Independently replay both
parents, prove the complete circle-to-junction ancestry, and reuse the existing
fresh plan-service reader. Preserve the identical replayed axis, unready
equipment and every previously ready service. Produce a new inventory receipt;
never edit the original inventory's graph hash to imply a fresh pass.

`pipeline.py validate-crossview-inventory --inventory-run NEW_INVENTORY` consumes
this mode and the earlier two-arm-circle inventory mode. Require exactly one
fresh check per equipment/service, no physical-value or mapping assignments,
and pending HIL. Downstream matchers still need their own support for the new
inventory mode and independent path proofs; this validator does not make old
correspondences current. Run `test_pending_junction_branch_inventory.py` and
`test_circle_junction_inventory_gate.py` plus the inherited service-reader tests.

Run `test_resolve_pending_native_junctions.py`, inherited native-ray tests and
incident-edge semantics tests. In SH16 09, UT0051/12E9B and UT0119/12E9A have
an approximately1.3045 drawing-unit marker offset; that value is a case result,
not a reusable snapping threshold. Native ray evidence alone must not bypass
the symbol, colour, Z and parent checks above.
