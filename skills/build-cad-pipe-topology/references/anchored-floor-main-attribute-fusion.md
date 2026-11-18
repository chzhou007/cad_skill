# Fuse additional anchored floor mains into the complete axis graph

Use `attach_anchored_floor_main_attributes.py` after the complete-floor mapping and native DN/XY attribute owners pass. This extends the entire verified axis parent; it is not an isolated replacement graph.

Require identical current local nodes, edges, geometry and component fields. Replay both the complete parent and the attribute owner. Retain old corridor/named main DN and XY values and add only mapping IDs absent from those historical scopes. Overlapping attribute writers, changed local hashes or altered old values block composition.

The per-edge `anchored_floor_main_attributes` field and `sourceAnchoredFloorMainAttributes` root carry the same records. A known DN is plan-derived and includes its native through-T lineage. A conflict retains null plus both source chains; do not choose a maximum or replace it with a local axis label. Whole installed/net-cut lengths remain null. Inline marker interiors are not counted as pipe length; such records cannot claim a complete horizontal centerline route.

Prove both endpoint Ts, one floor and the explicitly declared nonplumb axis directions before assigning a main-wide plan value. Cross-floor vertical evidence stays in its original independent SH16 11 fields. No nodes or edges are added by this stage.

```
python attach_anchored_floor_main_attributes.py --parent-graph GRAPH --attribute-run RUN --devices CSV --policy HASH_AND_DIRECTION_POLICY --output NEW_RUN
```

The source-comparison and viewer dispatchers must select this root before its retained wave/lower ancestors. Independently reconstruct the new output and reuse only the freshly verified complete parent audit when assembling viewer ancestry. Compare against the exact parent comparison report and preserve its unresolved issues. Changing semantic attributes invalidates current HIL; retain prior annotations as history.

The native worker supports the fixed `build_anchored_mains` operation and an explicit `anchored_floor_main_attribute_stage` source-gate expectation. It calls the original owner and checks the fixed predicted output hash; no verifier results are cached or substituted.

Viewer properties and CSV read the same checked field. Show unknown conflict DN and both lineages, pipe-only XY and the explicit inline exclusion. Keep every prior property/export field unchanged. Test source-gate priority, lost parent values, forged per-edge/root evidence, plumb/cross-floor rejection, conflict and inline partial lengths, and prior CSV compatibility.

SH16 floor1 integration case: preserve 26 old mains and add 30; 28 new DN are known, 2 stay in conflict, and 4 lengths exclude inline interiors. This scope does not prove the remaining floor1 interfaces, other floors, LF20 generalization or human acceptance.
