---
name: extract-cad-building-context
description: Extract auditable architectural context from existing building-plan DWG/DXF files for CAD and piping viewers. Preserve native walls, openings, columns, stairs, grid attributes, dimensions and room-label references in source coordinates; distinguish source geometry from unproven room boundaries and BIM semantics.
---

# Extract CAD Building Context

`source_shaft_text_inventory.py` re-extracts all labels containing `井` already present in a supplied architectural context, validates their source chains, text and world positions, and lists nearby graph risers without assigning pipe ownership or a shaft boundary. Nested blocks and cached MULTILEADER text are supported through the existing source renderer. This is not a complete native text inventory: proxy copies may be skipped even when the context issue count is zero. Run `test_source_shaft_text_inventory.py` and shaft-source tests.

`proxy_object_owner_inventory.py` distinguishes opaque `ACAD_PROXY_OBJECT` database entries from graphical `ACAD_PROXY_ENTITY` instances and traces owner metadata up to a graphical entity or block record, without decoding proprietary payload. A matching source-chain handle is metadata only; an absent match does not establish full visual or semantic coverage. Database totals are not the count skipped by a renderer. Run `test_proxy_object_owner_inventory.py` and source readability tests.

User language requirements override the default English display. For a source-Chinese viewer, keep this skill's source text and English alias records unchanged, verify strict native decoding and source handles, and use the visualization skill's explicit source-label display option. The building sidecar remains an architectural evidence layer, not proof of room boundaries or equipment ownership.

Current release: **v1.1.4**. Use this for source-derived building context, rather than generating or redesigning a floor plan. Read `references/research-and-boundaries.md` for tool selection and limitations.

## Workflow

1. Preserve DWG/DXF. Convert DWG with the installed ODA workflow if necessary; do not explode or overwrite the source. Inventory modelspace and nested layers, block attributes, dimensions, xrefs, proxy graphics, units and elevations before extraction. Distinguish DXF graphical entities from non-graphical proxy objects.
2. Run `scripts/architecture_context.py --dxf SOURCE.dxf --graph VIEWER/public/data/graph.json --output OUTPUT`. The graph supplies only the existing world-to-view transform; its nodes, edges and component assignments must not change. For a standalone architectural drawing, omit `--graph` to derive a display transform from native drawing extents. Generation requires Python and ezdxf; viewing the resulting bundle does not.
3. Keep original layer, source-chain identity, coordinates and source text. Normalize drawing layer aliases into candidate categories, including inherited layer 0. Expand nested blocks with their actual transforms, block attributes and rendered dimension blocks. Preserve hatch holes with compound evenodd geometry. Log missing xrefs, unsupported transformations and absent cached graphics explicitly; never silently skip architectural content.
4. Export `architecture.json`, `architecture.svg` and `architecture-labels.svg`. UI labels are English. Preserve source-language text in audit JSON, use explicit translations, and label unknown translations `Source label ID` with `translation_pending`. Unknown translations must remain searchable by stable reference and appear in the pending report.
5. Treat a source room name as a label candidate, not a verified room polygon or equipment-room association. Do not infer areas, fire ratings, clear widths, levels or pipe connectivity from a label, door arc, bounding box or projection overlap. Source layer names give candidate meaning rather than full BIM classification. Missing source content cannot be reconstructed by drawing a plausible building.
6. Use `validate_context` to check source hash, exact coordinate transform, unique IDs, label language and representation failures. Inspect the full building extent plus wall/opening, grid/dimension and room-label examples in the actual viewer. Compare against native source geometry. Known deterministic omissions must be fixed before handoff; source uncertainty remains explicit pending.
7. Integrate via `visualize-cad-pipe-topology` v2.7+ when a pipe graph is supplied. Provide separate geometry and label switches, building extent fit and label location. Expert Pair exports include local building geometry and English labels at the same transform, independent of display switches; include original label references in local context JSON without embedding the full building.

## Regression

Run `python -m unittest discover -s scripts -p test_architecture_context.py`. Cover nested rotation and inherited layers, source handles, attributes, dimensions, room translations, unknown text, hatch openings, xrefs and exclusion of pipe layers. Then run viewer/backend and Pair tests from the companion visualization skill. Compare all graph, component and source file hashes before and after building-context additions. Do not create HIL errors or attestations as a technical gate.

SH16 06/07 have sparse architectural source content; report it instead of fabricating room names or equipment connections. 08/09/10 share a plan family, so apply and verify shared fixes across all three. Record primitive counts as source records, never as counts of physical walls, doors or rooms.


## Pipeline ownership contract

For batch or mixed-family work, use sibling `orchestrate-cad-drawing-pipeline` v1.0.4 as the workflow entry point and read its references/contracts.md. The orchestrator schedules this skill; do not invoke the orchestrator recursively from a branch. Preserve task ID, source SHA256, units/WCS, profile hashes, stage status and artifact evidence. Use base library + center profile + family profile + verified local evidence; unknown/conflicting semantics stay pending. Branches own separate outputs and never overwrite another branch's graph, context or review records. HIL is error-only with whole-task confirmation, independent per drawing.

This skill owns the canonical scripts/architecture_context.py. The viewer may contain a generated portable copy only with a matching dependency lock; change the canonical source and resynchronize through the orchestrator verifier, then run both regression suites. Never apply pipe gap healing to architectural openings.

Source layer exclusion v1.1.1: do not interpret the Chinese door character inside valve/instrument layer names as architectural doors. Exclude explicit MEP valve/instrument names before architectural alias matching; retain real door layers. Regress both negative and true-door cases.

## Log consolidation (2026-10-27)

Read [building branch applicability](references/branch-applicability.md) for mixed drawings, support-only sheets, zero-result adapters and pipe/building isolation. Instruction/handoff revision only; the validated geometry/rendering algorithms from the previous release are retained.

`shaft_label_source_candidates.py` verifies explicitly selected two-handle modelspace INSERT/TEXT chains against the readable source hash, block membership, original Chinese text and WCS transform, then lists nearby graph `out_of_plane_riser` candidates within a caller-specified radius. The architectural sidecar and graph must both reference the same source SHA-256. Radius is only a search scope: no shaft polygon, floor-to-floor identity, pipe ownership or connection is inferred. Nested chains deeper than one INSERT, xrefs and proxies are outside this helper and require separate handling. Run `test_shaft_label_source_candidates.py`, building context regression and a source-bound comparison. Keep per-floor source evidence and do not use candidates as accepted mappings.

`floor_anchor_riser_evidence.py` tests an explicit floor translation hypothesis against at least three non-collinear, selected native INSERT/TEXT anchor pairs with exact source identity, block membership, text and transformed coordinates. The policy pins both sources, contexts, graphs and shaft-candidate reports; candidate risers must still match the bound graphs. Record how anchors were selected and alternative repeated matches. It computes spatial residuals only: selected anchors can be dependent on the hypothesized riser alignment, and near-zero residual is not physical connection or an isometric mapping. It does not search all possible registrations or estimate rotation/scale. Run `test_floor_anchor_riser_evidence.py` and source-bound checks.
