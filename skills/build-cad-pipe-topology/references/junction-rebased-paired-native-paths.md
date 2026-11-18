# Paired native-junction correspondence on the current plan

Use `match_junction_rebased_paired_paths.py` when a complete current native
corridor/inventory parent has replayed and older paired-service/interior-T
scopes must move to that plan version. This is the existing paired-service
method, distinct from three-equipment common-main order proof.

Pin the current corridor artifacts, original base/refined mapping artifacts,
original pair policy and original refinement policy. Reconstruct both services
for each independent equipment pair through `pair_paths`. Preserve context-only
equipment so that previously published branches are not counted twice. Match
interior Ts via their off-corridor branch to the first independently verified
equipment T with `native_paired_junction_correspondence.collect`, then refine
existing edges with the frozen `refine` kernel. Do not allocate by proximity,
index, label alone or an equal total edge count.

Recheck exact source coverage of all mapped mains. Compare source identity,
equipment roles, endpoints, paths and snapshots with both historical stages.
Unexplained changes block adoption and return to local source comparison.
New mapping IDs retain explicit historical lineage without transferring HIL.
No path may overlap the separately replayed current corridor writers.

`pipeline.py validate-source-crossview --mapping-run RUN` dispatches the new
mode to independent complete native replay. A pass stays pending/CLI exit 2:
recompute current DN/XY and compose the full parent before source comparison,
viewer publication and HIL. Named riser paths, earlier single branches and
whole-floor connectivity remain separate. Historical kernels stay unchanged.

Tests: `test_match_junction_rebased_paired_paths.py`,
`test_junction_rebased_paired_mapping_gate.py`, and the inherited paired-service,
native branch-target and path-refinement positive/negative tests.
