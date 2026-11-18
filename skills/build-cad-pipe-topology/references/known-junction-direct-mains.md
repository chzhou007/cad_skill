# Direct mains between already matched junctions

Read this after equipment/port correspondence when the mapped branches leave
unmapped mains whose two endpoint Ts already have independent cross-view
identities. Equipment labels alone, or the same order along a corridor, do not
establish these identities. This mode adds path correspondences; it does not
repair either local graph or extend a disconnected detail header by proximity.

Use `match_known_junction_direct_mains.py`. It independently replays the current
paired mapping and its corridor/inventory ancestors, checks exact local path
snapshots and consistent one-to-one endpoint identities, then compares unused
direct same-service T-to-T edges. Keep supply and return separate even where
their drawing coordinates coincide. A reversed stored edge has the same two
physical endpoints; retain the parent correspondence's A/B orientation.

Each candidate needs two same-floor, three-ray native Ts and unique native LINE
coverage of every selected drawn span. Multiple paths separated by a flexible
joint require the existing calibrated template, unique canonical component
ownership, native XYZ contacts and a complete endpoint-bounded pipe/joint chain.
Do not add marker interiors to pipe length. A parallel edge, missing counterpart,
changed parent snapshot, ambiguous native witness or mixed service cannot be
resolved by selecting the first or shortest route. Retain unmatched boundaries
as unresolved; successful local pairs do not prove whole-floor connectivity.

The policy pins `paired_sha256`, `paired_receipt_sha256`,
`template_origin_sha256`, `floor`, `mapping_prefix`, and explicit
`selected_pairs` with one `plan_edges` and one `iso_edges` entry. The selected
scope must agree with the uniquely discovered direct-main pairs. Outputs use
`mapping.json` and `source-mapping-receipt.json`; `verify_output` independently
reproduces the complete result. No human acceptance transfers from the parents.

For plan attributes on these paths, use `known_junction_main_plan_attributes.py`.
Reuse the native annotation inventory, scalar source witness, through-T reader,
unit/dimension corroboration and inline metric kernels. This reader currently
supports scalar pipe captions; a selected F annotation is routed to the existing
native F reader rather than flattened into a scalar. Do not weaken that guard to
make another drawing pass.

Read component-qualified DN labels separately before attributing pipe labels.
Replay the actual qualifier, all leader strokes, native template and current
component owners. Only the successfully proved component label/strokes can be
excluded from pipe attribution. A failed qualifier remains a blocker. For SH16
09, `18C0A` is a DN300 label for four metal flexible joints; the four added mains
have their own DN200(3.200) pipe captions. Keep both source meanings. The
parenthesized value is retained without assuming a physical datum or length.

Plan XY length comes only from native source pipe spans inside the corroborated
floor-plan window. Keep inline interiors, unshown connectors, installed whole
edge length and physical ports unknown. These outputs remain source evidence
until complete-parent fusion, source comparison, viewer and HIL are rebuilt.

The SH16 regression adds four pairs without rewriting the prior132 paths:
`E0046/E0178`, `E0129/E0298`, `E-EQUIP-B8B0/E0191`, and
`E-EQUIP-B8B1/E0312`. Run the new two test files with the historical component DN,
inline coverage, through-T, unit/length and corridor/paired mapping tests. Check
the actual native entry and its independent replay; a fixture pass alone does
not prove the CAD case or integration into the formal pipeline.


For the complete axis parent, run `attach_known_junction_main_plan_attributes.py
--policy POLICY.json --output NEW_RUN`, then `pipeline.py
validate-known-junction-main-fusion --fusion-run NEW_RUN`. Its policy pins the
complete parent graph, canonical component CSV, native attributes/receipt and
explicit source-horizontal isometric directions. Preserve every earlier field,
including existing anchored-main attributes and external-destination context.
Only the four new writers may gain attributes. Removing the outer root and
those exact writers must recover the complete parent byte semantics.

`known_junction_main_fusion_gate.py` retains all parent errors and pending issues.
The viewer's matching helper consumes the new root before current-floor
adoption and lists each ancestor audit at its actual source directory. Do not
let an inner root validate a child graph with additional fields. Run the fusion,
source dispatch, viewer ancestry and dependency-location tests.

A bounded native replay session may reuse a result only after an actual native
verification in that process and complete observed read-closure validation.
Changed files/code, directory membership, missing-file probes, environment or
external effects invalidate or disable reuse. Standalone calls still replay;
never preload a stored success record or substitute a geometry rule.
