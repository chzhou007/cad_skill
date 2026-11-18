# Paired plan DN and attribute scopes

Use `paired_plan_DN_scopes.py` after the independently replayed paired-service
mapping. Do not send a two-device corridor to the legacy three-anchor DN entry
or invent a third device. That legacy entry and its historical receipts stay
unchanged.

The new topology contract replays the exact current plan route and native
through LINE for each service. At equipment Ts, the two through rays must be
distinct from that equipment branch. At intermediate actual Ts, replay the
three native rays and keep the off-corridor network branch out of main-DN
propagation. An annotation on that branch cannot backflow into the through main.
Unknown degree-two normalization and unsupported source-specific T schemas remain
explicit failures rather than automatic DN propagation.

The shared `checked_plan_DN_scope_attributes.py` retains the established scalar,
F-leader, qualified-component, annotation-frontier, override and inheritance
algorithm. Its legacy positive cases are byte-compared against the old entry,
including rotation and mirror cases. The new contract supplies the independently
checked Ts and explicit non-through frontier exclusions. Main seed values come
from exact native TEXT/LINE selections; reuse calibrated text-side controls only
when that source/profile requires them. Re-read every visible nearby DN change
mark. Conflicts, unsupported leaders and compound labels cannot be interpreted
as absence of a change.

Annotation frontiers are read-only source fragments from a checked T to its
literal annotation or first bounded source segment. They never assign a whole
unselected feeder's diameter. Equipment branch labels override inherited main
DN without changing the main. Missing or conflicting values remain unknown.
Parenthesized source values are retained without converting them to lengths.

`pipeline.py validate-plan-DN --diameter-run ...` dispatches
`paired_service_plan_DN_scopes_v1` to independent native replay. This accepts no
cross-view allocation, equipment connector or HIL state.

`attach_paired_plan_scope_attributes.py` builds a separate attribute child on the
same common confirmed-attribute parent as the existing floor scopes. Consume the
independently replayed paired DN evidence, exact mapping and component inventory.
Reuse native floor/title/mm/dimension checks and path projection. Reuse the
existing DN extent fusion: only proved one-to-one horizontal T-to-T mains can
receive a whole centerline length. Multi-edge route totals are not repeated as
individual edge lengths. Unshown equipment ports, drops and connectors stay
unknown. The proof basis is `native_paired_service_corridors`, not the legacy
three-anchor main-order basis.

The attribute scope uses receipt mode `paired_service_plan_attribute_scope_v1`.
It preserves the common parent's confirmed attributes and all local geometry,
IDs, equipment and components. It is **not** the complete published presentation:
compose it with every prior checked scope before replacing the current viewer.
Preserve prior annotations as history; do not inherit their human acceptance.

`compose_paired_plan_attribute_scope.py` independently replays the current
multi-floor base and the paired child on their exact common parent. It adds only
new writers, preserves every old attribute value and local source root, and
stores a separate `pairedServiceCrossViewAttributeFusion` root with receipt mode
`paired_plan_attribute_extension_v1`. Missing or overlapping writers and changed
equipment/components/geometry fail. The earlier multi-floor proof stays intact.

The source-comparison entry dispatches this outer layer before older attribute
roots. Supply the exact prior base's `source-comparison-gate.json` as comparison
context. After independent native replay and exact preservation of prior local
data/attributes, retain that prior comparison with every error and pending item;
bind its hash and parent graph. This reuse does not replace native replay, accept
the whole drawing or transfer human acceptance. Missing, changed or mismatched
context fails. The viewer likewise replays the outer stage first, checks that
the verified base audit remains unchanged, and retains both proof sets while
following their common ancestor. Partial uncomposed children cannot enter this
presentation path.

Run the new DN-kernel parity and branch-backflow tests, paired topology tests,
paired attribute/one-to-many tests, pipeline DN dispatch tests and the inherited
DN/F/qualified-label/metric/composition tests. Native scope production, formal
replay, combined source comparison, viewer validation and human review remain
separate evidence.
