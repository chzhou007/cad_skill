# Pipeline and ownership contracts

Four independent versions: pipeline/schema, engine/skills, symbol base library, center/family profiles. Lock actual files by SHA256; a version string alone is insufficient. Unknown profile or missing dependency means pending/failed, never a default SH16 configuration.

| Stage | Owner | Dependencies | Owned output |
|---|---|---|---|
| source | orchestrator + read-only parser | frozen CAD | neutral inventory / issues / WCS source references |
| parameters | pipe skill recognition phase | source | reference library and source-instance bindings |
| topology | pipe skill family engine | source, parameters | nodes, edges, ports, components, geometry audit |
| architecture | building skill | source | architectural sidecar, raw source labels and English aliases |
| source_comparison | pipe skill | topology, parameters, applicable architecture | graph-bound comparison receipt, native overlays, issue-family dispositions |
| visualization | viewer skill | applicable topology and architecture; parameters | aligned rendering, local HIL / Pair |

Architecture-only/support drawings can deliver source-context artifacts without a pipe graph. Schedule-only drawings can deliver parameters without graph/viewer. Applicability needs explicit reason and source evidence. Mixed region/entity tags are retained; a family profile configures the engine rather than replacing the task identity.

Each task plan binds source SHA256, task ID, tags and family evidence. Stage receipt: `status`, `reason`, `evidence`, `artifacts`. Completed stage additionally has `source_sha256`, `task_id`, `owner` and each artifact's task-relative `path`, `sha256`, `role`. A receipt cannot assert completion with no artifacts. Artifacts may not escape the task output directory. An artifact path has one writing stage; other branches reference it without claiming ownership. Architectural receipts may not own graph/node/edge/port/component files. For graph/building artifacts include identical WCS `coordinate_contract` values (`frame: WCS`, declared `units`, source hash). The display transform is separately validated by the viewer; do not use screen coordinates as physical evidence.

Plan configuration: `project_id`, optional `profile_files` (list of immutable paths), and `tasks` list containing unique `task_id`, `source`, `family`, nonempty `evidence`, `tags` list. Paths resolve relative to config. Supported families: schedule, plant_schematic, outdoor_plan, ceiling_plan, isometric, architectural_support. Unknown family leaves routing pending and prevents final-ready output. `tags` can add pipe, equipment, architecture and parameters branches to a mixed sheet. Keep original tag evidence separately when finer region/entity classification is needed.

Contract validation checks receipts and hashes, dependency completion, applicable branches, ownership, source identity and WCS agreement. It is not a replacement for source coverage, physical topology, browser or expert checks. It cannot certify all CAD content recognized. These specialized checks and browser evidence must accompany the completed stage artifact. Never use an empty success JSON as proof.

Merge order is not conflict resolution. Source entity references may occur in multiple branches, but physical role candidates and exclusions must retain their evidence. Material/profile disagreements do not change an already proven pipe connection. Resolve explicit local source evidence over a generic template; unresolved contradictions stay pending. A profile must not override ownership or human-review policy.

Review semantics: task-wide HIL is tied to graph/source, effective parameters and building-context semantic fingerprints. Building source positions, categories, original labels and display aliases count as review content; projection scale, line colors, template code and viewport do not. Legacy manifests retain old identity only when no new semantic fields are present. Historical annotations remain under their original dataset folders; new content starts unconfirmed. No automatic remapping to changed graph IDs.

Effective parameter input to viewer: a JSON object with `task_id` matching `project.id`, `source_sha256` matching the source DXF, and task-local effective parameters with units and provenance. Keep unresolved/reference states explicit. `--parameters` copies and fingerprints that artifact. A path/hash mentioned in prose alone does not bind it to review identity. Geometry-independent schedule/library source hashes also belong in its provenance. Pure presentation config remains excluded from review identity.

Final visualization depends on source_comparison completion. Its receipt uses role comparison and is checked by scripts/source_comparison_gate.py. Evidence files must be task-local, hashed, current for the graph and explicitly dispositioned; algorithm blockers cannot be reclassified as expert ambiguities for convenience.


Source-scoping handoff: before restricting a building reference, inventory nested MEP/equipment descendants independently of architectural categories. An excluded parent INSERT may contain a whole floor. Exclusion from the architectural sidecar is not exclusion from topology or source-CAD rendering. The pipe branch owns source-backed equipment instances and ports; hand off source chains, native transforms, hashes and disposition of every MEP candidate family. Source comparison must detect a zero-equipment graph against native equipment bodies and block that implementation defect before HIL. Unknown schedule variants and unproved remote ports remain separate from local equipment ownership.
