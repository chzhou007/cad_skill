# Shared schematic extraction v1.5.0

## Execution

Run `scripts/build_schematic.py --dxf <source.dxf> --bindings <instance-bindings.json> --profiles <equipment-profiles.json> --materials <material-profiles.json> --config <source-profile.json> --output-dir <fresh-dir> [--previous-graph <prior-graph.json>]`.

Use the bundled `assets/alignment/sh16-plant-v4/inputs/source-profile.json` as a documented example, not a universal layer/symbol classifier. Input hashes, parameter library versions and task-local identity must be preserved. Run with ezdxf available. Do not overwrite an existing graph or review record.

## Base rules and source profiles

Shared modules implement connectivity, native equipment/assembly detection, source pipe contact tests, inline-span recovery and curve isolation. The profile supplies system layers, qualified auxiliary layers, native block names, inline type mappings, explicit equipment/material tag families, external note/leader rules, exploded flange layers and full source-terminal glyph families. Changes to a shared rule apply to future configured drawings; do not claim existing other drawings were rebuilt unless actually run.

A material row must describe physical equipment. Match an explicit source tag/caption, actual closed body and at least the configured number of native ports. A manufacturer package requires its dashed enclosure plus matching caption and vendor note. Store its internal geometry audit; do not count each pump or vessel inside it as an independent graph equipment node.

Identify ports from native body/assembly contact and outward source pipe continuation. Output `equipment_ports.json` and `equipment_port_coverage.json`. Each pipe port must have a completed adjacent-node edge or a localized unresolved record. CH-01/02/03 have three source ports in the bundled diagram; HE has two. This is source evidence, not a universal equipment-type port count.

## Native curves and discontinuities

Normalize a jump only with both owning tails and crossed-pipe evidence. A crossed pipe may be an explicitly configured auxiliary source layer; it is a witness, not a permission to merge networks. Split opposite rays are valid evidence. Prevent the normalized chord from joining crossing endpoints, even if the crossed pipe has a real T of its own. Preserve native ARC display geometry and relative elevation unknown. Keep real 90-degree bends as curves. Unqualified curves remain pending.

Heal inline gaps only with a complete native symbol or a tested exploded signature and two unique opposed source pipe contacts. Two equal parallel flange strokes require midpoint contacts, a scale-bounded gap and opposed collinear tails. A circle requires its full two-oblique-line signature and diametric opposed contacts; its semantics remain pending. One line, a bare circle or a plain short gap is insufficient.

External interfaces require a source note and its leader, or a complete configured native terminal glyph. The U-plus-short-bar family requires both side walls, full base, centered smaller parallel bar and centered native pipe termination. Label it Source-marked Terminal when its exact service is unknown. Do not infer flow direction, elevation or native DXF boundaries from ordinary endpoints.

## Geometry versus classification

Build proven source endpoint contacts separately from hydraulic class. Preserve `source_systems` on each edge. Mixed/unknown classifications use explicit `unclassified_water`; contradictory incident classes require `mixed_source_contact`, `incident_systems`, `system_review_required` and source handles. Same-system trace must not traverse that boundary as another system.

Three distinct source rays create an unreviewed junction candidate only after recognized display legs and package internals are dealt with. Four-or-more rays stay pending. Source-contact candidates are not expert-accepted T nodes. Export unresolved paths, components, tags and system conflicts; never erase them to improve an overview.

## Regression and review

Run `python scripts/run_schematic_regression.py --output-dir <fresh-dir>` for the portable real 03 fixture. It verifies input hashes, exact graph and port ledger equality, every jump on a complete edge, no crossover graph node and unknown elevation. Synthetic tests cover positive/negative symbols, false equipment, mirrored/rotated arcs and split crossing witnesses. The older alignment case remains unchanged.

A partial extraction stays unreviewed and graph_complete=false even when every detected equipment port has an edge. Review confirms the loaded graph only; it cannot accept unresolved source paths. New graph identities cannot inherit previous human confirmations.

Unproven ordinary pipe endpoints are allowed only as explicit unresolved_source_terminal virtual review boundaries under v1.5.0, not as proven external interfaces. See instrument-and-terminal-coverage.md.
