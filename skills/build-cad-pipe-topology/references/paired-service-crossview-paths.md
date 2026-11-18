# Paired-service cross-view paths

Use `match_paired_service_crossview_paths.py` for a native corridor containing two
uniquely identified equipment, each with **both** independently source-checked
supply and return branches in each view. This is a distinct proof from the
existing three-anchor main-order method; keep that method and its negative
two-anchor tests unchanged. Matching two labels or a straight geometric line
alone is insufficient.

First replay `crossview_equipment_branch_inventory_v2` on the current native
sources, local graphs and component inventory. Require complete local ownership,
caption, service route, endpoint and three-ray T evidence for all four services
per view. Recompute the graph service routes and recheck native Ts at this entry.

For each system, find one unique native modelspace LINE covering both main Ts.
Use the existing source-corridor and bridge-path helpers; duplicate, disconnected,
parallel/cyclic in-corridor paths, wrong floors, unresolved Ts, shared anchors or
mixed systems fail. Supply and return must remain separate. Opposite-system
crossings never provide a connection. Rings outside the native corridor are not
asserted to have one globally unique route.

Replay any intermediate actual main T against native source. A true extra branch
in only one view requires local topology investigation. Source-covered degree-two
subdivisions may differ between views. Correspondence is path-to-path and does not
claim correspondence of off-corridor branches at intermediate Ts.

`context_only_equipment_ids` retains all that equipment's native checks but emits
no new branch writer for it. Use this for an already published reference device;
do not delete its existing attributes or count it as a new mapped device. New
main intervals still include that reference's exact existing T. Reject repeated
pairs, overlapping claimed paths and a pair containing only context devices.

The versioned `source-mapping-receipt.json` has mode
`source_checked_paired_service_paths_v1`. The pipeline
`validate-source-crossview --mapping-run ...` independently replays it and stays
pending for DN, length and broader review. It does not create an expert answer,
change either local graph, accept physical ports or transfer axis strokes as
horizontal lengths. Attribute fusion must explicitly support this proof type;
do not disguise it as three-anchor main-order evidence.

Run the new native pair/negative tests and pipeline dispatch tests, inherited
three-anchor tests, endpoint inventory and plain-crossing/system-isolation tests.
Then rebuild the current SH16 paired scope and verify that its writers do not
overlap the published attributes. Source comparison and current DN/length fusion
remain separate gates.
