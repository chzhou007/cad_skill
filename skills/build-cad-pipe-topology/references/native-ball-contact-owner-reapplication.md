# Physical valve ownership is separate from equipment membership

After independently replaying the complete native component inventory, run
`reconstruct-native-ball-contact-owners` and `validate-native-ball-contact-owners`
to scan the entire known H-PICPNT-91 ball-valve family. Reuse the original
three-LINE/two-bulge signature and its WCS/negative-OCS circle centre. Find the
unique parallel flange pair, require the circle to lie between the flanges and
within their actual footprint, and use the shared double-flange contact kernel.
Do not require the symbol's slightly offset circle centre to coincide with the
flange midplane. Source geometry, not an enlarged snapping radius, supplies the
contact domain.

Require a unique same-Z source pipe, unique current graph owner and unique prior
component claim, retaining system, source-handle and original-continuity guards.
Two actual flange contacts prove physical ownership more directly than nearest
centre distance. A nearer perpendicular branch can pass through the symbol's
centre without owning its two flange ports. Duplicate source/graph owners,
unsupported geometry, unclaimed symbols, conflicting prior types or a previous
pipe-system conflict remain explicit and unchanged; this owner does not guess.

When the unique physical owner differs, conserve the component's identity,
equipment membership, type and unknown parameters. Keep original x/y and source
symbol geometry. Change the assigned pipe and contact assignment point, record
the complete before/after rows and native contacts, and retain the old edge as
history. Do not move the component back to an equipment branch merely because
its name or owner_equipment refers to that device. The two relationships answer
different questions.

Batch reapply the existing topology matcher with the corrected inventory. A
newly agreeing component profile is a candidate gate, not a new connection proof.
Independently requalify **all** affected old ordinary/member mapping scopes and
new complete native T/path scopes before adopting the correction or new matches
in a viewer. Preserve topology, old source attributes and annotation history;
invalidate related semantic confirmations. Do not discard old DN/length values
or claim new completions merely from a private profile experiment. Resolve an
old source-stage defect at its owning stage and recompute downstream outputs.

SH16 source fixture: scanning all 456 known-family axis symbols finds 12
equipment-labelled valves whose full flange contacts lie on supply mains rather
than their old equipment branches. The private inventory enables four bounded
path candidates, while 23 already mapped edge scopes require requalification.
These counts, handles and IDs are regression evidence, never recognition rules.
Keep the remaining ambiguous graph owners visible rather than forcing coverage.
