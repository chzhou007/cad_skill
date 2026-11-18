# Reapply specific native plan providers before treating generic unknown as HIL

The inherited circle/common-anchor provider already reads calibrated DN,
through-T inheritance, native canonical main families and plan XY metrics.
A full-plan table may still mark coincident source LINEs as unverified because
its single-LINE reader is deliberately stricter. Do not reimplement the
historical reader or discard its supported scope because the generic table is
unknown. Inspect the existing provider and its original controls first.

Use `rebuild_qualified_plan_scope_extension.py` to reconstruct the existing
provider against current native plan and axis parents. Old receipts can become
invalid when implementations change; a prior pass flag or hash substitution is
not a current replay. This version calls the original service/T, common-anchor,
canonical-source-family, calibration and attribute kernels anew, then compares
historical values and current complete node/edge snapshots. Every raw source
entity and the uncertainty about physical pipe multiplicity remain preserved.

Apply a freshly proved specific provider only to the same current one-to-one
horizontal T-to-T mapping whose generic DN is unknown. Explicit current
conflicts, contradictory known DN, changed source extents, parallel writers,
mixed/vertical paths and equipment branches remain separate. Do not use DN to
select a correspondence or move DN80 from an axis vertical branch onto the
floor-plan horizontal main. Preserve both old and current mapping IDs as
lineage; no ordinal reassignment or automatic HIL inheritance is allowed.

The native manifest pins original provider/configuration origins, current
graphs, sources, component inventory and current mapping. Use
`reconstruct-qualified-plan-scope-extension --manifest … --output NEW`, then
`validate-qualified-plan-scope-extension --scope-run NEW`.

`qualified_plan_scope_context.py` and the versioned
`refresh_qualified_plan_scope_attributes.py` compose the new horizontal scopes
as an independent context. Existing member and vertical contexts stay exact.
The compatible UI reader selects the proof from that context, not an unrelated
old root. Plan centreline includes inline extents; installed/net cut lengths
remain unknown. `validate-qualified-plan-scope-refresh --bundle …`, native
wide/local Pairs and actual properties/CSV checks precede publication.

SH16 motivating case: the existing provider supports the six-equipment DN150
main family and twelve branches. Its ten T-to-T mains can be exposed separately;
the twelve branch horizontal/vertical domains must not be promoted wholesale.
This is inherited reader reapplication and provider precedence, not a new
duplicate-LINE-to-physical-pipe inference rule.
