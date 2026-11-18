# Axis-anchored attribute sources, including local vertical runs

The expert rule applies to **every vertical pipe segment in the axis view**, not
only edges whose start and end floor differ. A same-floor vertical drop or rise
uses the axis drawing for DN and verified length evidence. Horizontal pipe
segments use the correctly matched floor plan for DN and physical plan length.
Axis horizontal annotations cross-check that match rather than choosing it.

Run `axis_attribute_source_routing.py` on the independent axis local graph, native
DXF and the established isometric horizontal-direction policy. Keep original
edge, path and segment IDs. Replay the native source coverage with
`--verify-output`. A direction inventory does not prove connectivity or fill DN
or length. Preserve source-unwitnessed and nonstandard-direction spans for their
original extraction/geometry readers; never force their direction classification.

Mixed graph edges retain horizontal and vertical domains separately. Floor
fields, equipment endpoint roles and edge totals do not decide which drawing
supplies a segment's attributes. Only its horizontal portion enters the floor
plan mapping queue. Vertical portions enter the axis annotation/level/dimension
queue, including same-floor portions. Do not send these to plan HIL because a
whole mixed-edge length or scalar DN remains unknown.

Reuse ordered/F DN readers, true-T inheritance and native axis segment/level
readers inside their actual source extents. A pipe level literal is not by itself
a verified physical elevation, datum or unit. Axis graphical vertical span also
is not automatically physical length. Report missing source evidence explicitly.

Report three scopes separately: pure horizontal edges still needing plan
attributes; horizontal portions of mixed edges whose exact coverage is pending;
and vertical segments needing axis attributes. Do not describe the sum of
incomplete whole edges as a count of unresolved plan correspondences.
