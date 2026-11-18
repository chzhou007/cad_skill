# Upper-floor plan attributes on original axis segment domains

Use `attach_upper_floor_plan_attributes.py` after independent upper-floor
mapping and plan DN/XY evidence. Compose over the complete named-approach
parent, not the raw axis graph. Freshly replay both source stages, then preserve
all previous equipment, plan and vertical attributes and the canonical component
CSV. Local geometry and node identities do not change.

Add `plan_segment_attributes` separately from inherited whole-edge attributes.
The record retains original axis path/segment indices and exact points, native
plan edges, DN lineage, measured XY pieces, named riser and independent device-T
anchors, source/graph hashes and the complete parent binding. An upper approach
must exclude the parent's checked vertical domain. Neither its horizontal DN
nor measured plan path can become a value for the whole mixed edge.

A network link can have complete horizontal-main DN and centreline route length
only when the current source mapping covers one existing full path between the
actual network and equipment Ts in each view. Both endpoints and edge floors
must agree. Plan chunks must touch exactly in order; every measured piece must
retain its original native identity and millimetre total. All axis segments must
follow explicitly configured nonplumb in-plane directions. A bent path is
supported; a plumb stroke, real gap, omission expression or detail domain cannot
satisfy this full-route contract. Net pipe cut length remains unknown.

The independent source verifier is `verify_output`. Formal source comparison
dispatches `upper_floor_plan_attribute_gate.check_upper_floor_plan_attribute_graph`
before retained roots, preserving the complete parent's issues. The viewer's
`upper_floor_plan_viewer_evidence.py` replays this composition before named/axis
parents, and reuses only that call's fresh ancestry. Pin the new stage audit and
the actual parent named-audit path; these files are in different directories.
An old consumer cannot silently display the named-parent state as if it
validated the new fields.
The source gate and viewer can share their first freshly verified result inside
one explicit `native_replay_session` process context. Actual read/stat/directory
dependencies are rechecked before reuse; changes rerun the native owner.
This does not persist trust between runs or replace source/HIL requirements.
`upper-floor-plan-segments.js` validates the original shape, separate vertical
domain, source bindings and metric/DN evidence before showing scoped properties
or CSV values. Human review remains pending after semantic changes.

Run the composition preservation/negative tests and segment display/export
tests, followed by the inherited upper-floor DN/metric, naming, crossing,
wave, component and parent-composition regressions. In SH16, the mixed
E0344/E0346 approach suffixes are DN300; complete E0428/E0544 main paths are
DN250. Only the latter may carry complete main centreline route lengths.
