# Exploded endpoint evidence inheritance

Use this reader when a current axis branch already has one logical equipment
owner and a native upstream T, but inventory reports `axis endpoint needs
supported native joint-chain evidence`. That message can be an unsupported
evidence schema rather than a CAD connectivity defect.

`native_exploded_endpoint_evidence.py` replays selected modelspace LINEs,
equipment CIRCLE and the existing two-bar/four-arc flexible-joint definition.
Require unique contacts, actual XYZ, unique assigned component, native equipment
caption and the unchanged unknown equipment-anchor segment. Every other path
segment and all three upstream T rays require native witnesses.

For an off-centre circle contact, reuse **all** applicable offset controls from
the existing native-block reconstruction, its pinned historical policy and
audit. Re-read the transformed native children and current endpoint snapshots.
Require at least four independent INSERT instances matching the local-frame
radius, pipe length, signed offset, Z and joint-span profile within the existing
coordinate tolerance. Keep the inherited radius bound (at most 0.2); do not
enlarge it or snap the source endpoint to the circle. Rotations are tested.

A wrong-colour inner LINE is supported only by the exact edge-local **and**
root-level previously user-confirmed upstream-resolution record. Replay its
same-system route from the native T to the joint, recorded source LINEs, original
colours/XYZ and component owner. The general rule does not authorize an
unconfirmed colour change, merging supply/return, a different joint or a guessed
physical port. Preserve the erratum history and unknown connector length.

`crossview_equipment_branch_inventory_v2.py` adds the reader after independently
rebuilding the inherited inventory. It may replace only that exact unsupported
axis-chain reason, with identical coverage and native T evidence. Plan-side
failures remain failures. All previously ready equipment records and unselected
services remain unchanged. The versioned receipt is dispatched by
`pipeline.py validate-crossview-inventory --inventory-run ...`; verification
recomputes native evidence, not just receipt flags. Historical inventory receipts
continue to use their original entry. This stage creates **no correspondence**,
connection, owner, physical length or HIL acceptance.

Run `test_native_exploded_endpoint_evidence.py`,
`test_crossview_equipment_branch_inventory_v2.py`, inherited inventory/native
joint/coverage/colour-repair tests and the pipeline inventory gate. Then rebuild
08–10 inventories from current source inputs and compare every previously ready
record and unselected service. New correspondence and DN/length fusion require
their own current receipts; a newly readable branch is not yet a mapped branch.
