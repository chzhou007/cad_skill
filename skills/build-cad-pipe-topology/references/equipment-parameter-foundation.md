# Equipment and material parameter foundation

Build this source-derived layer before connectivity extraction. It supports recognition; it does not create pipe connections or confer human approval.

## Records

- Equipment class: semantic family and its parameter field definitions.
- Schedule profile: a specific model/specification/operating-condition row with values, units, inequalities, requirements and applicability. Preserve merged headings, primary/secondary sides and summer/winter cases.
- Material profile: nominal-size options, pressure/range, constituent materials, actuator/electrical requirements and specification-to-quantity pairs. Keep source quantity as a reference.
- CAD pattern: the actual reachable native block or exploded source geometry, normalized geometry fingerprint, source hash and handles. An abbreviation is not a verified geometric prototype. A common caption can describe multiple symbols.
- Instance binding: task-qualified object ID, CAD source evidence, class/prototype, candidate profile IDs, explicit local overrides and unresolved reasons. Use a list of candidates when several rows apply.

Each value must retain the source drawing/version/hash, table/row or cell bounds, original text and entity handles. Retain the original language as evidence while respecting the chosen UI language.

## Read the table faithfully

Read TEXT, MTEXT, attached ATTRIB values and model-space ATTDEF display tags. For an unbound model-space ATTDEF, distinguish its displayed tag from its default value; retain both. Do not use a default such as 1450 or R as a displayed pump power or seal merely because it is stored in the text field. Verify the drawing context and record which representation was used. The AutoCAD command documentation distinguishes attribute tags from defaults shown upon block insertion: https://help.autodesk.com/cloudhelp/2025/ENG/AutoCAD-Core/files/GUID-5C99524B-B5BB-4067-AE18-BD3575F29DBF.htm

Reconstruct actual table grids and merged cells. Exclude revision-cloud and decorative geometry from grid detection. Account for small drafting skew and centered text overflowing a column; record bounded recovery instead of silently dropping the row. Check every numbered item against the extracted list. Preserve split specification rows and matched quantity ordering. Do not add the quantities of two operating rows for the same fan twice.

Keep original units and inequalities. A W header with a suspicious 9.9 value is a unit-review issue, not permission to rewrite it as kW. Keep multiple operating temperatures as separate source cases with unresolved condition assignment when necessary. Distinguish blank, not stated, not applicable, conflicting and extraction failure.

## Match without inventing attributes

Match explicit equipment tags within their family and schedule range; normalize zero padding only for matching and preserve original tags. Confirm symbol family through actual geometry plus bounded local label evidence. Do not use unconstrained nearest-neighbor association. Treat primary/secondary pump stage, combined ball/butterfly captions, rooms, capacities and air-delivery variants separately.

Prefer explicit instance annotations over an exactly identified schedule variant, then a verified type-level reference. Shared candidate properties may be exposed as reference values, clearly separated from effective installed attributes. Do not assign an arbitrary CRAH capacity from a shared tag pattern or a nominal diameter from a material-table option list. Preserve explicit cross-references such as 'material same as motorized on/off valve' with a traceable parent profile.

## Handoff and limits

Deliver the field dictionary, equipment/material profiles, native pattern catalog, task-local instance bindings, coverage report and unresolved items. Shared libraries are immutable, versioned references; each drawing retains independent topology and human review. Keep graph and annotation data unchanged while adding a parameter enrichment sidecar. Do not describe proposed class mappings as expert-confirmed recognition or claim an unimplemented family adapter is complete. Project-specific table coordinates and shape identities are not universal extraction rules.
