# Lower-floor plan segment fusion

Use `attach_lower_floor_plan_attributes.py` after independently checking the lower-floor correspondence and plan DN/XY scopes. The parent is the complete upper-floor composition, not a local child graph. Preserve its legacy plan values, upper segment values, vertical evidence, topology, component inventory and review history.

```
python attach_lower_floor_plan_attributes.py --parent-graph .../graph_with_edges.json --attribute-run ... --devices .../edge_device_instances.csv --policy ... --output ...
```

The policy pins parent graph, source scope, scope receipt and component CSV SHA256, and declares the independently established nonplumb isometric horizontal directions.

## Scope and source rules

- A lower approach is the original path prefix immediately before exactly one checked final vertical segment. Require matching original indices, points, floor start/end and vertical floor pair. Never replace the mixed edge with a new horizontal edge or assign its whole-edge DN/length.
- A complete horizontal main can take plan DN and centreline route length only after native same-floor T endpoints, exactly touching plan pieces and the full axis path are checked. A bend remains geometry, not a new equipment/T node. Net pipe cut length and unseen connectors remain unknown.
- Reuse inherited T-based diameter propagation. Explicit branch changes do not backflow into a main. A qualified riser name is a separate vertical domain, not a horizontal DN seed.
- The floor-plan source supplies horizontal values. Drawing 11 supplies cross-floor vertical evidence. Do not convert bracket numbers into pipe elevations without independent evidence, or interpret the user's instruction about source selection as confirmation of that meaning.
- Reject an existing writer on any selected edge. A new graph must keep all unrelated upper, plan, vertical and component fields exactly. Semantic additions invalidate related HIL confirmation while retaining historical annotations.

## Formal consumers and replay cost

The root is `sourceLowerFloorPlanSegmentAttributes`; `lower_floor_plan_attribute_gate.py` and `lower_floor_plan_viewer_evidence.py` dispatch before the retained upper root. They directly reproduce the new root. Only its two independent children use bounded, same-process `verify_once` reuse; every root call rechecks those child closures and rebuilds/comparers the root. Do not cache this nested root until nested dependency capture is supported.

Source comparison requires the exact complete upper-parent report and preserves every prior error and pending scope. The viewer binds the lower audit, the actual upper-parent audit and the actual named-parent audit. `upper-floor-plan-segments.js` validates both upper and lower scopes using their separate floor/original-segment contracts. Properties and CSV expose scoped DN, source metric pieces and lineage; scalar mixed-edge values remain blank.

Run `test_attach_lower_floor_plan_attributes.py`, `test_lower_floor_plan_attribute_fusion_gate.py`, `test_lower_floor_plan_viewer_evidence.py`, `test_lower_floor_plan_segments.mjs` and the registered inherited union. The first includes source-change invalidation across repeated root reconstructions. Then independently replay the actual composition, run formal comparison, build the viewer and check real browser/CSV/Chinese display before publication. Unit or in-memory composition success is not native replay, publication or human acceptance.
