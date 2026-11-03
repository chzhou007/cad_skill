# Viewer input contract and project configuration

## Supported normalized graph

The frontend consumes a two-system water-piping graph. Machine system IDs are `supply` and `return`; display codes/names/colors/line patterns are configurable. Adapt other source schemas explicitly before building. Do not pretend this viewer understands an arbitrary CAD ontology without an adapter.

`graph.json` contains `nodes` and `edges` arrays:

- Node: unique `node_id`, `node_type`, `floor` (or `floor_band`), finite native `x`, `y`. Types are `equipment` / `physical_equipment`, `physical_junction` / `tee`, or `virtual_equipment`. A junction must have one known system, inferred from incident edges or specified as `system`.
- Virtual node: `ports` containing unique `port_id`, `system`, native `x`,`y` and optional `source_marker_handle`; alternatively provide the port CSV. Each explicit port binds one adjacent edge through `start_port_id` or `end_port_id`.
- Edge: unique `edge_id`, existing `start_node_id`, `end_node_id`, `system`, nonnegative `path_length`, `path_points` (two or more native XY pairs), and `attribute_paths` (one or more paths). Keep omission-separated source paths disjoint rather than manufacturing a straight source pipe. The builder derives edge floor fields from endpoint nodes.
- Edge inventory: `equipment_inventory` entries with `equipment_type`, integer `count` and `device_names`. Counts and names must reconcile with the per-instance CSV. Supply `{}`/empty inventories only where no components were detected.

Instance CSV: `device_name`, `equipment_type`, `edge_id`, `assignment_status` (`assigned`), finite `x`,`y`,`assignment_x`,`assignment_y`,`edge_distance`; source audit columns `source_kind`, `source_block_name`, `source_top_handle`, `owner_equipment` are retained. Device names must be unique. Display aliases replace the mapped type name with its English label; source names remain in the JSON audit. If a larger name needs translation, provide an explicit input adapter and preserve the original identity separately.

Optional port CSV: `node_id`, `port_id`, `system`, `port_x`,`port_y`, optional `source_marker_handle`. If both embedded ports and a CSV are supplied, their identities and counts must agree. Ports not incident to their declared virtual node are invalid.

Identifiers are preserved. Markup delimiters/control characters in IDs are rejected rather than inserted into HTML/SVG. Use an explicit traceable adapter for unusual IDs. The supplied template uses English-only display text; later localization must translate all UI/legend labels together, not mix languages.

## Configuration

```json
{
  "project": {
    "id": "Building-A",
    "title": "Pipe Topology",
    "description": "Water systems",
    "equipmentLabel": "Source equipment"
  },
  "preferred_port": 8765,
  "systems": {
    "supply": {"code":"CHWS", "name":"Supply", "color":"#cf26bd", "dash":""},
    "return": {"code":"CHWR", "name":"Return", "color":"#aa7a10", "dash":"5 3"}
  },
  "floors": [
    {"id":"Roof", "label":"Roof Level"},
    {"id":"B2", "label":"Basement 2"}
  ],
  "device_types": [
    {
      "code":"BV", "label":"Ball Valve",
      "source_names":["Ball Valve", "球阀"],
      "symbol":{"drawing":"main", "block":"VERIFIED_BLOCK_NAME", "mode":"block"}
    }
  ],
  "equipment_symbol": {"drawing":"main", "block":"VERIFIED_EQUIPMENT_BLOCK", "colors":[1]}
}
```

`floors` is optional. When absent, floors are enumerated from nodes and ordered by their mean CAD Y position. Numeric IDs get an F label; named IDs retain their text. An explicit list must contain every floor exactly once, use string IDs and define the intended display order. Equipment counts and review counts are always computed.

Device codes must be unique SVG-safe identifiers; `EQUIPMENT` is reserved for the equipment glyph. Every used type needs a verified mapping. Unused configured types are omitted from the legend. Do not reuse a profile just because its labels look similar.

Symbol `drawing` is `main` or `legend`; `mode` defaults to `block`. Block mode exports canonical block geometry. Insert mode exports an actual modelspace INSERT with its placement rotation/scale, then normalizes the resulting geometry. If multiple inserts share the block, supply `insert_handle` to disambiguate. Optional `colors` selects ACI entity colors, for example separating a cabinet's outline from an assembly's attached pipes. Only set such filters after inspecting the source. Symbol geometry must remain nonempty after filtering.

Inspect and configure source pipe line types too: solid/dashed distinctions must match the project's CAD table. Source vector colors may be changed for light-background legibility, but not symbol shapes, filled regions or counts. An exploded device in the main drawing may use a verified matching symbol from the supplied table, as SH16 air vents do. If no reusable block exists, extract the verified geometry into a traceable reference DXF and point the config to that legend input; do not hand-invent an icon.

For a mixed architectural reference containing extensive unrelated electrical/MEP detail, an explicit `cad_reference_context` list may scope that top-level source INSERT to an externally prepared building sidecar. Each entry requires its actual `handle`, exact `block`, `mode: architectural_context` and an evidence-backed `reason`. The builder preserves every primary-drawing entity and copies the selected reference's native building paths/source chains from the validated sidecar into CAD comparison. It rejects missing INSERT identities or empty reference coverage. Preserve the complete original reference separately, record the scope in the manifest, and inspect actual CAD/Pair alignment and performance. This is a reference display scope, not removal of primary pipe/equipment data or inferred connectivity.

## Output and limits

The builder emits a new viewer directory plus sibling ZIP. It stages work so failed checks do not leave a plausible final viewer. It never rewrites source graphs or DXFs. The app uses local static assets and a loopback HTTP server. It is an inspection interface, not hydraulic analysis, a live monitor, a CAD editor, or proof that the original extracted graph is physically correct.

Read `public/data/manifest.json` for input hashes, actual counts and per-type symbol sources; read `validation-report.json` for structural checks. Browser QA is separate. Review degree exceptions and original unresolved semantics rather than replacing them with optimistic status labels.
