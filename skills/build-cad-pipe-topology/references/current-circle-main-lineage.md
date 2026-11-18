# Current reviewed-circle mains after split or merge

When the original circle reader reports `reviewed main child identity differs`
or `main descendant lacks one source-reviewed split`, use
`rebuild_current_circle_full_plan_DN.py --manifest INPUT --output NEW_DIRECTORY`.
Then run `pipeline.py validate-current-circle-full-plan-DN --batch-run DIRECTORY`.
The ordinary inherited entry and its receipts retain their original algorithms.

Each plan may add `circle_main_lineage_parents`: distinct hash-pinned original
graphs. A native two-arm merge origin uses `role: two_arm_origin`; a split
origin is identified by the actual `split_source_edge.source_graph_sha256`.
Do not fabricate parent snapshots or relabel old hashes as current ones.

`current_circle_main_lineage.py` reuses the original reviewed-circle collector,
its native radial/branch/XYZ checks and its ray reader. A private dependency
namespace extends main membership only. Subsequent splits need one actual
source-bound repair owner, the exact original parent and its exact source-path
interval. Merges reread all original center/rim contacts and execute the original
two-arm normalization; current path, source handles, endpoint identities and
complete archived snapshots must agree. Coincident or wrong-system source rays
remain barriers. Split/merge ancestry is not evidence for a new connection.

Run this over complete checked local plans, preserving ordered F/calibration,
direct labels, through/branch overrides, bounded expert DN scopes and every
unresolved record. The output records current source lineage separately from
DN inheritance roles. Changed inherited values and newly exposed conflicts
must retain their complete source chains, then invalidate affected cross-view
attributes and confirmations. Do not mutate the final fusion graph by hand.

This read-only stage does not change topology, components, physical lengths,
axis values or human acceptance. An arbitrary native geometry/review failure
cannot trigger the lineage fallback. Ordinary crossing, supply/return isolation,
circle radius exclusion and unknown omitted lengths retain their old meaning.

Tests: `test_current_circle_main_lineage.py`,
`test_current_circle_full_plan_DN_gate.py`, and historical full-plan DN,
reviewed-circle, two-arm, wave, scalar/F, calibration and pipeline tests.
SH16 08--10 complete native replay and LF20 backtests remain separate evidence.
