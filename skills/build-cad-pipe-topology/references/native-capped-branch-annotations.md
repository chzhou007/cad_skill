# Caption-linked capped branch evidence

## Capped captions on an existing axis marker

Use `native_capped_marker_port_context.py --source SOURCE --graph GRAPH --output
NEW_DIRECTORY` and `--verify-output NEW_DIRECTORY` when the caption points to a
native `DIM_SYMB` polyline owning separate external-interface ports. Reuse the
existing underline/leader reader and native path coverage; require a complete,
unique current port population, original marker membership, independent service
ownership and exact adjacent source LINE contacts. Retain the unmeasured
node-centre display span separately.

The formal pipeline check is `pipeline.py validate-capped-marker-context
--context-run NEW_DIRECTORY`. It independently reloads the native sidecar and
retains pending topology, correspondence, physical lengths and HIL even when
all directly targeted marker ports have passed source comparison.

The common marker does not connect its ports. Source captions declare reserved,
capped boundaries, not equipment identity or a hydraulic supply/return link.
The declaration comes from the complete native caption and qualifier; the
zigzag itself retains only its drafting-omission meaning. Do not locate a
physical blind flange at the graphical marker or measure its omitted tail.
The source quantity is retained as text evidence; enumerate only existing,
source-checked ports on the directly targeted marker. Do not broadcast the
declaration to neighbouring markers or generate additional endpoints from the
quantity. Preserve native Z without interpreting it as physical elevation.

This is a read-only annotation sidecar. Local topology, main/detail mapping,
whole-edge DN/length, graph-bound review invalidation and final HIL remain
separate operations. Plan non-node boundaries and multi-leader captions need
their own source-bound owner; a missing unresolved-node candidate is not proof
that the source has no capped interface.

For whole-view discovery, use `batch_discover_capped_annotations.py --manifest
MANIFEST --output NEW_DIRECTORY` and independently replay with `--verify-output
NEW_DIRECTORY`. Each manifest view supplies an ID and hash-pinned `source` and
`graph` inputs. `discover_native_capped_annotations` enumerates native Chinese
caption/qualifier frames, connected leader chains and complete transverse bars,
then passes every proposed handle set to the existing strict collector. Missing,
competing or unsupported witnesses remain pending. No quantities become ports.
Existing axis external-interface ports need their own source owner; this plan
frontier reader must not retype them or treat zero accepted selections as proof
that the drawing has no reserved branch. Discovery is annotation evidence only,
not local topology acceptance, cross-view mapping or HIL acceptance.

Use `native_capped_branch_annotations.py` when native Chinese explicitly declares `预留支管接口/共N处` and `盲板封堵`, and a source LINE leader points to a complete two-bar marker near an unresolved pipe frontier. This fills a source-reading gap: marker projection can have a small offset from the pipe endpoint. Do not increase general endpoint snapping or reuse an expert-confirmed boundary policy for an unreviewed case.

The source/graph-pinned policy selects `node_id`, `pipe_handle`, two ordered `marker_handles` (long then short), `caption_handle`, `qualifier_handle`, and ordered `leader_handles` (caption to marker). Native modelspace TEXT and LINE only are supported. The reader checks the Chinese pair's placement in its own rotated/mirrored text frame, a connected leader chain reaching the outer marker centre, complete transverse unequal bars, a bounded outward projection from the source endpoint, one same-system incident graph edge and a unique native pipe-frontier interpretation. Record native XYZ and projected offset separately; projection is annotation evidence, not physical pipe contact.

The output is a source evidence inventory. It does not change nodes, edges, systems, equipment, mapping, DN or length; it does not expand the callout quantity into pipes or ports. An adjacent return marker does not inherit the supply marker's direct leader proof. A room name, similar bars, nearby text or a nearest endpoint alone is insufficient. A residual topology blocker stays until a separate semantic/connection stage has the required evidence.

CLI: `native_capped_branch_annotations.py --source SOURCE --graph GRAPH --policy POLICY --output NEW_DIRECTORY`. Independently replay with `--verify-output NEW_DIRECTORY`. Input and output hashes and the reader's hash are bound to the audit. Chinese must pass `source_readability` before extraction.

For a complete ceiling-plan run, `build_ceiling_family.py --capped-branch-annotation-policy-map MAP.json` accepts a task map whose values contain only `policy`. The family supplies the current final graph/source and owns the sidecar output under `reports/native-capped-branch-annotations`; the policy cannot override these paths. Run after normalization, ownership and wave recovery. Independently replay the actual source reader before writing the stage receipt. Final graph counts and existing unresolved statuses remain unchanged.

Tests: `test_native_capped_branch_annotations.py` covers native XYZ, projection offsets, rotation/mirroring, absent/unrelated Chinese declarations, incomplete leaders, competing frontiers and system/source drift. `test_capped_branch_annotation_stage.py` covers current-task ownership, exact input preservation, independent replay and refusal to close HIL. SH16-10 UT0192 is a direct-caption positive case; UT0095 remains outside that direct leader proof. This annotation capability is separate from SH16's project-only redundant-circle drafting erratum.

## Separate interface-role application

After independently replaying the actual topology parent and annotation inventory, `source_capped_branch_roles.apply` can classify a selected unresolved frontier as `source_declared_capped_branch_interface`. Require the exact current graph hash, unique same-system leaf and matching source endpoint. Preserve the node ID, position, source handles, all equipment/components and edge geometry. Reconcile only the endpoint subtype; retain the original node snapshot and source declaration. No nodes are retired, no connections or lengths are created, and quantity does not produce ports. Existing explicit ports, route claims or conflicting endpoint roles block application.

The direct source role can cease being an unknown source-terminal classification; it does not become a human-approved graph or establish an unseen remote route. Keep neighbouring return frontiers separate. Invalidate graph-bound comparison, mapping/attribute receipts and related human acceptance even when selected physical paths are unchanged. The annotation-only family flag does not implicitly perform this second stage. A project-parent adapter must replay its original topology owner and the annotation owner before applying the shared role kernel; do not feed the changed graph into an old ancestor verifier or inherit an old graph-bound receipt by hash substitution. Run `test_source_capped_branch_roles.py` and retain both local native checks and the formal-entry evidence separately.
