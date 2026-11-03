# Log-driven routing and whole-batch refresh

Use this after expert feedback or a shared rule change. The orchestrator owns applicability, task isolation and evidence collection; specialist engines own interpretation. The planner/receipt validator does not execute arbitrary CAD recognizers or prove semantic completeness.

## Route and bind inputs

Freeze DWG/DXF, source hashes/units/WCS, schedules/legends, base library, center/family/local profiles and the previous released graph. Expert Pair input adds issue ID, original note, dataset/bundle identity, source region and selected objects. Verify those identities against the actual release before attributing a defect to stale data. Archive mismatched feedback as historical evidence and locate its source before applying it.

Inventory neutral source entities first; do not normalize architecture through the pipe parser. Classify drawings, regions and entities with multiple evidence-backed labels. Resolve base library → center profile → family profile → verified local evidence; record conflicts rather than silently choosing a profile. Parameters are references until a source instance/variant, units and provenance are bound. Table quantities are not topology acceptance counts.

| Content | Pipe owner | Building owner | Handoff |
|---|---|---|---|
| Schedules / material tables | Recognition and parameter references | Not applicable absent actual architectural content | Audited library / instance bindings |
| Plant schematic / isometric | Equipment, pipe normalization, ports, T, adjacent edges, edge components | Usually not applicable; explicit adapter may find zero relevant records | Independent completed/partial graph |
| Outdoor / ceiling piping plans | Source-proven piping and equipment | Native walls/openings/columns/grids/dimensions/labels | Separate artifacts sharing source coordinates |
| Architectural / maintenance support | Not applicable absent source-proven pipe content | Source context | Context without a fabricated pipe graph |

Use the SH16 routing table as an example, never classify future projects by sheet number. A schematic viewer invoking a compatibility architecture adapter does not demonstrate that the sheet contains a building plan. Log adapter invocation, applicability and actual extracted content separately. Prepare architecture display transforms from the final graph, then generate the viewer once.

## Expand a fix and account for every task

For a family profile change, rerun every affected family task and a relevant negative family. For shared geometry/parser changes or an explicit request to update all tasks, rerun every applicable pipe family; revalidate schedule/support branches. Do not report all tasks updated after only rebuilding one drawing and packaging unchanged others. Tasks can process independently; serialize local server startup if port scanning cannot bind atomically.

Each task refresh record needs source/profile/code hashes, family and applicability reasons, executed stages, fresh artifact paths/hashes, before/after counts, physical differences, unresolved states, regression outcome and reviewer scope. Keep pending/failed/not_run distinct from rebuilt. An unchanged result needs comparison evidence: source-supported node positions/types/groups, full edge paths and endpoints, equipment/component identities and owners, ports, and pending/disposition changes. Counts or file presence alone are insufficient.

Use `assets/refresh-task-receipt.example.json` as an additional refresh-evidence template. It starts not_run/pending and is not automatically certified by scripts/pipeline.py; keep the stage receipts required by references/contracts.md and attach this evidence to them. Populate actual observations instead of changing template states to completed without execution.

Fresh reconstruction may use different temporary IDs. Retain established IDs only after proving physical equivalence and checking attributes/ports separately; archive the fresh outputs and explicit canonicalization map. Source-derived enrichment can be retained with provenance; do not blindly replace new pending states or changed parameters with an old snapshot. Explain all true changes. Source-supported new baselines may change counts; immutable historical fixtures remain separate.

## Before delivery

1. Pipe owner: discover source candidates independently of accepted graphs; every accepted repair must cover its entire span on final adjacent edges, with no false crossover T and no lost components/ports. Inspect accepted normalization audit records even when a family has no pre-existing gap-coverage file. Missing audit output is not zero candidates.
2. Building owner: validate source identity and coordinate agreement, architectural/MEP exclusions and representation issues. Zero records on a plan with visible building content needs an explicit explanation or pending/failure; zero on a schematic is not a topology failure.
3. Viewer owner: validate declared node systems and default visible nodes as well as edges. Include isolated pending equipment. Inspect actual refreshed viewers and supported native local regions; a complete node table does not prove display coverage.
4. Keep known implementation defects blocking. Insufficient source evidence may remain explicit pending with a reason. Tests and browser checks do not generate human exceptions, close issues or confirm review.
5. Deliver task receipts, raw reconstruction and canonical maps, final source coverage/dispositions, current node-edge/component outputs, browser evidence, test results, pending limitations and version/hash locks. Verify portable ZIPs and actual runtime project identities. Preserve prior releases/services/annotations; each task starts unconfirmed when required by content changes.

## Observed SH16 cases, not universal thresholds

- Pair19 matched v3.7 source/bundle identity: unknown-service tails were filtered before straight-crossing discovery. Fourteen proven gaps were restored in 04, five in the selected region; T count stayed 77. Physical source grouping did not establish supply/return. Old cooling-v1 now reproduces an expected blocker, cooling-v2 is the positive case.
- v3.7.2 reran 8 pipe tasks, revalidated 3 reference/support tasks and regenerated 10 viewers. Exact physical equivalence retained stable official IDs and archived temporary reconstructions.
- 06/07 each loaded 135 nodes but displayed 118 because 17 isolated equipment nodes had no selectable pending system. Viewer v2.8.2 added the pending filter and validation; all 135 became visible without asserting new ports.
- Sparse outdoor source building context and unproven equipment connections remained pending. Do not turn these observations into fixed quantities or thresholds for other centers.

This reference adds future workflow requirements; it does not retroactively certify unrecorded checks in old releases.
