# Valve display stems in DN pipe competition

Use this rule when a scalar DN observation is blocked by a short pipe-coloured
LINE inside a referenced equipment block. A short line, a layer name or the
fact that the graph omitted it does not make it annotation geometry.

`native_valve_display_stub_evidence.collect` first replays the existing v17
overshoot and turn-display-valve normalization on the original document with
the same explicit source system layers. Its private legacy namespace must not
change another pipeline stage's layer detector. Then require all of:

- One exact native root/valve/free-line/attached-line source chain, supported by
  the inherited turn-display valve names and the original transformed geometry.
- The attached sibling was actually removed by the inherited rule: its removal
  changes three rays to a non-collinear bend, and its valve-side endpoint is
  dangling. Do not replace this replay with a block-name or proximity test.
- The proposed free line lies on the opposite side of that same valve, on the
  same stem axis, within the inherited short-leg bound and at coincident Z.
- Its outer endpoint reaches no other native same-system pipe. Its span is not
  retained as an active graph pipe. The attached sibling's real two-ray bend
  remains uniquely in the current source-backed block path.

The output qualifies that **one source primitive** only as the opposite stem of
an already normalized display valve. It removes no CAD entity, local graph
edge, component or device, and assigns no DN or physical length.

`native_segment_dn_candidates_v2.py` replays this evidence before inheriting the
original segment-DN reader. A private reader dependency namespace excludes only
the exact qualified primitive from its nested **pipe competitor** stream. The
original source document remains intact for text/F recognition. Every other
modelspace or nested pipe, including another primitive in the same block, must
still compete. Verify that the exact source chain was encountered once with
the same layer/XYZ. Do not exempt the whole block or globally change
`recursive_decompose`. With no exclusion policy, behaviour is the original
reader's behaviour.

The CLI independently reproduces the native line evidence and pins all input
and implementation hashes. `pipeline.py validate-axis-segment-DN --diameter-run
...` calls the native verifier; successful scoped replay returns status pending
(exit 2), not whole-riser or human acceptance. Preserve the previous withheld
item as history when its source owner becomes readable. Earlier DN values and
projections stay fixed; competitor lists may change only for the proved stem.

Tests cover native rotation/mirroring, a real pipe at the free end, an active
graph span, missing/wrong sibling proof, unsupported valves, Z/length changes,
surviving-bend source evidence, another nested competitor, old source/text/F
guards and unchanged global readers. Run these with inherited segment-DN,
v17 normalization, component, riser and pipeline regressions, then re-read the
current native source through the formal entry.

This rule resolves label competition. A direct segment DN still does not prove
its whole-edge extent, a transition position, cross-view correspondence or
installed length. Mixed horizontal/vertical edges require separate source
domains; horizontal physical values continue to come from matched floor plans.
