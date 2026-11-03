# Post-drawing quality gate

Run after generating the actual viewer, before presenting it as a checked release. This is a technical self-check and repair loop; it never creates human HIL annotations or Finish Review attestations.

## Check and repair

1. Check every edge has valid endpoint nodes or explicitly pending virtual boundaries; equipment ports have logical edges or localized unresolved evidence. Check source pipe coverage, system separation and crossover non-connectivity. Counts alone do not establish completeness.
2. Check every recognized assembly retains every member's complete source handles, including exploded strokes, circle heads, diameter bars and actual connectors. Source connectors may cross drafting layers; require both native endpoint contacts and the qualified family geometry rather than proximity. Keep measurement context separate from water connectivity.
3. Compare exported per-instance equipment/component paths and fills against source geometry at the same original-coordinate transform. Source equipment size, rotation and mirrors must survive. Keep selectable node halos separate from equipment body geometry. List icons may stay normalized. Do not use a nearby rectangle as proof of a complete equipment family.
4. Inspect matching CAD/topology extents and scale: overview, each equipment/symbol family, repeated measurement assemblies, discontinuities/virtual terminals and every repaired region. Inspect all repeated instances affected by a rule change. Save actual visual evidence and observations; a script that merely generates images is not a visual inspection.
5. Fix deterministic defects in shared conversion/viewer rules, add positive/negative regression coverage, regenerate in a new directory and repeat the affected checks. Do not patch only the delivered graph/SVG, update snapshots to hide an unexplained difference, or declare a missing source line connected without evidence. When evidence is insufficient, retain a localized pending entry with reason and source coordinates. Distinguish source ambiguity from a known implementation defect.

## Executable gate and states

`build_visualization.py` invokes `scripts/post_drawing_gate.py` on the generated viewer. It compares native paths/fills with DXF and consumes the converter's `sourceFidelity` ledger when provided. Known geometry/member/identity/endpoint failures block the bundle build. Legacy adapters without instance display handles are explicitly unverified, not silently accepted as CAD-identical.

After inspecting actual renders, run:

```powershell
python <skill>/scripts/post_drawing_gate.py --viewer <viewer> --dxf <source.dxf> --visual-evidence <quality/visual-evidence.json>
```

Evidence JSON contains `graph_sha256`, `renderer_sha256` (public/app.js), `performed_by` (e.g. Codex technical check, never impersonate an expert), `known_unfixed_defects` (list), and `regions` (list of `id`, relative `artifact`, `sha256`, `result: checked`, `observation`). Bind evidence to the exact rendered graph and renderer; regenerate evidence after changed geometry. A PNG/SVG must exist and match its hash. Report actual scope and limitations; artifacts and schema alone do not prove a complete inspection.

- `FAIL`: known deterministic defect or stale/missing supplied evidence; repair and rerun. Do not mark release ready.
- `AWAITING_VISUAL_CHECK`: machine checks passed but visual inspection is not recorded; candidate only.
- `PASS_WITH_PENDING`: checks completed for the stated scope, explicit source/semantic uncertainties remain; deliver as ready for human review with the pending list.
- `PASS`: checks completed without recorded pending items in that scope; still not an expert correctness confirmation or proof of recognition of all unknown CAD symbols.

Ship `quality-gate.json`, evidence images/observations and relevant regression results. Refresh the ZIP after the final gate so its files match the inspected directory. Preserve old releases and human review storage. Ordinary source uncertainties do not require a new complex approval process.
