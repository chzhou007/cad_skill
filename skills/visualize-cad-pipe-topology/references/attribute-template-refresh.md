# Refresh attribute presentation without reconstructing an unchanged graph

Use `scripts/refresh_attribute_templates.py` after a qualified portable viewer
exists and only `edge-attributes.js`, `full-batch-plan-attributes.js` and their
`app.js` attribute-context bootstrap/CSV calls need to change. Supply `--parent`,
the exact original `--graph`, `--devices`, `--source`,
`--legend` when present, `--comparison`, `--templates` (viewer template root),
new `--output` and `--port`. Existing output/ZIP paths are refused.

This is reuse of an immutable rendered artifact, not a cached flag authorizing
a new topology result. Parent schema/native fidelity, original comparison and
all primary native-input hashes must qualify it. Any graph, component or source
change requires normal reconstruction and source-owner validation instead.
Keep all inherited pending source scopes; this entry never certifies full graph
correctness, pipe lanes, correspondence or physical attributes.

The entry verifies the old template bytes, copies the artifact, replaces only
the declared attribute templates and evaluates actual CSV attributes for every
edge. It gives the resulting effective attributes a review-content hash and new
bundle identity. Historical annotations remain byte-equal under their old
identity; human confirmation does not carry across the semantic presentation
change. All native graph/CAD/component payloads remain byte-equal.

Native bundle schema and post-render fidelity run again, without re-running the
topology family's ancestors. The output records explicitly that source-owner
comparison was inherited, not newly replayed. Run `--verify-output BUNDLE` or
`pipeline.py validate-attribute-template-refresh --bundle BUNDLE` to independently
reproduce the complete artifact. Then verify actual browser properties, CSV,
Chinese, source CAD and portable startup before publication.

Operational `startup-logs` may change during diagnosis and are excluded from the
artifact's semantic snapshot. Original annotation files remain protected;
additional notes under the new dataset identity do not change native content.

Never refresh an old viewer with a different graph merely because edge counts
or IDs match. The SH16 576-edge integration fixture preserves the old 142 known
DN values; it is a tooling check, not publication of the new full-batch fusion.
That fusion gets its own refresh only after its actual viewer build qualifies.

For a full-batch graph also supply its original `--group-policy`. Its hash must
match the qualified parent manifest. The [uniform path DN reader](uniform-path-group-DN.md)
may assign known uniform DN to complete horizontal children, while leaving the
group length unallocated. Native geometry/graph changes still require normal
reconstruction; the bootstrap binds the context to the actual rendered bytes.
