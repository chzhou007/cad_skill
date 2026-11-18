# Publish existing attribute-entry compositions

Use after the complete native batch in
[inherited branch attribute entries](../../build-cad-pipe-topology/references/inherited-branch-attribute-entries.md)
has replayed the current published parent and its original source owners.

`refresh-inherited-branch-attribute-viewer` adopts only new records from that
batch; `validate-inherited-branch-attribute-viewer` independently replays it.
Arguments are `--parent`, `--output`, `--proof`, `--parent-provider`,
`--templates` and `--port`; validation uses `--verify-output`.

The new context is `inherited_branch_attribute_entries`. Keep every previous
context byte-equivalent as data. Match the exact native and rendered source
namespaces, edge endpoints, system, floor and complete path partition.
Normalize the newly assembled context through the canonical JSON boundary
before comparing actual Node values: fresh native normalization evidence may
contain tuples, while manifests and exports contain arrays. Preserve the full
nested source proof and never clear a mismatch by omitting those fields.

- Horizontal domains inherit the independently owned floor-plan main DN.
  A partially classified main receives only its original horizontal domains.
  Its unknown direction is retained, so it cannot receive a whole-edge DN.
- Retained vertical domains must match their old drawing11 CSV evidence by
  path index, segment index, scope, system, source hash and DN.
- Newly recovered vertical domains have a separate source kind and separate
  CSV fields. They require the independently replayed drawing11 annotation/T
  owner and original semantic normalization proof. Do not pretend these new
  domains existed in `axis_rule_vertical_DN_segments_json`.
- Fill an unknown whole physical DN only when all actual domains, excluding
  the proved marker display stroke, are covered and agree. A shared value or
  equal count does not prove that partition. Preserve old known scalars.
- Semantic normalization establishes connectivity; it does not certify raw
  LINE coverage or a measured gap length. Keep that length null. No new
  length, device identity, remote mapping, component or graph edit is allowed.

Nine provenance columns append to the old export prefix. Verify the actual
Chinese properties, both complete supply/return CSVs, all original columns,
component conservation and unchanged annotations. Source success, publication,
actual browser verification and human acceptance are separate states.

After exact branch qualification, do not interpret old incomplete raw-LINE
coverage as an unresolved logical connection. Use the checked context to show
local main-T/branch evidence, still-unassigned terminal identity and pending
human acceptance separately. Keep the original raw coverage/unknown length
record; unknown, stale, partial-main and wrong-system contexts retain the old
display. This display refinement writes no CSV values or connectivity.
Apply that same checked display rule to the previously published plan-main
branch context as well as the new entry context; both must pass their own
original complete-domain readers. Do not leave older qualified branches with
the old false-pending header. Include all shipped UI module hashes in the new
bundle identity so a display evidence change cannot retain an earlier review
bundle identity, even when the port and numeric values are unchanged.

SH16 regression: the complete28-branch cohort retains the old25 source
payloads. E0224/E0330/E0582 are new complete DN candidates; E0303 keeps its
unknown first direction and exposes only three horizontal DN domains.
E0582's two vertical domains are owned by11; their normalization does not
create a physical length. These IDs locate fixtures, not algorithm triggers.
