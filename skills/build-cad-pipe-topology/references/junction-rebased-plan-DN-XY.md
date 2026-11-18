# Current native-junction corridor DN and XY

After `junction_rebased_plan_DN_scopes.py` has rebuilt the current DN scopes,
run `junction_rebased_plan_attributes.py --diameter-run RUN --policy POLICY
--output OUTPUT`. Its policy pins both DN artifacts and one original metric
policy per current group. Each original metric policy must identify that
group's exact historical mapping hash. Identical source units do not make a
detail drawing measurable.

The entry independently replays the complete DN owner, including current
inventory/mapping and original native calibration fragments. Only this closed
parent replay permits reuse of its exact mapping bytes within the same call.
It then rereads the native DXF, Chinese floor title and original independent
dimensions, and reuses `metric_context`, native path coverage and
`confirmed_detail_projection.projection`. Every DN path must equal the current
mapped source path. Group coverage, supply/return counts, unique writers and
unknown connector lengths are mandatory.

Confirmed detail spans retain their native geometry and source context but
their physical lengths remain unknown. Floor-plan XY projections exclude
unshown connections; wave omission distance, circle radius, symbol interiors,
axis drawing spans and parenthesized values are not added. DN conflicts remain
unknown rather than zero. This source stage does not change either local graph
or fuse values into the published axis graph.

`pipeline.py validate-junction-rebased-plan-attributes --attribute-run OUTPUT`
independently reconstructs the output. A successful replay returns pending
(CLI exit 2): complete-parent replacement/fusion, other mappings, source
comparison, viewer rebuilding and HIL are separate requirements. Preserve old
annotations as history; source version changes do not transfer human approval.

Regression: `test_junction_rebased_plan_attributes.py`,
`test_junction_rebased_plan_attribute_gate.py`, plus the inherited metric,
detail, DN, coverage and source-attribute tests. Keep historical collectors
and their implementation-bound receipts unchanged.
