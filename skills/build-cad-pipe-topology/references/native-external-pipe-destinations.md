# Native grouped external pipe destinations

Use `native_external_pipe_destination.py` when pipe ends share a drawing break/group marker and a caption such as `接至室外冷冻站`. A readable destination must not remain an unspecified destination merely because the pipe continues outside the drawing. The marker does not connect its member pipes.

Replay the native caption TEXT, its unique underline and LINE leader to an exact interior vertex of the selected open LWPOLYLINE marker. Replay each qualified pipe name's separate text/underline/leader chain to that member's own native pipe endpoint. Require unique graph node/incident-edge/source-LINE ownership, consistent supply/return layers and one floor. Check all native pipe endpoint contacts with the complete marker; a missing member, extra pipe, duplicate source or leader ambiguity blocks the evidence.

Reuse the existing readable TEXT, named-caption, underline and XYZ geometry helpers. The current mode supports modelspace positive-OCS TEXT, straight annotation leaders and an open zero-width, zero-bulge LWPOLYLINE marker. Nested, mirrored-glyph, negative-OCS or unsupported marker forms remain explicitly unsupported in this mode; other historical readers keep their existing transform support. Do not experiment on unreadable Chinese.

SH16 08 has four source-declared station interfaces: CHWS1/CHWR1/CHWS2/CHWR2, caption2A1D0 and marker2BAFC. The exact name leaders reach UT0013/UT0001/UT0014/UT0002 respectively. The sidecar records `室外冷冻站` for all four, preserves each service and source endpoint separately, and assigns no new graph connection, physical port, whole-edge DN or length. A local DN450 name observation is retained without propagating it along the whole route.

```
python native_external_pipe_destination.py --source SOURCE --graph GRAPH --policy HASH_AND_NATIVE_HANDLE_POLICY --output NEW_RUN
python pipeline.py validate-native-external-destinations --evidence-run NEW_RUN
```

The formal command independently replays original CAD evidence. Exit2 distinguishes known source destination from unresolved physical external connectivity, semantic adoption and cross-view path mapping. Do not delete endpoints or merge supply/return at the common annotation. Source destination evidence is useful before HIL and does not itself change graph counts or human acceptance.

Run `test_native_external_pipe_destination.py`, `test_native_external_destination_gate.py` and existing native named-caption tests. Cover rotation, wrong pipe colour/layer, moved leader, incomplete marker membership, added native pipes, wrong XYZ, equipment mistaken for boundary, text-transform rejection and forbidden physical claims.
