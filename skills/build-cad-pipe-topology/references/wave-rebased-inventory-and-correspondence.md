# Adopt a repaired local plan before reusing cross-view attributes

Use `wave_rebased_branch_inventory.py` after the independently replayed wave reconstruction. Its v4 receipt is distinct from the historical v3 inventory: do not rewrite the old graph hash or manufacture an old ownership receipt for the new graph.

```
python wave_rebased_branch_inventory.py --parent-inventory OLD_V3 --wave-run WAVE_RUN --policy POLICY --output INVENTORY
python pipeline.py validate-crossview-inventory --inventory-run INVENTORY
python match_wave_rebased_circle_paths.py --inventory-run INVENTORY --policy MAPPING_POLICY --output MAPPING
python pipeline.py validate-source-crossview --mapping-run MAPPING
```

The inventory policy pins `parent_inventory`, `parent_receipt`, `wave_graph` and `wave_receipt` SHA256. Replay both complete native parents; require the wave child to start from that exact old local graph/source. Equipment, real Ts, owner roots and all unrelated edges must be unchanged. Recheck native captions and every plan service on the new local graph using the existing ordinary-T or inherited-circle reader. Rebuild the active circle extension proofs too. A formerly ready branch becoming pending blocks this adoption. Preserve axis evidence only after replaying the old full inventory and verifying identical native axis, source and component inputs. Unmatched waves and missing equipment identities remain explicit.

The mapping policy pins the new `inventory` and `inventory_receipt` SHA256 and declares independent `groups`. Each group has `group_id`, `equipment_ids`, `floor`, `mapping_prefix`, exact `source_main_families` and `previous_mapping` (`path`, `sha256`). Recheck the existing common-anchor geometry kernel using a private dependency namespace: ordinary plan Ts call the historical native T reader, while explicitly typed duplicate-circle contracts use the inherited reader. Both recheck raw source evidence against the fresh inventory. Never mutate the shared kernel's globals or relax its source-family/order/coverage guards.

Run each independent corridor separately under its unchanged `4*N-2` invariant. A batch of three six-device corridors has 66 paths, not a fictitious single eighteen-device corridor. Reject shared equipment, repeated local writers and duplicate mapping IDs. Loading and verifying the native inventory and documents once per batch avoids repeating that work for each group; formal validation independently replays the whole batch.

Pin each historical mapping to the actual old wave-parent and unchanged axis/source version. Compare every path's endpoints, source edges and full local snapshots; emit old-to-current mapping-ID lineage and keep prior human annotations historical. A changed mapped path needs explicit reconciliation, not an automatic alias. SH16's original first twelve devices and newer six-device group have equal retention requirements.

The v4 inventory and new mapping receipt only establish current prerequisites/correspondence. DN, XY metrics, fusion, native comparison and HIL still need the new local version. Preserve the separately recorded plan DN150/axis DN80 extent difference; new correspondence cannot resolve it or transfer old engineering acceptance.

## Recompute plan attributes after correspondence

Use `wave_rebased_plan_attributes.py --mapping-run MAPPING --policy ATTRIBUTE_POLICY --output ATTRIBUTES` to independently replay the current mapping batch, then reuse the established inherited-circle DN/XY kernel for every corridor. A configuration is required for each group; incomplete batches, overlapping plan writers and repeated mapping IDs fail. Keep scalar through-T inheritance, explicit branch overrides, F ordering, native crossover exclusions, coincident-source manifests and independently corroborated plan units. A component-qualified DN label must use its dedicated entry; it must never silently become a pipe seed.

Run `pipeline.py validate-wave-rebased-plan-attributes --attribute-run ATTRIBUTES` for the independent formal replay. Success remains `pending`/exit 2 with `source_replay=passed`; argparse failure or exit 2 alone is not a pass. Check the parsed record count, group count and explicit unresolved fusion/HIL state.

Each group configuration records `group_id`, `scope`, `calibration_origin` and `metric_origin`. Origins pin immutable configuration paths and SHA256. The original calibration must belong to the exact wave-parent graph and unchanged native source. Every selected seed must be an unchanged explicit original selection. Recompute all native controls against the current graph; the new configuration hash is not an old acceptance receipt. Metric configuration supplies only the floor-plan window/title/native unit dimensions; do not inherit unrelated historical mapping or graph hashes as metric proof.

The output keeps independent group records, old-to-current mapping lineage and source hashes. Record historical DN lineage, source paths and XY differences separately from new scopes. Matching numeric values are regression evidence, not proof that an old receipt validates the child. Preserve all unrelated floor/vertical evidence when later composing; do not edit values directly on the final graph.

No stage here selects whole-axis DN or installed lengths, interprets parenthesized levels, resolves the DN150/DN80 view difference, or transfers HIL. Horizontal plan evidence and axis cross-floor evidence remain separate. Full local-topology, mapping and attribute replay, view comparison and composition must pass before publishing the new child.

## Compare the historical scopes as well as new scopes

Run `compare_mapped_plan_axis_diameters.py --attribute-run ATTRIBUTES --policy COMPARISON_POLICY --output COMPARISON`, then `pipeline.py validate-mapped-native-DN-comparison --comparison-run COMPARISON`. Pin the `attributes`/`attribute_receipt` hashes and explicitly select `axis_text_handles`. Replay the current attribute owner and independently recompute native axis annotation ownership using other source instances as controls. Targets must never calibrate themselves. Reject stale snapshots, repeated writers, system changes and missing independent controls.

Compare every current mapped path, including historical paths. SH16's broader comparison exposed the same local DN80 issue on the original24 device services as on the newer12: plan inherited values differ, while the plan's drawn fragment and the axis's labelled fragment have not been proved coextensive. Preserve both source values and their exact scopes. Different values block affected whole-axis DN fusion but do not by themselves prove a drawing contradiction or a physical reducer. Matching values do not prove matching extents. A path without a selected native axis annotation is unexamined, not agreed. Existing valid partial-plan attributes and unknown connectors remain intact.

Group the recurring extent issue for native comparison before HIL; retain original question text/options/answers and annotation history. Neither this comparison nor a topology-only expert answer settles an unshown change-of-diameter location. Full native/formal comparison, final fusion and human acceptance are separate states.

## Adopt current evidence without rewriting history

Use `axis_local_DN_segment_domains.locate` on the independently replayed axis ownership. Bind every label to one original path/segment and its native LINE chain; retain CAD stroke direction, graph floor fields and source coordinates. A same-floor vertical drawing stroke is not an inter-floor riser proof. Different floor metadata alone also does not establish the pipe's physical direction or length. Report a missing/competing domain explicitly.

`adopt_wave_rebased_plan_scopes.py --parent-graph PARENT --devices CSV --comparison-run COMPARISON --policy POLICY --output ADOPTION` replays the current comparison and complete lower-floor attribute parent, then adopts all current scopes. Its policy pins `parent_graph`, `devices`, `comparison`, `comparison_receipt` SHA256 and declares the exact `retained_historical_mapping_ids`. Validate it using `pipeline.py validate-wave-plan-scope-adoption --adoption-run ADOPTION`.

For an inherited attribute, require identical native local snapshots, systems, DN values, metric pieces and XY total. Preserve its original ID, provenance and historical receipt unchanged; add a separately versioned `current_plan_scope_evidence` backed by the freshly replayed mapping/attribute/comparison. Archive the exact prior attribute object in the new root. A changed old value needs explicit reconciliation. Do not relabel an old receipt as acceptance of the child.

For a new path, add only the verified drawn-plan DN/projection scope. Keep whole-axis DN, whole installed length and unseen connectors unknown until an extent stage proves them. Add independently owned axis DN domains as source evidence rather than overriding the horizontal plan value. Preserve nodes, components, all other floor/vertical attributes and historical annotations; invalidate related HIL. Native adoption is not viewer publication: source-gate and viewer dispatch must independently replay the new root before display/export or delivery.

The orchestrator's `wave_plan_scope_adoption_gate.py` runs before the retained lower-floor stage, independently replays adoption and preserves the exact lower-parent issues and pending states. The viewer's `wave_plan_scope_viewer_evidence.py` also dispatches before that parent; reuse only the lower/upper/named/vertical context freshly returned by this replay. Bind inherited audit files at their actual parent paths, not in the new child directory. Extend the proof list only for newly added attributes; keep historical mapping IDs and provider hashes intact.

`current-plan-scope-attributes.js` validates each current proof and native annotation domain against its edge and original segment points. Display/export current and historical mapping identities separately, along with the local axis annotation and its source chain. The existing plan DN/XY fields retain their meanings. Reject stale hashes, mismatched source/domain identities and physical-length or inter-floor claims. Check legacy properties/CSV as well as the new fields, then inspect an actual native-CAD browser view before publication.
