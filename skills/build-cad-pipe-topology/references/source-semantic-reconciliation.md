# Source semantic reconciliation and pre-HIL comparison

Distinguish physical equipment aggregation, native symbol assemblies, pipe junctions and external interfaces. A circle, room tag or repeated short stroke alone never proves physical equipment. Equipment aggregation requires native enclosure/assembly evidence, all source ports, adjacent-edge conservation and internal-component ownership; preserve every instance and source path. Do not merge ports just to reduce unresolved counts.

Before expert HIL, classify complete source symbol families, including nested/exploded forms, rotated/mirrored members, circle-center/rim contacts, terminal strokes, concentric circles and imported block aliases. Retain a candidate assembly ledger distinct from hydraulic node ownership. Cross-service circle tangency is a negative case, not a T. A short stroke may be a glyph or actual branch: calibrate its role before deleting/connecting it. No universal radius or length constants.

Known destination and remote identity are separate fields. Bind text through traced native leader incidence, never nearest text alone. Preserve destination class, exact source text/handles, service, floor/elevation evidence and unknown remote port. Do not invent physical equipment from a destination caption. Source Z and dimension/elevation text require unit/scope calibration before physical interpretation.

Use scripts/source_semantic_reconciliation.py for conservative enrichment and candidate assembly accounting. It never applies hydraulic merges. Audited Importer block renaming must be propagated to profile aliases using original/imported handle mapping, not name prefixes. Alias repair does not prove an engineering symbol class.

Run a source-coordinate comparison round BEFORE final HIL: inventory source candidates independently; group recurring issues by mechanism; inspect representative CAD and topology at the same extent, including counterexamples; repair deterministic shared rules and regenerate all affected members; reconcile IDs, edges, ports and components; compare again. One sampled match alone is not family-wide acceptance. Carry unresolved rule/role/calibration families as algorithm blockers. Only genuine source ambiguity belongs in expert ambiguity queues; avoid thousands of equivalent expert tickets.

Produce source-comparison.json with graph_sha256, rounds_completed, native_comparisons [{path,sha256}], families [{id,status,source_handles,disposition}], algorithm_blockers and unclassified_terminal_count. Status resolved requires family-wide checks and repair proof, source_ambiguity requires exact missing evidence; neither may be asserted just to pass. Grouped candidates never silently replace the hydraulic graph. A blocked drawing can be delivered as a comparison work product with hil_ready=false, not as expert-ready topology.

Regression includes label-leader positive/negative incidence, source ambiguity versus algorithm pending, exact imported aliases, no fabricated equipment, cross-service tangency and stale/missing comparison evidence. Historical fixtures remain immutable.

## Readability before source trials

Confirm the actual DXF file read codec with ezdxf.filemanagement.dxf_file_info. A modern AC1032 DXF is UTF-8 even when its retained legacy header says ANSI_936. Preserve source Chinese verbatim in strict UTF-8 JSON and CSV; reject replacement/surrogate characters and verify representative complete Chinese labels visually at readable size, with their full leaders inside the crop. No guessed decoding of binary proxy payloads is evidence. Read CLASS IDs and typed BLOCK_RECORD pointers structurally instead.

## Source pipe section continuation

The opt-in source_section_connections profile runs in build_schematic after initial trace and before component assignment. It requires source SHA256, readable native calibration evidence, project pipe layers, radii and angle rules. Use pipe_section_connections.py: one degree-one center contact, one same-layer rim contact, external main ray beyond the circle and radial outgoing tail; preserve conflicting layer contacts as separate. Protect named interfaces and reject diameter, service and floor contradictions. Preserve all native attribute paths; circles become audited semantic connector spans, not physical equipment or asserted vertical lengths. Reconcile final edge signatures after reconstruction and retain UT IDs even after their semantic status changes.


## Nested equipment and source scoping

Inventory complete nested MEP INSERTs before any architecture-only scope is applied. A top-level object can contain an entire floor of equipment; neither the reference filename nor its parent layer establishes an architectural role. Keep immutable full source and a source-chain handoff for excluded MEP candidates. Architecture exclusions do not remove pipe-branch equipment. Source tables establish class candidates, never a port or cross-drawing connection.

The opt-in nested_equipment_ports stage in build_schematic restores physical equipment ownership after source-circle normalization and before component assignment. Supply a hash-pinned readable DXF, actual INSERT ownership chains, source prototype fingerprints, caption signatures and WCS floor evidence. nested_equipment_ports.py retains one node per source instance path, including repeated captions; transformed complete closed native outlines own only unique degree-one source terminals on that outline with an outward pipe ray. Bounding boxes only prefilter candidates. Reject interior, nearby, competing-owner, inward and floor-conflicting cases. Keep all actual port coordinates, edge services, IDs, source paths and component identities. Retain source equipment without proven ports explicitly; never invent links or assert expected port completeness from accepted contacts alone.

The source CAD view must retain those same MEP bodies through audited retained_mep_chains even when an architecture sidecar owns the rest of a reference. Preserve source captions with actual Chinese decoding and font checks. Run test_nested_equipment_ports.py, circle/proxy tests, actual fresh source rebuild and historical/native regressions; compare complete equipment, pipe contacts and negative examples at the same extent before HIL.
