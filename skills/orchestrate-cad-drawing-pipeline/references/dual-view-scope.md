# Dual-view scope

S0 ledger: `assets/sh16-s0-ledger.json`.

Validate it from the repository root:

```powershell
python ./skills/orchestrate-cad-drawing-pipeline/scripts/test_dual_view_scope.py
python ./skills/build-cad-pipe-topology/scripts/test_dual_view_attributes.py
```

`drawing_correct` stays false until a later stage compares the repaired topology with native CAD. The isometric fixture count is a historical lock, not acceptance.

Three records stay separate:

- `plan_topology`
- `isometric_topology`
- `cross_view_fusion`

Fusion cites both local hashes. A change to either local topology marks mapping, diameter inheritance and attribute fusion stale. Diameter and length rules live in `build-cad-pipe-topology/scripts/dual_view_attributes.py`. They do not alter a graph.
