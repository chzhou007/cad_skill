# Mixed axis edges and through-riser DN scopes

An axis edge may contain a floor-horizontal approach, a cross-floor vertical
stroke and another horizontal approach. A DN beside one stroke never assigns
the entire mixed edge. Use `native_axis_riser_DN_scopes.py` after freshly replayed
`native_segment_dn_candidates_v2.py` observations.

Keep both local graphs immutable. Split only a private attribute projection at
the original bends. Its cut IDs are not physical nodes and create no new pipe
length. Require the original middle T, exactly three same-system native rays,
two arms on the same uniquely covering source LINE, an independently identified
non-through branch and the declared adjacent floor spans. Do not propagate
through ordinary crossings, another system, unresolved Ts or private bend cuts.

Reuse `checked_plan_DN_scope_attributes.attribute_checked_scope` and its original
source coverage, F/leader inventory, direct-change checks and DN inheritance.
Exclude only the actual non-through branch frontier from main backflow. A new
direct DN is a boundary; conflicting or compound labels block the scope.
Horizontal portions retain their separate floor-plan DN and length domain.

Nearby device DN can overlap a riser in projection. Resolve it before inheritance:
`native_repeated_branch_DN_layout.py` requires at least four other clear native
instances of the exact block child, text profile, rotation, root linear pose and
signed normal offset. The target cannot teach itself. Recheck all modelspace and
nested competitors, native Z, the control along-line range and one current
source-backed branch owner. A different pose, unresolved owner or two matching
layouts stays unresolved. This scoped rule does not relax the existing generic
two-direction calibration, discard a whole block or select the nearest pipe.

`native_scope_leader_isolation.py` checks every native LEADER and its connected
same-layer straight annotation component. Only components that cannot reach
the declared scope may be omitted from the inherited unsupported-entity loop.
The original document and native queries remain intact. References, curved or
unknown geometry, connected strokes reaching the scope and nearby unresolved
DN remain blockers. Other source catalog checks remain unchanged.

The output records local edge/segment IDs, source LINE, exact scope points,
direct or T-inherited DN and its source chain. It assigns neither whole mixed
edge DN nor installed length, accepts no plan-riser port mapping and performs
no final graph fusion. Run `pipeline.py validate-axis-riser-DN --diameter-run ...`;
a successful independent source replay remains pending/exit 2 for those later
stages. A source or implementation change invalidates the dependent scope.

Tests: `test_native_axis_riser_DN_scopes.py`,
`test_native_axis_riser_DN_entry.py`, `test_native_repeated_branch_DN_layout.py`,
`test_native_scope_leader_isolation.py` and pipeline
`test_axis_riser_DN_gate.py`, together with inherited segment, text, F, T,
display-normalization and component checks.

SH16 evidence: four upper native DN450 seeds extend across the four actual
middle Ts to eight vertical-only scopes. Four crowded DN80 labels bind to
other device branches using 34 independent native instances per role. Eleven
native LEADER components remain outside these selected scopes. Preserve these
counts as case evidence, not universal thresholds beyond the stated rule.

Vertical physical dimensions come from explicit axis annotations and verifiable
axis elevation/dimension evidence. The expert's instruction to use drawing 11
does not confirm that parenthesized horizontal numbers mean pipe-centre heights.
Do not reinterpret that reply, measure drawing pixels or borrow plan XY lengths
for the vertical domain.
