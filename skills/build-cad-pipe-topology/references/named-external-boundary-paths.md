# Named external feeds and separate boundary ports

Use `native_external_port_destination.py` for an existing axis boundary node
whose native common marker has several named pipe contacts. Reuse the native
TEXT/underline/leader reader and exact XYZ line endpoint tests. Both `接至...`
and `接...` are supported when the literal destination matches the policy.
The destination leader may target a marker segment interior. Require every
native pipe contact, every graph port and every incident edge to be accounted
for; matching names or a shared destination alone do not prove correspondence.

Read the common marker and centre-to-port display span as annotation. They
create no port-to-port connection, physical pipe length or whole-edge DN. Do
not interpret the graph's historical `source_insert_handle` name as proof that
the source entity is an INSERT: this mode verifies the actual LWPOLYLINE.

After this read, `match_named_external_boundary_paths.py` independently replays
the whole-floor main mapping, plan and axis destination evidence, complete
plan inline-path coverage and the original explicitly confirmed axis gap-joint
owner. A route must agree in name, system, floor, destination, distinct port
and the already matched main T. The current axis feed must equal its original
replayed gap-owner edge. Only the exact marker display segment and confirmed
joint gap may lack native LINE coverage; any additional gap blocks mapping.
Retain all original answers and Pair bindings. Pipe interior/connector lengths
and external hydraulic connectivity stay unknown.

```
python native_external_port_destination.py --source AXIS.dxf --graph AXIS/graph_with_edges.json --policy PORT_POLICY --output PORTS
python pipeline.py validate-native-external-port-destinations --evidence-run PORTS
python match_named_external_boundary_paths.py --main-run MAINS --plan-destination-run PLAN_DEST --axis-destination-run PORTS --plan-inline-run INLINE --gap-run ORIGINAL_GAPS --policy MAPPING_POLICY --output MAPPING
python pipeline.py validate-named-external-boundary-paths --mapping-run MAPPING
```

Policies pin all canonical data/receipt pairs by SHA256. Native correspondence
does not reclassify nodes, fuse plan DN/length, accept whole drawings or close
HIL. Those remain explicit subsequent stages. Run the native port, external
path and formal-gate tests alongside existing named-riser, external-destination,
inline-path and confirmed-gap tests. Include rotation, wrong colour, duplicate
ports, wrong T, extra pipe/branch, changed reviewed route and unexplained gaps.
