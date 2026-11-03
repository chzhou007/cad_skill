---
name: build-cad-pipe-topology
description: Convert HVAC, MEP, or P&ID piping drawings in DWG/DXF form into an auditable node-edge graph with equipment nodes, physical T-junctions, omission-symbol interfaces, and inline devices aggregated as edge attributes. Use for CAD topology extraction, schematic simplification, false/missing T diagnosis, exploded-symbol recovery, equipment reconnection, edge inventory generation, topology visualization, or regression/alignment testing against the bundled SH16 case.
---

# Build CAD Pipe Topology

Current release: **v1.14.0**. Read [expert roundtrip and calculation scope](references/expert-roundtrip-v18.md) when applying expert feedback or composing an explicitly authorized calculation aggregate. Read [shared normalization and source coverage](references/normalization-v17.md) for every rebuild or topology repair. Use the shared family entry points, final-edge coverage ledger, stable ID reconciliation and component-conservation gate before visualization. Retain historical fixture results separately from a source-justified new baseline.

Treat CAD geometry as evidence of physical connectivity, not as topology by itself. Preserve traceability from every node, edge, and inline device back to source geometry.

## Select resources

- Read [references/methodology.md](references/methodology.md) before changing extraction logic or classifying ambiguous CAD geometry.
- Read [references/output-schema.md](references/output-schema.md) before creating or validating deliverables.
- Read [references/alignment-case.md](references/alignment-case.md) when running the bundled SH16 benchmark or changing this skill.
- Run `scripts/validate_alignment.py` after any material rule change.

## Semantic reconciliation before expert HIL

For every new extraction or repair read [source semantic reconciliation](references/source-semantic-reconciliation.md). Distinguish equipment, native glyph assemblies and known-destination interfaces; run native source comparison and consume recurring algorithm defects before expert HIL. Use the shared reconciliation helper; candidate grouping never authorizes a hydraulic merge. Export the graph-bound comparison receipt.

## Execute the workflow

Before extracting topology, build the equipment/material parameter foundation from the current source schedules and legends. Read [references/equipment-parameter-foundation.md](references/equipment-parameter-foundation.md). Identify equipment and inline-component classes, actual CAD symbol prototypes, parameter fields/units, schedule variants and source references. Bind drawing instances to those references with explicit ambiguity and missing-value states. A shared tag pattern or nearby table row is not enough to select an equipment variant; a list of scheduled diameters is not an instance diameter. Keep inline-device parameters on edge components. Reference-table quantities are not graph acceptance counts.

For a multi-drawing delivery, use one independent processing task per drawing. Give each task a stable task ID, its own graph artifacts, validation report, viewer, annotation storage and human review scope. Node/edge IDs are local to that task. A batch dashboard aggregates task status only; it does not merge graphs or provide a shared review confirmation. Independent tasks may run concurrently when authorized, with isolated output and temporary directories. One failed or pending task must not block unrelated ready tasks.

Immutable source files, material tables and verified symbol libraries may be shared as versioned references with hashes. A shared legend does not create a topological connection or share human review. Do not deduplicate or connect networks across drawings unless the user explicitly requests a separate aggregation task. Keep reference-only drawings as their own tasks and report topology applicability explicitly; never fabricate an empty accepted graph or mark a reference task reviewed automatically.

1. Preserve the source drawing. Copy DWG inputs into the project and convert them to DXF locally. Prefer a normalized ASCII DXF for deterministic parsing.
2. Inventory layers, nested blocks, primitive entities, labels, line colors, drawing bounds, detail regions, and scale. Count `ARC`, `SPLINE`, and polyline bulges on pipe layers because a drafting crossover may be encoded as a display-only curve. Render the source once for visual comparison.
3. Define the graph ontology before detection:
   - collapse each non-valve physical equipment item to one equipment node;
   - create a physical node for a source-supported three-way pipe contact; preserve mixed-source classification as explicitly pending, as specified below;
   - keep valves, vents, flexible connectors, filters, gauges, and thermometers as edge attributes;
   - convert an unbound omission symbol into a virtual equipment/interface node with explicit ports.
4. Normalize geometry conservatively before finding T nodes:
   - trim only short dangling overshoots that cross a same-system main;
   - fold valve and automatic-air-vent display legs back to their owning elbow/edge;
   - reconnect a short collinear drafting gap when it crosses another pipe, but keep the crossing as an interior non-node point on both paths;
   - normalize a short crossover jump arc or polyline bulge to the straight physical continuation of its owning pipe; preserve the curve only as source-display evidence and infer neither connectivity nor elevation from its orientation;
   - do not create physical equipment/junction nodes for ordinary elbows, endpoints, labels, or symbols; retain unproven pipe ends as explicitly pending virtual boundaries under the endpoint policy;
   - retain an audit record for every removed or healed segment.
5. Detect equipment and T nodes. Handle nested INSERTs and exploded geometry. Exclude legends, title blocks, and explanatory details using layout-relative bounds, not hard-coded page coordinates.
6. Reconnect equipment through omission symbols:
   - match dense repeated arrays by floor, system, row, and monotonic order; do not use unconstrained global nearest-neighbor matching;
   - place the equipment node at the main-diagram omission symbol;
   - keep both main-side and equipment-side source paths as the future edge geometry;
   - retain directly connected equipment at its physical connection when no omission symbol exists.
7. Build one logical edge between adjacent graph nodes when the traversed pipe contains no third graph node. Preserve source display geometry alongside normalized `attribute_paths`, including both sides of an omission gap. Display-only crossover arcs are excluded from physical path length and replaced by their straight semantic continuation.
8. Extract inline devices from both block references and exploded templates. Use complete multi-primitive signatures and negative controls; never classify from one line or one filled region alone.
9. Aggregate edge devices by `(edge_id, equipment_type)` while retaining one row per source instance for audit.
10. Validate counts, uniqueness, assignments, geometry distances, source coverage, and localized visual overlays. Do not accept a plausible overview image in place of tabular invariants.

## Enforce invariants

- Keep supply and return tracing separate. A proven physical endpoint contact with contradictory source layer classes may be retained only with `mixed_source_contact`, source handles, incident systems and `system_review_required`; do not silently relabel it or claim hydraulic consistency. Unclassified edges do not join supply/return tracing.
- Assign every detected inline device exactly once or report it explicitly as unresolved.
- Do not silently discard symbols because they are exploded rather than blocked.
- Do not promote valves or display artifacts to physical nodes.
- On SH16 ceiling sheets 08–10, set `edge_type` from the endpoint `node_type`. A riser (`RIF`) or an unresolved virtual terminal (`UT`) is `tee_to_virtual_equipment`. A `VIF` prefix is not the only virtual endpoint, and this label does not create an equipment port.
- An out-of-plane omission symbol keeps the two bars in front of its own arms. Bars behind that V, including a neighboring symbol inside the search radius, stay out. Extra forward bars stay unmatched. Do not choose the nearest bar or bind the other system. This match does not create an equipment port.
- A three-ray endpoint-incidence contact stays a physical tee when a nearby circle is not a matched omission symbol and is not a calibrated riser. An unmatched circle, even one within a few drawing units, does not erase the tee and does not create an equipment port. A circle centered on the contact can still be a tee. A matched symbol or calibrated riser still withholds that junction.
- A ceiling equipment label inside another block's selected set is not a unique identity. Do not give that label to the block that happens to have no second label, and do not create a supply or return port from the label.
- Do not connect two pipes merely because they cross in the drawing; an over/under crossover gap restores only the broken pipe and never creates a node at the crossing.
- Treat a crossover jump arc as a non-connectivity symbol, not a physical bend. Do not infer which pipe is above or below unless a separate project standard or elevation annotation states it.
- Do not replace omission-separated source paths with a synthetic straight line when edge attributes must be recovered later.
- Preserve stable IDs after deterministic spatial sorting.
- Infer tolerances from drawing scale and repeated geometry. SH16 constants are alignment expectations, not universal defaults.

## Deliver results

Produce at minimum:

- normalized node and edge tables;
- per-instance edge-device audit and per-edge/type aggregation;
- omission-marker, preprocessing, and gap-healing audits;
- JSON graph payload and summary metrics;
- full and localized comparison visualizations;
- a report stating exclusions, unresolved items, and validation results.

Use the field definitions and validation rules in [references/output-schema.md](references/output-schema.md).

## Default runnable visualization handoff

After a completed CAD conversion, also use the sibling [visualize-cad-pipe-topology](../visualize-cad-pipe-topology/SKILL.md) to generate a runnable local viewer directory, portable ZIP and validation report. This is the default final deliverable for this user's workflow; do not wait for a separate visualization request. Skip it when the user explicitly requests analysis/tables only or a non-retained regression run.

Pass the actual graph JSON, per-instance audit, explicit ports and source DXF/legend. Inspect and configure the current project's source symbols; SH16 block identities, floor bands and counts are not universal. Keep English-only display labels by default, preserve original IDs and respect later user language preferences. Preserve graph issues as pending review; do not rewrite extraction results to make the viewer look clean. Local package generation does not authorize uploading or publishing CAD data.

Retained bundled alignment runs now generate the viewer automatically after successful graph validation:

```powershell
python .\scripts\run_alignment.py --output-dir <new-results-dir>
```

The default viewer output is `<new-results-dir>-viewer` beside the results, plus its ZIP. `--visualization-output <new-viewer-dir>` chooses another path; `--without-visualization` explicitly opts out. Temporary regression runs without `--output-dir` keep their existing validation-only behavior. The sibling visualization skill must be installed for a retained run unless visualization is explicitly disabled.

## Run the bundled alignment case

From this skill directory:

```powershell
python .\scripts\run_alignment.py
```

Pass `--output-dir <path>` to retain the rebuilt artifacts. Use `validate_alignment.py --case <case> --actual <case>\expected\outputs\edges` for a package-integrity self-check without rebuilding.

## Shared schematic extraction v1.5.0

Read [references/shared-schematic.md](references/shared-schematic.md) when changing a source symbol, restoring equipment edges or processing a plant schematic. Use the installed `scripts/build_schematic.py` and shared geometry modules; do not fork a per-sheet algorithm or patch only a generated graph. Keep drawing-specific layer names, material/tag rules and verified symbol families in a versioned source profile. An unknown family stays pending until source evidence and positive/negative tests are provided.

`pipe_geometry.py` implements conservative native ARC and LWPOLYLINE-bulge crossover normalization. Require owning collinear tails and an independently qualified crossed-pipe witness, including explicit auxiliary pipe layers and split opposite rays. Preserve native display curves; protected chords must not connect to another pipe's endpoint or T at their crossing. Elevation is unknown. True quarter bends remain curves. SPLINE crossovers remain pending unless separately verified; do not claim arbitrary curved geometry is supported.

Equipment completeness is measured by native ports and completed adjacent-node edges, not node counts alone. Include physical equipment scheduled in material tables. Preserve a whole vendor assembly as one node when its source enclosure, caption, package note and pipe contacts prove that boundary; retain internal source geometry in the audit. Never create equipment from a table row, circle, frame or nearby tag alone.

Run both `scripts/run_alignment.py` (the immutable original SH16 case) and `scripts/run_schematic_regression.py` (the native 03 case). Run `test_pipe_geometry.py`, `test_equipment_assemblies.py` and `test_source_glyphs.py` for changes to these modules. The legacy fixture remains 427 nodes / 579 edges / 1560 components. These numbers are not acceptance counts for a new drawing.

## Three-way junctions after healing

After preprocessing and every gap-healing stage, detect junctions again. Three distinct same-system physical rays form a junction even when no pair is opposite in the CAD isometric projection. Remove verified valve/vent display legs first. Split logical edges at every such junction; do not bypass a third graph node. Pure crossover interiors still create no junction. Preserve established straight-run T IDs and append newly recovered isometric corners deterministically.

Drawing crop bounds are not physical boundaries. An omission symbol outside plot bounds may be retained only with source evidence: typed supply and return terminals both touch the glyph and both source paths reach main-graph junctions. Disconnected detail symbols remain excluded. Validate the new junctions' incident edges, not only the total counts.

## HIL handoff v1.3.0

The sibling visualize-cad-pipe-topology v2 generates exception-only local HIL review: node/edge groups, immediate annotations, whole-dataset confirmation and portable CAD/topology expert pairs. Preserve the extraction graph and its existing case baseline. Ship unreviewed viewers; put demonstrations in a separate examples folder. Human annotations and expert explanations never authorize automatic topology edits.


## Source endpoint and instrument coverage v1.5.0

Read [references/instrument-and-terminal-coverage.md](references/instrument-and-terminal-coverage.md) for source instruments, capillary legs or unresolved endpoints. Count unknown source endpoints as well as already recognized equipment ports. Default to explicit review-required virtual boundaries for unproven source pipe ends. A virtual boundary does not prove an external physical connection or a repaired pipe. Repair source-proven straight crossovers before creating virtual boundaries.

Include inclusive native symbol contacts, transformed primitive endpoints, bounded source sensor extension leaders, complete exploded signatures and whole measurement panels. A DPS/DPIT measurement loop is edge context, not a hydraulic link between supply and return. Remove its proven capillaries from the hydraulic graph and retain the entire source assembly. Link multi-tap measurement context to all affected edges without double-counting the instance.

Audit every recognized source inline instance as an edge attribute, measurement-group member, equipment-internal item, reference legend or unresolved item. Export all categories; do not turn legend items or internal vendor components into missing graph equipment. Track atomic source-pipe coverage and both graph endpoints of every edge. A leftover path must be a visible pending boundary/context with source evidence, or a reported blocking extraction failure; do not merely suppress it from the graph and report equipment ports complete.

Run `scripts/test_instrumentation.py` in addition to the existing tests. The active portable native fixture is `assets/alignment/sh16-plant-v5`; prior fixtures remain historical snapshots. The original full-floor SH16 alignment stays unchanged.

Exploded component coverage v1.6.2: recognize complete source prototypes across model-space layers, including layer 0; a known INSERT inventory does not cover exploded symbols. Read [references/exploded-component-coverage.md](references/exploded-component-coverage.md). Preserve source handles and infer no hydraulic links from instrument display leaders. Audit tagged source heads independently of detected sensor bodies; unmatched heads remain pending. Run test_exploded_templates.py and the native v5 fixture; validate source-backed additions against unchanged prior nodes, edge geometry and prior component records.


## Instrument head completeness v1.5.1

A block assigned to a pipe is not proof of a complete instrument assembly. Inspect both transformed native INSERT leads and external source leaders, including a single stroke shared by the instrument diameter and connector. Match complete tagged heads through source geometry; count distinct head identities rather than matching strokes. Preserve rotation/mirroring and keep competing heads ambiguous. Export instrument_head_coverage.json with completeness separate from edge assignment. A missing source leader remains a visible automatic component hint, even when its sensor body has a valid edge. Do not infer its association from proximity alone. Run test_instrument_heads.py and the actual E0116 regional assertions in the native fixture; compare individual source circles and leaders, not only instance counts or template words.

## Post-drawing quality gate v1.6.0

After drawing generation, perform [source fidelity checks and repair](references/post-drawing-quality-gate.md), then the sibling viewer's machine and visual gate. Check connectivity, complete assembly primitives and source-scale equipment display; fix confirmed omissions in shared rules, regenerate and rerun relevant regressions. Do not deliver a known deterministic mismatch as checked, or substitute unchanged counts for localized CAD comparison. Preserve source uncertainties explicitly and keep expert HIL review separate.

v1.6.1: For profiles where capillaries and hydraulic mains share a drafting layer, isolate the native DPS-connected component and its complete valves before testing independent main witnesses. Do not count a capillary as its own main tap or consume nearby disconnected pipe strokes. Keep dedicated-layer crossover gaps supported by their separate evidence. Export unqualified source curves as pending_source_curves.json and read-only source context; processed-line coverage never implies those curves have verified connectivity. Regress both the dedicated-layer 03 fixture and shared-layer positive/negative cases.

## Proven contact coverage v1.8.1

Configured near-junction normalization must run in ceiling and outdoor entry points as well as schematics/isometrics, before detecting T nodes. For proven endpoint incidence, canonicalize both segment cut positions with `proven_contacts.py` before quantized vertex keys; never spatially cluster unproven crossings or conflicting systems. Preserve a contact-pair audit.

Discover expected junctions independently from source circles and accepted near-contact candidates. Every source-supported three-ray contact must correspond to one final physical T with three distinct valid adjacent paths. An intermediate bridge record and a valid degree for existing T nodes do not establish completeness. Block a known missing T; retain uncertain equipment ports as pending. Run test_proven_contacts.py and native all-task source coverage after rebuilding, with per-case source handles, resulting node/edge IDs, stable ID mappings and component conservation.

## Physical equipment preservation v1.9.0

For hydraulic projections, ignore only proven meter measurement/pressure-tap branches under the current user policy. Large physical equipment and its inlet/outlet source connections must remain; an auxiliary-system name, repeated CAD block or missing schedule parameters is never permission to remove it. Six pump instances in the SH16 example remain edge equipment, not deleted objects. `derive_hydraulic_graph.py` rejects physical-equipment removal and removal of its incident edges, preserves isolated source equipment as explicitly unresolved, exports hydraulicEquipmentCoverage, and never substitutes zero resistance for missing data. Missing pump curves/pressure-drop curves keep solver readiness false.

An explicit source-native equipment rule can retain a unique bounded assembly without fabricating a material-profile match. Require tag, verified native block identity and complete multi-primitive geometry; retain missing parameter state. A source-profile verified closed enclosure can own an entering source pipe terminal even if that terminal does not touch an internal drawing primitive. Require a complete closed four-corner frame at the assembly bounds, terminal incidence, outward continuation and unique ownership. A nearby shape or unconfigured block is insufficient. Do not infer supply/return from terminal count. Run test_native_equipment_preservation.py and test_hydraulic_projection.py.

Supplier package captions have source variants. Match verified variants in the source profile, then recheck enclosure/caption/note/ports together. Folding package internals must conserve every source component identity and explicit equipment-internal ownership. Report changes in edge versus internal roles; unchanged edge component count is not the only valid conservation measure.

## Current-plan evidence boundary (v1.9.1)

When the user limits repairs to connections provable in the current layout, accept only source-supported pipe contacts in that drawing. Do not borrow schematic connections, nearest-distance matches, projected overlaps or equipment bounding boxes as substitute port evidence. Preserve large equipment, separate supply/return services where proven, and explicit missing resistance parameters; unproven ports remain pending. Distinguish completed instance/evidence audits from completed connectivity repairs. Record the user scope decision and source references; this does not confirm human review or close expert exceptions.

`double_line_pipes.py` is a diagnostic candidate-discovery helper only. Parallel-wall candidates do not establish bends, equipment ports, junctions or accepted edges. Keep ambiguous wall pairings pending and require independent source-contact evidence before admitting any candidate into a graph.

## Architectural plan context (v1.10)

For building plans, inventory architectural layers, nested blocks, attributes, dimension blocks, OCS text, xrefs and cached proxy graphics separately from pipe extraction. Use the companion extract-cad-building-context skill for a read-only source context sidecar and visualization v2.7+ for aligned overlays and local expert pairs. Do not classify walls as pipes, infer equipment ports from building outlines, or infer verified room polygons from text. Preserve pipeline counts and all node/edge/component source identities; unsupported representations must be reported and fixed before handoff.


## Pipeline ownership contract

For batch or mixed-family work, use sibling `orchestrate-cad-drawing-pipeline` v1.0.4 as the workflow entry point and read its references/contracts.md. The orchestrator schedules this skill; do not invoke the orchestrator recursively from a branch. Preserve task ID, source SHA256, units/WCS, profile hashes, stage status and artifact evidence. Use base library + center profile + family profile + verified local evidence; unknown/conflicting semantics stay pending. Branches own separate outputs and never overwrite another branch's graph, context or review records. HIL is error-only with whole-task confirmation, independent per drawing.


## Native inline WCS anchors (v1.11.1)

For transformed LWPOLYLINE symbols, get_points() supplies OCS xy/bulge, not WCS positions. Use native_inline_coordinates.ball_valve_anchor for the complete verified three-line/two-bulge valve family. Compute anchors from vertices_in_wcs after INSERT transforms, retain native source identity, require exactly one bounded source-edge contact, and preserve unresolved/ambiguous states. Mirroring and negative extrusion must not silently remove edge components. Regress rotations, mirrors, negative OCS and incomplete-symbol controls with test_native_inline_coordinates.py. Shared graph-ID reconciliation must disambiguate parallel edges by full source path, not endpoint pair alone; run test_parallel_edge_ids.py. A component repair never establishes an equipment port or authorizes connecting nearby equipment.

Native regression default is now assets/alignment/sh16-plant-v6. v5 remains immutable; v6 only adds the 14 already implemented reference_candidates_only equipment parameter states and explicit witness metadata for 3 unchanged crossovers, with compatibility-delta.json. No fixture connectivity or component counts changed. Never update a golden graph to conceal unexamined geometry or assignment changes.

The same native-anchor phase now verifies the complete six-LINE balancing-valve signature (two crossed equal diagonals, two paired flange strokes and two source-connected adjustment strokes). Assign its WCS center only to one bounded accepted edge; a block name or six arbitrary lines is insufficient. Ball and balancing-valve recovery changes edge attributes only, not equipment connectivity. Run the positive, rotated/mirrored and incomplete/random-shape negative controls.

## Independent source candidates v1.12.0

Read [source candidate coverage and native profile repair](references/source-candidate-coverage-v112.md) for missing source layers, filtered equipment candidates, filled exploded variants, unknown-service contacts or a whole-drawing repair. Run the independent final-source inventory and gate, and recompute equipment ports, T nodes and adjacent edges after normalization. Never equate known-instance conservation with full-source completeness.

## Unknown-service crossover completion v1.12.1

Read [source-group crossover completion](references/source-group-crossovers-v1121.md) when an auxiliary or unknown-service pipe remains broken. Physical source-group verification is shared by near-junction and straight-crossover stages; it never assigns hydraulic service. Discover opposed-tail gaps before the service filter. A same-layer physical gap with independent crossing evidence that is skipped only for missing group verification blocks delivery; do not relabel it as a generic unproven endpoint. Gate on the full final span, not merely both source handles being present.

## Log consolidation (2026-10-27)

Read [expert repair evidence and batch handoff](references/batch-repair-handoff.md) before expanding a local defect into a family/shared repair or handing rebuilt results to the pipeline. Instruction/handoff revision only; the validated geometry/rendering algorithms from the previous release are retained.
