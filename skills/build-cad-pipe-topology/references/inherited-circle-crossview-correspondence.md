# Common-anchor correspondence for inherited circle inventories

Use `match_inherited_circle_crossview_paths.py` after the independently replayed v3 inherited-circle inventory proves both services of at least three equipment instances in both views. It reuses the existing unique logical bridge, pairwise common-anchor order, selected snapshot and native coverage kernels. Source-ready equipment names alone are insufficient.

```
python match_inherited_circle_crossview_paths.py --inventory-run ... --policy ... --output ...
python pipeline.py validate-source-crossview --mapping-run ...
```

The policy pins inventory and receipt SHA256 and declares `equipment_ids`, integer `floor`, stable uppercase `mapping_prefix` and `source_main_families[view][system]` (`canonical_source_handle`, `coincident_source_family`). It must match freshly replayed per-anchor provenance; never populate a family by nearest geometry or by accepting an unexpected extra LINE.

## Canonical source-family view

`native_canonical_main_family_view.py` checks the complete native XYZ family, service layers, all anchor positions, current source/graph hashes and both through-ray source owners at every anchor. Every native LINE covering the anchor set must be explained by that same family. Only then may a private read-only query view expose the canonical graph source owner to historical unique-LINE corridor and coverage readers.

The raw DXF, entity database and local graph remain unchanged. A hashed projection manifest preserves every raw coincident source entity, its coordinates and the explicitly excluded query aliases. Source entity multiplicity remains visible and **physical pipe identity/multiplicity remains unresolved**. This is a provenance view, not deletion, source deduplication or a physical pipe-count decision. The original mapping modes keep rejecting ordinary unexplained duplicate LINEs.

## Mapping and difference guards

Recheck each equipment's actual route and native junction against the freshly reproduced inventory. Plan legacy circles use the inherited source reader and its pinned external cases; axis Ts use the existing native T reader. Require distinct same-floor, same-system anchors. Compare common-anchor order across all equipment pairs, then map adjacent intervals. Repeated edges, cycles, parallel logical edges, reversed order or an unmatched interior branch return to local source comparison. Existing source-covered degree-two subdivisions can remain path detail.

Output contains two service branches per equipment and two sets of adjacent main paths: `4*N-2` scoped records. Each retains both local snapshots, source/projection evidence and stable mapping IDs. The source family, physical port, physical value and human-confirmation unknowns remain explicit. Correspondence changes neither local topology nor attributes. The formal entry remains pending/exit 2 for DN, installed lengths, broader comparison and HIL.

Run the canonical source-family, inherited correspondence and pipeline gate tests plus the historical regression union. Cover unexplained competitors, native Z changes, stale evidence, incomplete paired services, extra interior branches and branch-order disagreement. Then independently replay the complete native inventory and mapping before attribute fusion or publication.
