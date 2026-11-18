# Complete local-plan DN before cross-view selection

Use `rebuild_full_plan_DN.py --manifest INPUT.json --output NEW_DIRECTORY`, then
`pipeline.py validate-full-plan-DN --batch-run NEW_DIRECTORY`. This additive
entry reads every current local plan edge after independently replaying its
reviewed owner, drawing-gap or wave/main-cohort producer. It does not rebuild a
cross-view inventory merely to read a local DN label.

## Common rules

- Inventory readable native annotations on the whole plan before selecting
  cross-view paths. Otherwise a DN seed outside an already matched corridor is
  lost even when its T-connected descendants are relevant.
- Reuse strict scalar/native-LINE attribution and exact source-path coverage.
  Classify compound/named DN and unconsumed leader conflicts; do not choose the
  nearest pipe across competing services. Nested/F/other unsupported source
  domains retain their specialized entries and require explicit integration
  before being claimed as covered by this batch.
- Replay each current native T through the applicable historical provider.
  The unique opposing pair is the through main; it is not hydraulic direction.
  DN propagates through that pair and defaults into an unlabelled branch.
  A direct DN anywhere on the branch's checked through-connected region
  overrides its incoming parent default. A branch value never backflows into
  its parent main. Conflicting parent defaults remain unknown with all lineages.
- Unknown T, annotation and path scopes are barriers. A source-provider schema
  gap is a code/entry task, not a newly discovered disconnected pipe or a reason
  to ask the expert to confirm the same connection again.
- A reviewed bounded DN scope stays bounded. The first-floor DN450 answer is
  not a new native annotation to broadcast beyond the two reviewed mains.
  Rebase review only onto unchanged native paths, services and equipment owners.
- The reviewed third-floor 31–36 group has DN150 on the drawn plan branches;
  DN80 belongs to the distinct axis equipment drops. Preserve both extents,
  unknown transition position and connector length. Do not fill a whole axis
  edge with one of these values.

## Component captions

`discover_native_component_DN.py` enumerates existing exact-reader inputs for
`金属软管 / DN…`, including a fan joined at either underline endpoint. Reuse the
native block fingerprint, two POINTs, full shared-hub star and unique canonical
component ownership. An arrow can terminate on the exact native two-port axis
interior; this proves annotation ownership, not a physical connection or port.
Record the WCS target and its axis fraction. Rotation, mirroring and native Z
are checked. `余同` does not authorize broadcast to unpointed symbols. Component
DN is never a pipe seed, resistance or installed length.

## Manifest and outputs

`plans` contains distinct integer `floor` values, `parent_mode`, and hash-pinned
`inputs.source`, `.graph` and `.devices`; graph/component names are canonical.
The inherited-circle reader can receive `.circle_policy`. Optional reviewed
main boundaries reference their independently replayed producer; reviewed
horizontal scopes pin original question definitions, raw/validated reply,
original plan/attribute scope, Pair and large locator. No free-form review seed
is accepted by the formal entry.

`full-plan-DN-results.json` contains one record per plan edge, native annotation
and path evidence, current T roles, source-provider exceptions and reviewed
scopes. `full-plan-DN-receipt.json` pins input and implementation hashes.
`--verify-output DIRECTORY` independently rereads source evidence and compares
the complete payload; the pipeline gate recomputes counts and rejects filtered
inventories, duplicate IDs, fabricated values and false human acceptance.

The batch is read-only: topology, components, physical lengths, axis values and
expert acceptance remain separate. After changing a local connection, replay
the local owner and recompute DN, correspondence, fusion and affected HIL. Route
only remaining semantic conflicts to grouped review after deterministic reader
gaps have been processed.

## Regression

Run `test_full_plan_DN_source.py`, `test_full_plan_DN_inheritance.py`,
`test_component_DN_underline_end.py`, `test_reviewed_horizontal_DN_scopes.py` and
`test_full_plan_DN_gate.py`, plus registered inherited scalar/F, calibrated DN,
through-T, component, circle/wave, metric and pipeline suites selected by the
feature registry. Native SH16 08–10 and later LF20 backtests are separate from
unit tests and human acceptance.
