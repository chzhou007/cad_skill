---
name: visualize-cad-pipe-topology
description: Generate a runnable, portable CAD piping topology viewer and ZIP from completed node-edge results, component audits and source DXF/legend files. Use after CAD graph conversion or when the user requests interactive pipe highlighting, connected-equipment inspection, source-CAD comparison or a reusable visualization package. Supports local exception annotations, whole-dataset human review and portable expert pairs. This skill visualizes existing topology; it does not infer a new graph from screenshots.
---

# Visualize CAD Pipe Topology

Current release: **v2.9.1 HIL**. Read [calculation views and source distinction](references/calculation-views-v25.md) for derived calculation views and authorized aggregate schematics. Interactive drawing and expert Pair export share `public/native-rendering.js`. Pair export must include all relevant native equipment and component geometry intersecting its crop, regardless of the current overlay switches, at the same CAD/topology range and scale. Fallback symbol placement remains explicitly unverified. Run `test_pair_rendering.mjs`, HIL backend/frontend tests and `test_post_drawing_gate.py`, then inspect a real exported Pair and its offline form. Preserve original annotation and expert explanation separately. New dataset identity never inherits prior review confirmation. Unresolved virtual boundaries have unverified logical bindings, not asserted physical equipment ports.

Turn completed CAD topology results into a local application, not a mockup. Reuse the working frontend in `assets/viewer/` and the deterministic builder rather than regenerating UI code or device icons.

## Comparison readiness

Honor graph.metadata.hil_ready=false: allow source inspection and comparison notes, disable Finish Review in the UI and reject confirmation on the backend. This does not prevent internal previews; it prevents algorithm-family gaps being presented as expert-ready results. Preserve known-destination interface semantics and start a fresh semantic dataset without inheriting confirmations.

## Default handoff after CAD conversion

When used with `build-cad-pipe-topology`, treat the viewer as the final conversion deliverable unless the user explicitly requests tables/analysis only. The user's current defaults are **English-only display labels**, source CAD symbols, local use and a portable ZIP. Preserve equipment/node/edge identifiers. Respect a later language or delivery preference rather than treating these defaults as universal restrictions.

Do not wait for an extra request to make the viewer after a successful conversion. This is an agent workflow handoff, not an operating-system watcher: it runs when Codex executes the conversion skill. Do not set up background monitoring, publish CAD data or upload the package without a corresponding user request.

## Inputs and configuration

When a source-derived equipment/material parameter library is supplied, preserve its version/hash and task-local instance bindings alongside the graph. Distinguish candidate reference parameters from effective instance attributes. Show unresolved variants, unit conflicts and missing local DN/range explicitly; do not fill them from a generic type or hide them behind a complete status. Retain provenance to the exact source table and symbol. Parameter enrichment does not change graph connectivity or inherit a reference drawing's human confirmation.

In multi-drawing work, build one viewer per drawing task. Include the stable drawing-task ID in project.id so dataset identity and expert pairs cannot be confused across tasks. Keep each viewer's annotation storage, revisions, expert explanations, exports and Finish Review independent. Finish Review covers only that task's loaded graph, even when it contains multiple floors or systems; it never confirms another drawing task. A batch dashboard may link to each viewer and aggregate processing/review status, but has no batch-wide confirmation action. Shared immutable source legends retain their own hashes without sharing review state. Do not merge drawing graphs unless separately requested as an aggregation task.

Read [references/input-contract.md](references/input-contract.md) before adapting another project's results. The builder needs a graph JSON, per-instance device CSV, normalized main DXF, verified symbol config, and a legend DXF when a configured symbol comes from that drawing. A port CSV is optional when virtual ports are embedded in the graph.

Inspect the completed artifacts and source CAD table before producing `visualization-config.json`. Project name, floors, counts and symbol block names are data/configuration, not constants. Match each used type to an English label and its actual source block or inserted legend symbol. Unmapped types or missing source geometry must be resolved or reported; never substitute a generic icon and claim it matches the CAD table.

`references/sh16-profile.json` is the verified SH16 symbol mapping, not a universal HVAC template. Use it only when those block identities and meanings are verified. Other projects need their own mapping. Drawing-scale normalization and floor enumeration are automatic. Named floors and non-SH16 equipment are supported.

## Build and validate

Use an available Python environment with `ezdxf` (`scripts/requirements.txt`); the generated viewer needs only Python 3 and a browser. Resolve paths from this skill's actual location. Example:

```powershell
python <skill-root>/scripts/build_visualization.py `
  --graph <results>/graph_with_edges.json `
  --devices <results>/edge_device_instances.csv `
  --ports <results>/virtual_equipment_ports.csv `
  --dxf <inputs>/system.fixed.dxf `
  --legend-dxf <inputs>/table.fixed.dxf `
  --config <project>/visualization-config.json `
  --output <project>/output/topology-viewer-v1
```

Omit `--ports` when embedded ports suffice and `--legend-dxf` when no configured symbol uses it. `--project-id` and `--port` override the configured identity/preferred port. Output must be a new versioned directory; the script refuses to overwrite either it or the sibling ZIP.

The builder validates before finalizing the directory and ZIP. Independently recheck a retained package with:

```powershell
python <skill-root>/scripts/validate_visualization.py <viewer-directory>
```

For script/template changes, run `scripts/test_builder.py` with the same Python environment. It tests another project's custom symbols, named floors, tiny drawing units, reconciliation failures and overwrite protection. The source CAD/results stay read-only.

## Interaction and verification

Preserve pipe selection in either view; current-segment vs same-system tracing; connected equipment and source-instance inventory; equipment-to-branch lookup; explicit interface ports; floor/system/layer filters; search; shortest same-system path; pending-degree review; pan/zoom; actual DXF comparison and PNG/SVG/CSV export. Equipment and virtual interfaces are traversal boundaries. Floor filtering affects display, not an existing network trace.

Use original paths, including both sides of omission links. Draw no inferred flow direction. Native drawing units are not certified installed lengths. A degree exception is pending review, not a confirmed fault. Symbols must retain source geometry, filled widths and proportions; graph dots, diamonds and selection halos are separate overlays.

Launch `python <viewer>/serve.py` in a retained process and verify its printed URL. If browser QA is available, check representative pipe selection, network scope, equipment/component lookup, a source comparison, a path query, exports and single-language labels. Use the actual current data; never require SH16 counts in another project's acceptance. Distinguish structural validation from browser verification if a browser is unavailable.

## Deliver

Return the generated directory and ZIP, `validation-report.json`, project config and launch instructions. `start.cmd` opens the local app; `serve.py` selects a free loopback port or reuses only the exact same build. Package identity, input hashes, node/edge/instance counts and symbol sources are recorded. No npm dependency installation or external service is required to view the completed package. Preserve the original conversion report and unresolved topology issues.

## HIL review v2

Generated viewers include exception-only human review, immediate annotations, local persistence, entire-dataset confirmation, paired CAD/topology exports and expert explanation import. Read [references/hil-review.md](references/hil-review.md) when adapting or verifying this workflow. Keep human annotations separate from graph extraction; never mark automatic hints as confirmed errors or ship test attestations as completed review. Preserve source hashes and coordinate transforms; graph revisions do not inherit confirmations. Run the HIL storage, geometry and existing builder tests for changes to these resources.


## Source schematic support v2.2.0 HIL

Render every explicitly configured SVG-safe system ID, including auxiliary and classification-pending systems. Generate system filters, legends and path selectors from configuration. Preserve same-system boundaries through equipment/interfaces. Accept a mixed-source physical junction only with explicit source evidence, incident systems and review-required flags; show that uncertainty without joining hydraulic classes.

Use each equipment node's actual source `symbol_key`, including whole native assemblies and source-contour equipment, with `equipment_symbols` in the builder config. Show native source-port counts and completed-port edges when supplied. Do not replace a tank or manufacturer assembly with a generic chiller icon.

For partial extraction, retain `pendingSourcePaths` as a read-only source overlay, show a persistent partial banner and provide an extraction coverage report. Finish Review applies only to the loaded graph and explicitly excludes unresolved source geometry. It does not turn extraction gaps into accepted topology. Reject unproven mixed-system junctions. Run `test_builder.py`, `test_new_drawings.py`, `test_hil.py`, and `node --test scripts/test_hil_frontend.mjs` after modifying shared assets.


For source instrument/component fidelity, accept `componentSourceGeometry` (device_name and native source paths with fill intent). Convert it with the same source transform as CAD, preserve sourceGeometry per instance, and enable `display.components=true` for schematic review profiles. Match geometry to the instance audit; do not create uncounted fake instances. Keep `related_edge_ids` as measurement context, not extra hydraulic connectivity. Selecting both owning edges counts one source instance once. Unresolved source-terminal nodes must retain their explicit pending label and stop tracing. Run test_system_boundaries.mjs as well as the prior frontend suite.

Native geometry may also be generated directly from the standard per-instance CSV source_handles and main DXF, without a drawing-specific adapter. Preserve source instrument tags. Include unresolved source terminals and source-system conflicts in automatic topology hints; these never create human error records. Fit the whole native geometry when locating a component.


Instrument completeness v2.2.1: preserve source_head_status/handle/tag independently of assignment_status. Render a pending head association in amber and include a componentReview automatic hint that locates the instance. An assigned sensor body with pending_no_proven_head is partial recognition, not a complete group. Node and component hints never create human errors or review attestations.

## Post-drawing quality gate v2.3.0 HIL

v2.3.2 HIL: preserve sourceTaggedHeadCoverage from conversion. Independently discovered source heads remain explicit pending records if no component is proven; a represented head missing from exported source handles blocks delivery. Compare the selected edge's component inventory and actual CAD region, including exploded primitives on layer 0 or secondary drafting layers. Selection filtering must not be confused with failed recognition. This coverage is limited to supported tagged families, not an exhaustive CAD semantic audit.

Read and execute [references/post-drawing-quality-gate.md](references/post-drawing-quality-gate.md) after generation and before a checked delivery. The builder now emits quality-gate.json and blocks known source-geometry mismatches. Complete same-range visual inspection, fix shared rules, regenerate and recheck; machine success alone remains AWAITING_VISUAL_CHECK. Render equipment display_source_handles at native position/scale/rotation while keeping selection halos separate. Final PASS_WITH_PENDING states technical scope and source uncertainties and does not confirm human review. Ship the final gate evidence and refresh the archive after it is recorded.

v2.3.1 HIL: Nested equipment and components may supply display_source_chain. Validate actual parent INSERT/child ownership and apply all ancestor transforms. A component's source_top_handle may name an entire parent assembly: resolve the unique actual child block identity at its audited WCS insertion point; do not display the whole parent at every component. The gate rejects a declared component whose supplied INSERT identity names another block. Preserve technicalPending source-coverage records and absent optional CSV handles as explicit unverified states. Omission-anchor legacy layouts without per-instance native placement remain explicitly unverified; do not move equipment to a table or invent native handles to suppress a warning.

## Hydraulic equipment scope v2.6.0 HIL

Show physical equipment even if its schedule or resistance parameters are missing. Equipment details use hydraulic_model to distinguish inclusion in a calculation graph from source topology and show required resistance parameters without assuming zero. Retain source ports, separate service classifications, native geometry and parameter references. A pump represented as an edge attribute is still equipment; absent pump-node count is not loss. Calculation scope must not silently remove a large auxiliary device or its connections. Display unresolved source equipment ports honestly and do not turn them into asserted water paths. Run test_hydraulic_properties.mjs with the backend/frontend suites and inspect restored native equipment in both main and Pair views.

## Architectural context

Read [building-context-v27](references/building-context-v27.md) for architectural plans or missing walls, openings, room labels, grid attributes and dimensions. Generate a separate source context sidecar, preserve world coordinates and original text, and run the architecture representation and actual-browser gates before delivery.


## Pipeline ownership contract

For batch or mixed-family work, use sibling `orchestrate-cad-drawing-pipeline` v1.0.4 as the workflow entry point and read its references/contracts.md. The orchestrator schedules this skill; do not invoke the orchestrator recursively from a branch. Preserve task ID, source SHA256, units/WCS, profile hashes, stage status and artifact evidence. Use base library + center profile + family profile + verified local evidence; unknown/conflicting semantics stay pending. Branches own separate outputs and never overwrite another branch's graph, context or review records. HIL is error-only with whole-task confirmation, independent per drawing.

Prefer --building-context ARCHITECTURE.json from the architecture stage. It must match the final graph source hash and display transform; prepare it using the final graph transform, not screen coordinates. Direct builder calls without this argument retain a compatibility extraction adapter using the locked building-owned implementation; manifests explicitly identify that mode. No topology is inferred by the adapter. New review fingerprints cover architectural semantics and supplied effective parameter artifacts, excluding display-only template/style changes.

Building dependency v2.8.1 HIL: use the locked building owner v1.1.1; explicit valve/instrument layers must not be rendered as architectural doors merely because their Chinese names contain the door character. Rerun building and Pair regression after syncing the canonical owner.

Node filter coverage v2.8.2 HIL: validate declared node systems as well as edge systems. Isolated equipment with explicit pending source service must have a visible English PENDING filter even when no edge uses that service. Do not hide unresolved equipment or invent connections. Unknown named services require an explicit mapping. Regress the real orphan-node filter omission in test_builder.py, and verify all loaded nodes appear with all filters enabled.

## Log consolidation (2026-10-27)

Read [default visibility and review handoff](references/default-visibility-handoff.md) for batch refresh, isolated pending equipment and architecture/parameter integration. Instruction/handoff revision only; the validated geometry/rendering algorithms from the previous release are retained.

## Portable startup v2.8.4 HIL

Ship the standard-library launch_review.py and guarded start.cmd from assets/viewer. Check Python 3.10+ using py then python, retain failure text, and write startup diagnostics instead of closing silently. Batch distribution should copy this entry to its root: default to a selected single drawing, with explicit ALL for the existing dashboard. Distinguish backend working sets, source SVG size and actual browser memory; none alone proves a remote crash cause. Preserve annotations when applying startup-only patches. Diagnose in the fully extracted writable package; do not require CAD conversion dependencies for review. Run test_portable_launcher.py and the builder/HIL suites, plus an actual Windows start.cmd --check-only smoke check. A startup fix must preserve graph/source/component identities and review data.


Nested MEP source retention v2.9.1: cad_reference_context may supply retained_mep_chains (source_chain, reason) for actual equipment embedded in a reference otherwise rendered from an architecture sidecar. Resolve the real parent/child chain and native geometry; include it in CAD and Pair source vectors. The sidecar remains architecture-owned. Equipment native sourceGeometry still uses display_source_chain at source scale. Preserve readable source captions as sourceAnnotations. Never let an architecture-only exclusion erase equipment from the source comparison.
