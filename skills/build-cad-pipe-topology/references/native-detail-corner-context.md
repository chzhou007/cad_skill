# Native corner context with different vertical drawing clearance

Reuse `source_detail_frame_links.py` for its existing exact-translation mode.
If four original annotation LINEs describe the same-width upper/detail regions
but have different vertical clearance, use the separate
`native_detail_corner_context.py` reader. The old matcher still rejects this
case and must not receive a larger global tolerance.

Require explicit source/graph hashes, one nonpipe annotation layer, allowed
linetypes, four distinct native modelspace LINEs per frame, planar endpoints,
complete axis-aligned rectangles and preserved corresponding corner order.
Reject crossed corners, shared source lines, overlapping regions, nonfinite or
nonplanar inputs. Retain every native endpoint and both vertical corner offsets.
Offsets, rectangle height differences and drawing spans are not pipe lengths
or a physical scale.

This is regional drawing context only. Identical glyphs, left-to-right rank,
nearby lines and frame membership do not confirm a physical pipe connection or
individual identity. Preserve single-wave remote destinations until they have
separate source or expert evidence. A confirmed view relation then requires
local topology/edge reconstruction, current branch inventory, cross-view mapping,
DN/length recomputation and invalidated HIL as appropriate. Keep unknown device
ownership and nonmetric detail lengths unknown.

The standalone entry writes `corner-context.json` and its receipt.
`verify_output` rereads source CAD and independently reproduces the output;
it does not replay all local topology parents or establish a whole-drawing pass.
The caller must keep those acceptance scopes separate.

Run `test_native_detail_corner_context.py` with existing frame, boundary and
sideview source tests. On SH16 10 independently replay both real A/B source
frames, record the100-unit vertical clearance difference and inspect the native
overview and individual offset exceptions before HIL. This case extends an
existing frame-reading feature; it is not a new topology connection rule.


## Existing circle-rim topology before main/detail canonicalization

For a detail branch whose native pipe path already excludes the display-circle
radius, reuse `crossview_equipment_branch_inventory.native_tee` and its existing
source-reviewed/user-circle readers. They replay the pinned local source
confirmation, native three rays and original circle-rim path. A rejection by
`canonicalize_confirmed_sideviews.verify_tee` on such an edge can mean its older
witness schema is unsupported; it does not establish a disconnected pipe.
Do not add the radius to pipe length or relax contact tolerance to make that
older private reader pass. The current native source check must pass first.

Keep local T evidence separate from main/detail identity. A candidate needs an
explicit correspondence decision before a canonical topology can be emitted.
If source-calibrated ownership already retired the upper interface, use its
actual pinned preownership parent and then reconcile the confirmed aliases
with all retained ownership records and paired-wave continuity. Do not turn an
owned equipment node back into a disposable virtual endpoint in the active
graph, and do not promote a source-expression context into physical topology.
Recompute components, source coverage, inventory, mapping and attributes after
canonicalization; retain unknown physical connector lengths and HIL state.
