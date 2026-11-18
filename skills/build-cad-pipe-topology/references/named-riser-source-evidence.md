# Named riser source evidence

Before matching shafts, look for explicit native labels such as `CHWS1 DN450`
and `CHWR2 DN450`. Preserve the identifier, system and DN observation separately.
A shaft name, matching colour, equal text, nearby position or equal DN is not a
connection or cross-view correspondence by itself.

Use `scripts/native_named_riser_evidence.py --source ... --graph ... --policy ...
--output ...`. The shared `collect` function is read-only and can be replayed by
the consuming stage. The CLI first checks Chinese/native text readability,
re-reads the original DXF, and pins source, graph, policy and implementation
hashes. It never edits nodes, edges, ports, components or physical values.

The formal pipeline validator is `pipeline.py validate-named-risers --source ...
--graph ... --policy ... --evidence ...`. It re-reads the original DXF, checks
all implementation/input hashes and exactly recomputes the entire evidence.
A valid result reports `source_replay=passed` with `status=pending` (exit 2):
normalization interpretation, cross-view mapping and physical values remain
separate. Changed source, policy, graph, code, observations or extra acceptance
claims fail. The validator does not mutate either local graph.

## Policy and source guards

Select literal native TEXT handles and their exact expected text. Declare text
and annotation-line layers independently; SH16 uses both `空调平面`, `TH_TEXT`
and `空调编号` for the text, while the leader LINEs are on `空调平面`.
Do not discard a label because its text and leader layers differ.

For each label, require:

- A supported native TEXT transform. Rotation is supported; mirrored flags,
  non-default OCS, oblique or justified insertion-point semantics stay pending.
- Exactly one parallel native underline at the checked text-normal offset.
  A left-aligned insertion directly above the underline endpoint is valid.
  An insertion beyond the endpoint tolerance is not.
- Exactly one native leader joined to an underline endpoint in XYZ. A shared
  leader star, duplicate underline or unexplained annotation branch fails.
- An independently checked native target, not the closest graph object.

`plan_riser_circle` requires the leader tip to meet the selected native circle
centre in XYZ, the current graph's retained `out_of_plane_riser` node to refer
to that circle, matching system/position, and one current incident service edge.
The circle radius is graphic evidence; it does not supply physical length.

`axis_source_line` requires one native same-system pipe LINE at the tip.
`axis_source_corner` additionally supports two native endpoint rays only when
both are consecutive source-covered segments of one existing graph edge. It
does not turn an ordinary crossing into a connection or create a T.

`axis_source_junction` records three distinct native endpoint rays with an
opposing pair. It **requires local topology recheck** and does not repair the
graph. An interior crossing, another system, coincident rays or four candidate
pipes cannot use this rule.

## Interpretation and dependency boundaries

Report graph coverage at the actual source target. A pipe-coloured three-ray
contact can include an automatic air-vent **display leg**. First replay the
historical normalization with the exact current isometric configuration's
explicit system layers; its legacy colour-first defaults can select building
layers in a mixed DWG. Keep the original `WHAT` semantic anchor, removed/trimmed
leg and surviving non-collinear graph corner as evidence. Do not restore a false
T or a physical pipe from that display leg. A missing graph node alone is not a
defect. If the target remains unexplained after normalization, return its scope
to local source comparison before mapping. Never extend an axis edge or assign
a pipe length to make an identifier match.

Repeated main/detail labels remain distinct records with their own native
leader targets. They are not deduplicated by name. A named riser's DN is a local
annotation observation; no whole-edge diameter, T inheritance, transition
location, shaft ownership, installed length or human acceptance is implied.
Horizontal metrics still come from verified 08–10 paths. Vertical pipe metrics
need independent 11 source/extents evidence, including mixed-path separation.

When a vertical DN is withheld solely because a referenced equipment block's
display stem competes, use [valve display-stem evidence](native-valve-display-stub-DN-competition.md)
to replay the exact inherited normalization before reconsidering attribution.
Retain the old withheld item as history and keep every other competitor. A
resolved direct segment observation does not by itself authorize vertical
extent inheritance, whole mixed-edge DN or installed length.

Run `test_native_named_riser_evidence.py` and the registered native text,
line/ray, riser, direct-DN and cross-floor regressions. Re-extract on current
local graph hashes after topology changes. Keep skipped labels and their
reasons; unsupported source forms are not new CAD defects by themselves.

SH16 source replay identified four plan riser labels on each of 08–10 and eight
11 labels. Four additional 08 detail labels were retained as outside the
current plan-RIF target scope. The four apparent upper pipe/stub discrepancies
were reproduced by the historical automatic air-vent display-leg rule on the
current explicitly configured source layers; the current graph retains their
surviving corners. The 11 main/detail labels still do not authorize automatic
mapping or physical-value fusion. Keep both raw target evidence and the
normalization interpretation, and require separate evidence for correspondence.
