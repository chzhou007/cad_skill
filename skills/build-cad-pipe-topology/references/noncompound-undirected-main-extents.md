# Complete plan main lengths without assuming drawing direction

A native LINE or polyline can be drawn opposite to node-ID order. Keep the
source point order, graph IDs and flow direction unchanged. Reuse
`native_main_endpoint_extent.qualify` to check both endpoint permutations and
the original axis horizontal-domain reader. A direction mismatch alone does
not invalidate native T-to-T centreline coverage.

Before applying this rule, carry compound declarations along their exact native
LINEs with `noncompound_main_extent_guard`. Empty declaration populations are
explicitly not applicable. A compound carrier must use its member owner; a
previous scalar DN or a matching axis DN cannot bypass that barrier. Preserve
the current qualified member context and every other existing attribute owner.

`rebuild_noncompound_main_extents.py --manifest MANIFEST --output NEW` replays
the current member owner, which itself reconstructs the exact original bounded
main and full mapping ancestry. Consume that freshly checked transitive parent
only after matching its hash; do not replay the same ancestry twice. Every new
main still rechecks both native paths, both endpoint Ts, the unchanged mapping,
qualified local plan DN and plan units/metric. This retains existing local DN;
it does not claim to rebuild global DN inheritance or discover new mappings.

Run `pipeline.py validate-noncompound-main-extents --extent-run NEW`. Mixed
paths, inline flexible assemblies, uncertain endpoints and unproved horizontal
domains retain their original metric owners or stay unresolved. Already
member-qualified intervals must not become new HIL questions just because
this separate noncompound reader declines them.

Use the versioned `refresh_noncompound_main_attributes.py` and
`validate-noncompound-main-attribute-refresh --bundle VIEWER` to expose lengths
on the existing axis graph. Only previously unknown complete T-to-T run length
or its normalized source columns may change; all DN and unrelated values must
remain equal. A pre-existing `crossview_whole_edge_length_mm` with kind
`floor_plan_horizontal_main_centerline_route` is already a known centreline.
Retain its exact value/kind and do not count normalization as a newly completed
pipe. Keep net cut and installed whole length unknown. Preserve old annotations
as history and invalidate related semantic confirmation. Native wide/local
Pairs and actual browser/CSV checks remain required before publication.

The earlier unpublished 14-main candidate included four compound-carrier
scalars. It remains quarantined. This entry inherits its direction predicate,
excludes compound carriers before qualification and preserves the independently
corrected member DN values.
