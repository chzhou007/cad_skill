# Dual-view scope

S0 ledger: `assets/sh16-s0-ledger.json`.

Validate it from the repository root:

```powershell
python ./skills/orchestrate-cad-drawing-pipeline/scripts/test_dual_view_scope.py
python ./skills/build-cad-pipe-topology/scripts/test_dual_view_attributes.py
```

`drawing_correct` stays false until a later stage compares the repaired topology with native CAD and accepts that class. A recorded comparison that does not accept the sheet leaves it false. The isometric fixture count is a historical lock, not acceptance.

The S2–S8 record is `assets/sh16-s2-s8-record.json`. It keeps plan checks, the isometric inspection, and fusion apart. Mapping stays empty until the same range passes both views. The HIL file `assets/sh16-hil-package.json` is unreviewed and has no human confirmation. Unknown diameter and length stay null.

```powershell
python ./skills/orchestrate-cad-drawing-pipeline/scripts/test_sh16_dual_view_loop.py
```

Three records stay separate:

- `plan_topology`
- `isometric_topology`
- `cross_view_fusion`

Fusion cites both local hashes. A change to either local topology marks mapping, diameter inheritance and attribute fusion stale. Diameter and length rules live in `build-cad-pipe-topology/scripts/dual_view_attributes.py`. They do not alter a graph.
