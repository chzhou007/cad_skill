# Inventory attribute records across all supported carriers

Use `scripts/attribute_scope_inventory.py` in delivery/postcondition checks when
reporting preserved plan attributes. Count the five supported carriers together:
`cross_view_attributes`, `anchored_floor_main_attributes`,
`external_feed_plan_attributes`, `network_named_lower_plan_attributes`, and each
record in `plan_segment_attributes`. A mixed edge can carry several records.

Do not equate this total with the number of edges or with the first field alone.
SH16's published302 record scopes comprise 258 cross-view objects, 30 anchored
main objects, four external-feed objects, two named lower-prefix objects and
eight segment records. Original vertical scopes stay in a separate eight-record
inventory. Current source-evidence sidecars update provenance; do not count them
as another136 physical pipes or plan attribute scopes.

```
python attribute_scope_inventory.py --graph GRAPH.json --output NEW_INVENTORY.json
```

The utility checks carrier shapes and stable edge IDs, records canonical payload
hashes and distinguishes record counts, owning-edge counts and evidence counts.
Equal counts do not establish equal attributes: compare payload signatures and
the complete parent graph. Unknown DN/length values stay unknown and still
belong to their stored record. This structural inventory does not certify source
geometry, physical lengths or HIL.

Run `test_attribute_scope_inventory.py`, then check the actual completed raw and
viewer graphs. A failed reporting assertion must not trigger another expensive
native rebuild when the source gate and native viewer already have genuine
passing reports; preserve those reports and repair only the postcondition.
