# Plan attributes on network-anchored named lower prefixes

Use `attach_network_named_lower_plan_attributes.py` after independently checked
`network_named_lower_plan_attributes` evidence. Compose over the complete
additional-main parent, retaining all previous equipment, plan, vertical,
component and source fields. Reuse `selected_path` and `plan_values`; do not
invent a single equipment anchor for this whole-network correspondence.

Each selected scope starts at original axis segment zero and stops exactly at
the existing cross-floor vertical tail. Require the same named column, system,
floor pair, native vertical source LINE and adjoining whole-network main proof.
Horizontal DN/XY comes from its plan; vertical DN stays from drawing11. Preserve
whole mixed-edge DN/length, unshown connectors and net cut length as unknown.

```
python attach_network_named_lower_plan_attributes.py --parent-graph PARENT/graph_with_edges.json --attribute-run SCOPES --devices PARENT/edge_device_instances.csv --policy POLICY --output OUTPUT
python pipeline.py validate-network-named-lower-plan-fusion --fusion-run OUTPUT
```

The policy pins `parent_graph_sha256`, `attributes_sha256`,
`attribute_receipt_sha256` and `devices_sha256`. The native root and its formal
validator replay both source owners. The source comparison dispatches this
root before the retained additional-main root and preserves the entire parent
comparison, including its errors. The viewer consumes only the freshly
replayed parent audit, verifies complete restoration after removing this root,
and reads the prefixes through the shared plan-segment property/CSV validator.
Legacy segment modes retain their original guards.

Run the composer, fusion-gate, viewer-ancestry and lower/upper segment tests;
include changed original paths, vertical boundaries, duplicate writers and
false whole-edge claims. A passing pure composer or property check is not a
completed native rebuild, publication or human acceptance. Rebuild source
comparison, portable viewer and actual browser/CSV checks before publication.
