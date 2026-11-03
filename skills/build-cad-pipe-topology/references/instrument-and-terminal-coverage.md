# Instrument and endpoint coverage

## Provenance before appearance

One drawing can contain INSERT heads, native extension leaders, exploded instrument circles and a tagged measurement panel. Keep these as a complete source component. Do not infer hydraulic flow through a sensor or pressure measurement leg.

`instrumentation.py` implements inclusive segment-box clipping (including boundary and corner contact), native primitive endpoint ownership, bounded axis-consistent sensor extension contacts, complete four-stroke bowties, full tagged DPS assemblies and closed two-DPS/two-DPIT panels. A bare circle, lone label, two crossing lines, open bowtie or rectangle alone is insufficient. Unmatched glyphs remain pending. The tested sensor drafting clearance is at most 0.05 of that native glyph's diagonal, only for explicitly configured sensor blocks with a perpendicular source lead and a unique pipe contact; it is not a global nearest-neighbor rule.

Local DPS loops need two true main taps, two opposite body contacts and source native valve/gap evidence. Preserve their native source geometry and component members. Fold their capillaries, then recompute T candidates and adjacent-node edges. The two hydraulic pipes stay independent. Multi-edge context uses one canonical component instance with related_edge_ids. Inventories deduplicate by instance ID when both owners are selected.

Panels require a source closed enclosure, at least two fully tagged DPS and two DPIT circles, and two independent typed riser terminals. Do not collapse such a measurement panel into a fluid-through equipment node. Attribute the source panel to its risers, keeping each terminal independent.

## Endpoints

Before virtual closure, `straight_crossovers.py` restores only a unique pair of opposite collinear source pipe terminals, with the same source class and exactly one strict interior crossed-pipe witness. The allowed gap is calibrated from explicit source valve glyph diagonals. No witness or an oversized/ambiguous gap stays pending. Protect the restored span against crossing nodes; elevation stays unknown.

A source end without a proven equipment/interface is retained as virtual_equipment / boundary_type unresolved_source_terminal, with source handles, source coordinates, one explicit port and review_required=true. It stops network tracing. It is not a confirmed external interface or a claim that no other drawing connects there. Keep its original problem available to HIL. Every published edge must reference two existing graph nodes; every explicit virtual port binds one adjacent edge.

Compare atomic_source_pieces with atomic_pieces_on_edges and inspect unresolved_paths, not just equipment_ports_with_edges. Missing source coverage cannot be silently discarded. Complex cycles or multi-ray contacts that a profile cannot resolve require explicit review representation or a blocking report; do not claim the endpoint policy automatically solves all such geometry.

## Component accounting

Each native inline source instance has exactly one role: edge_component, measurement_assembly_member, equipment_internal_component, reference_legend_only or unresolved_component. Group members keep their own source handles; assembled context has a separate canonical record. A legend exclusion needs an explicit source legend title and at least six known captions within a scale-bounded region. Equipment internals require the proved vendor enclosure or exact contact with its retained internal source geometry.

The viewer should show the full original component geometry at native source coordinates and scale, including actual instrument heads and leaders, rather than placing a generic icon on the pipe. Source text is not needed for recognition geometry. Preserve single-language display labels, allow source tags and keep annotations separate. For new schematic profiles enable display.components=true. Keep unresolved terminals visually distinct and explicitly unconfirmed.

The default strict_source_path_coverage gate blocks publication if unrepresented pipe paths remain after virtual closure; it writes unresolved_paths.json and source_path_coverage_failure.json before stopping. Do not disable it to hide a failed drawing. Measurement context and reference/internal roles are retained as separate evidence.
