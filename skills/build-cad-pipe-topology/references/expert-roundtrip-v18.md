# Expert feedback, source repairs and calculation scope

Read for expert-pair remediation, near-contact repair, calibrated riser symbols or calculation projections.

1. Verify source hashes and rebase historical annotations through source bounds / entity handles. A matched source hash does not make old graph IDs current. Retain original comments and explanations; technical remediation never closes a human issue or confirms a new dataset.
2. Repair shared source rules before rebuilding families. Near-contact normalization must distinguish discovery from acceptance: unique same-class contact, dangling branch, angle and relative-length checks, protected equipment/valve/crossover spans. Audit both applied and pending candidates. SH16 uses discovery 10 / acceptance 3 drawing units, ratio 5%, angle 20 degrees; these are source-calibrated values, not general CAD tolerances.
3. A verified main crossing both sides of a package frame must survive package folding. Require a configured equipment role / system and physical through-path evidence. Internal package lines remain folded.
4. Two-bar capped display tails require the full calibrated pattern plus real base directions and no continuation. Never remove T nodes merely because their final degree is two. Circle-centered real three-ray contacts remain T nodes even near other symbols. A calibrated riser circle and unique radial typed pipe ending on its circumference can define an explicit virtual port. Unrecognized radii remain pending.
5. Inspect all source layers, but do not ingest a layer wholesale because some pipes appear gray. Sensor logic / pressure capillaries are not additional water links. Distinguish recognized unknown-service pipes from unresolved display context visually. Demonstrate claimed missing pipes against existing source-handle coverage before adding edges.
6. Run source-gap final-edge coverage, T direction / adjacency, component identity conservation, stable IDs, endpoint / explicit-port checks and localized native CAD comparison. Preserve pending discoveries and their evidence in the delivery, not only a success count.

## Separate calculation projection

`scripts/derive_hydraulic_graph.py --graph ... --devices ... --policy ... --output ...` creates a new graph. Pin the policy to `input_graph_sha256`. The current physical-equipment preservation policy supersedes the earlier quick-version auxiliary exclusions: exclude only proven meter/measurement branches. Preserve physical equipment, incident source connections and a component-conservation audit. Unknown service is not an exclusion policy. Convert only proven same-system degree-two pumps to edge attributes, preserving source paths, source handles, instances and old/new mappings. Real source T nodes that become calculation-scope boundaries use explicit virtual ports rather than misleading T labels. Do not claim that connectivity alone establishes flow, pipe sizing or solver readiness.

## Optional cross-drawing aggregate

Only after user authorization, `scripts/build_calculation_aggregate.py --config ... --output ...` composes hash-pinned task graphs without changing independent tasks or reviews. Qualify IDs by task. Split virtual multiports by explicit port; never short supply and return through a shared virtual owner. Keep actual equipment and edge components once. A plan and an isometric view of the same terminal network are alternative evidence, not additional equipment.

Every cross-drawing link records both ports, service, source intent, verification status and physical-length uncertainty. Counts and spatial order alone do not establish exact pairing. Store unverified mappings in `proposed_links`, outside proven edges, disabled by default in visualization. Never turn these logical links into invented native pipe lengths. Keep an aggregate-specific identity, source hashes, mapping table and validation report. Source tasks remain the scope for HIL and CAD Pair exports.
