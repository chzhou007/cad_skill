# Source coverage through already identified inline joints

Use `native_inline_joint_path_coverage.py` when an existing graph edge has
separate source pipe paths, or an axis path explicitly includes an inline
marker span that has no native pipe LINE witness. Do not relax the historical
single-LINE auditor or classify an arbitrary gap as a flexible joint.

Pin the original source, current graph, component CSV and preserved
source-calibrated template policy. The template must match its original
fingerprint and the supported two POINT, two LINE and one SPLINE definition.
Recheck native transformed XYZ points and bar midpoints, unique outward
same-system pipe contacts, exactly one inventory and graph component owner,
every ordinary pipe segment and one endpoint-bounded private pipe/joint chain.
Preserve raw path indices and all original graph objects. Rotation and mirror
are accepted only through their actual transformed source geometry.

Separate paths need source-qualified markers at every break. A marker span
already encoded in an axis path must match exactly those two native contacts;
another missing or competing source segment stays unresolved. Do not flatten
Z, widen tolerance, infer a connection at a crossing, discard a fragment or
use a nearby marker to explain a different gap.

```
python native_inline_joint_path_coverage.py --source S.dxf --graph G.json --inventory C.csv --template-origin CALIBRATION.json --policy P.json --output AUDIT
python pipeline.py validate-inline-joint-path-coverage --coverage-run AUDIT
```

The policy pins `source_sha256`, `graph_sha256`, `inventory_sha256` and
`template_origin_sha256`, plus `block_name`, `block_fingerprint_sha256` and
explicit unique `edges`. The preserved template origin supplies calibration
data, not workflow instructions. The independent verifier reconstructs the
complete audit. Formal success is `pending` / exit2 with `source_replay=passed`;
it does not establish a cross-view mapping, a repaired graph or HIL acceptance.

The ordered pieces are private evidence, never new physical nodes or edges.
Report source-drawn pipe length separately; exclude all marker spans and keep
joint/whole installed lengths unknown. Keep the old flexible-joint reconstruction,
component conservation, strict pipe coverage and downstream mapping gates.
Test `test_native_inline_joint_path_coverage.py`, existing native path and
flexible-joint tests, and `test_inline_joint_path_gate.py` before actual source
and formal-entry replay.

SH16 one-floor evidence: four withheld main pairs have six independently
identified joints in each view. This is a case inventory, not a universal
count requirement. The remaining main candidates still require formal
multi-anchor correspondence and attribute reconstruction before publication.
