# Source fidelity and post-drawing repair

After conversion and viewer generation, use the sibling viewer's [post-drawing gate](../../visualize-cad-pipe-topology/references/post-drawing-quality-gate.md). Finish the technical check/repair loop before reporting CAD consistency. Count equality is necessary only where applicable and is never sufficient.

The schematic converter emits `assembly_source_fidelity.json`, `equipment_display_coverage.json`, `sourceFidelity` on the graph and per-equipment `display_source_handles`. Hydraulic `source_handles`/ports remain separate from display-only attached geometry. `source_fidelity.py` verifies complete assembly members and source connectors and identifies the tested attached pump display family. Ordinary unknown families stay pending; a rectangle alone, a table row or one stroke is insufficient.

When source profile/geometry rules change, test the complete symbol and negative controls, all repeated instances of that family and the original SH16 baseline. Run `test_source_fidelity.py`, existing geometry/instrument tests, `run_schematic_regression.py` and `run_alignment.py`. Inspect the actual repaired render as well as numeric results. Add discovered failures to regression before updating expected snapshots, and justify every changed output by source evidence. Never modify immutable source drawings to pass.

For each drawing task retain separate evidence, gate status and pending list. Fix reusable rules rather than a single generated figure. Future conversions use those shared changes; existing unrelated tasks are not claimed rebuilt without running them. Source ambiguity may remain visible under `PASS_WITH_PENDING`, but a proven omitted primitive or incorrect native transform is an implementation defect to repair. Neither technical checks nor automatic hints perform human review.
# Additional source discovery check

Inventory all layers and independently reconcile tagged source heads before claiming instrument completeness. Include exploded rectangle/leader sensors and complete native connector prototypes. Known graph instances alone are not a discovery denominator. Keep reference legend heads separate; retain unmatched heads as pending and reject any represented head lost from exported instance handles. See exploded-component-coverage.md and the v5 native regression fixture.

