# Reuse native floor-marker evidence in a complete source batch

`native_level_evidence.py` and `cross_floor_axis_diagnostic.py` are inherited
capabilities. SH16's explicit three-marker policy already verifies 一层 ±0.000,
二层 4.800 and 三层 9.800. Do not claim those symbols or their verification as
a new implementation. Keep that original policy and every historical result.

The added capability discovers policies for the existing verifier:

```
python discover_native_level_markers.py --source SOURCE.dxf --output NEW_RUN
python pipeline.py validate-native-level-discovery --batch-run NEW_RUN
```

Strict native decoding precedes discovery. Find supported modelspace TEXT floor
captions and decimal elevation text with the original LINE baseline, symmetric
arrow arms and horizontal leader contract. Group independent stacks separately,
then run `native_level_evidence.verify` unchanged. Native policy handles are
discovered, not a handpicked per-project allowlist. Duplicate geometry or floor
captions, conflicting stacks and missing symbols remain explicit pending items.
Room numbers and DN suffixes are not datum markers. This reader keeps the
original scope: unsupported rotation/negative OCS, MTEXT, nested/proxy symbols
and nonconsecutive floor stacks require separate evidence; no matches do not
prove a whole drawing has no elevations.

The numeric datum differences retain the original source unit caveat. They are
not pipe lengths, pipe-end heights, pipe floors, shaft identity or HIL acceptance.
Replay actual source LINE evidence and the existing cross-floor diagnostic for
the current graph before comparing drawing offsets. SH16's current eight mixed
paths yield six datum-aligned drawing candidates and two other offsets; those
eight physical lengths stay unknown. Drawing alignment alone must not convert
the six candidates into installed pipe lengths.

`test_discover_native_level_markers.py` requires the original policy and verifier
result to remain exact; it guards ambiguous geometry, unsupported transforms,
ordinary text and independent stacks. `test_native_level_discovery_gate.py`
guards the source-only scope. Run inherited native-level/cross-floor tests and
all applicable registered suites. This source-context update does not require
rewriting plan topology, DN results, cross-view correspondences or expert replies.
