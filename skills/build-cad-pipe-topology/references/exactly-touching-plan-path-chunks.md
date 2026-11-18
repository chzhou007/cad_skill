# Exactly touching chunks of one existing plan edge

An existing same-floor edge may store one continuous pipe as multiple
`attribute_paths`: one ends exactly where the next begins. The historical
single-path coverage/metric entry rejects this representation. That rejection
does not prove a CAD gap, a disconnected pipe or a new question for an expert.

Use `native_touching_plan_path_chunks.py` as a separate reader. Require one
existing edge, one system, existing same-floor endpoints, finite nonzero
segments and exactly equal adjacent endpoints in their recorded order. Join
only a private attribute projection. Keep each original path/segment identity
and the public graph byte-for-byte unchanged. Do not snap, reverse/reorder
chunks, recover even a tiny gap, connect different edges or create nodes.
Reject overlapping/retraced pieces, detail domains and wave/omission scope.

Run the inherited native same-system LINE coverage audit on that private
projection. Every piece needs a unique source witness. Reuse the original
floor-plan millimetre unit check, including native title/window and two
independent native dimension directions, then the original projection-length
kernel. Translate every measured piece back to its original path/segment ID.
The result is an audited XY drawing route; physical whole-edge/connector
length and connectivity acceptance remain unknown. The API does not select DN
or establish cross-view correspondence.

Keep real cross-pipe drawing gaps, crossovers, wave omissions, circle interfaces
and ordinary intersections in their existing features. Do not replace those
rules or change historical entry files to accept arbitrary multiple paths.
The additive reader avoids invalidating unrelated frozen source receipts.

The entry writes `touching-path-evidence.json` and an input/code-bound receipt.
`pipeline.py validate-touching-plan-chunks --scope-run ...` independently
replays it and returns pending/exit 2 for topology acceptance, mapping, DN,
fusion and HIL. Downstream named-riser segment mapping must consume this scope
explicitly; do not count this geometry evidence as a formal mapping.

Run `test_native_touching_plan_path_chunks.py`,
`test_touching_plan_chunks_gate.py`, inherited native coverage/metric tests,
wave-convention and crossing negatives. SH16 10 E0026/E0012 are two source
examples. Their join distance is zero; no extra pipe length is inferred.
