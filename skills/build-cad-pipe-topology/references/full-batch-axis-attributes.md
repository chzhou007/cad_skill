# Complete plan attributes on the current axis graph

Use `compose_full_batch_plan_attributes.py --policy POLICY --output NEW_FOLDER`
after complete local DN and native correspondence batches. Verify through
`--verify-output FOLDER` and `pipeline.py validate-full-batch-plan-fusion
--fusion-run FOLDER`. The producer independently replays the complete current
mapping, complete local DN owners and prior complete axis parent.

Check the historical parent's entire implementation surface before replaying
current mappings. If only its pinned runtime library is historical, use
`historical_parent_native_replay.materialize_runtime_overlay` to copy the current
asset tree with the bundled original library at its actual import path. Every
geometry-owner hash must still match the original receipt. Pin the resulting
overlay manifest as `historical_parent_overlay` in the fusion inputs. The
original parent then runs freshly in an isolated, single-threaded historical
module namespace; current modules are restored on success or failure. The new
audit records this separate bridge. Do not rewrite old receipts, accept a hash
mismatch by whitelist, preload old pass flags, or run current geometry under a
faked historical module path. Pin both current and overlay legacy child CLI
entries when using bounded same-batch scratch reuse.

For independent replay of historical full-plan DN receipts, use
`verify_inherited_plan_DN_semantics.py --verify-output FOLDER` or the pipeline
`validate-inherited-full-plan-DN` entry. Keep the original producer and its
implementation hashes intact. Recheck the saved byte hash and every native
input, then compare complete canonical JSON values: dictionary key order and
Python tuple/list storage are serialization details, while array ordering,
number representation, missing fields and evidence values remain strict.
Never repair this failure by trusting stored pass flags or dropping lineage.

## Inheritance and scope

- Reuse ordered F, calibrated scalar, through-T/branch rules and bounded expert
  answers through `rebuild_inherited_full_plan_DN.py`; never filter plan DN
  extraction to an already matched subset.
- Reuse strict native projection metrics first. Recover qualified inline paths
  through `native_inline_joint_path_coverage.collect/inline_projection` and
  source-normalized crossings through `path_evidence/lengths`. Preserve known
  prior measurements. Joint interiors, omitted spans and unshown connectors
  remain unknown; a detail expression cannot become measurable from global
  drawing units. Unresolved metrics do not stop unrelated paths or floors.
- Replay caption/body identity and migrate physical component references. The
  whole parent must be exactly restorable after stripping new batch scopes and
  inverting the proved permutation. Identity-affected existing attributes need
  explicit semantic invalidation; this entry refuses to relabel those values.
  Preserve all other old attribute payloads, source roots and boundary context.
- `batch_plan_attribute_scopes` contains the current mapping, floor/service,
  source-checked plan DN records and partial XY. It does not replace a distinct
  axis equipment drop or cross-floor riser value.
- A one-to-one main gains whole horizontal DN/centerline only when both plan
  endpoints reach real Ts and the existing native horizontal-axis domain reader
  passes. A multi-edge group retains a shared path scope; no child receives the
  group's route total or an invented allocation. Complete centerline route,
  net cut length and installed whole-edge length remain distinct quantities.
- A current conflict stays unknown even if an old result selected one value.
  Retain old fields for history and show current source status first. Do not use
  historical snapshot agreement to hide new evidence or fabricate improvement.

## Formal source and viewer

The source gate dispatches `sourceFullPlanBatchAttributes` before retained roots,
replays its producer, restores the complete parent and retains every prior
comparison error/pending item. It never promotes human acceptance.

The viewer uses `full_batch_plan_attribute_viewer.py` before old prefix ancestry.
Reuse only the parent audit produced by this actual replay, binding all ancestor
paths at their real parent folders. The bundle schema checks root/edge equality,
source hashes, metric pieces, original axis extents and review state.
`full-batch-plan-attributes.js` presents current drawn-plan DN, source labels,
local pipe XY, group totals and complete horizontal centerlines separately.
CSV keeps unknown numbers blank and shared totals in their own group column.
Existing values, physical geometry and expert annotation history remain present;
related HIL confirmations do not carry across semantic changes automatically.

Run the registered composition, inherited metric, source-gate, viewer schema and
JavaScript property/export tests plus affected historical suites. Native complete
composition, actual browser/CSV/Chinese checks and publication are separate
steps. A source-ready candidate is not a published or human-accepted drawing.

## Effective publication regression

Before publication, apply the effective UI/CSV and component-name conservation
checks in [batch application and scoped review](batch-application-and-scoped-review.md).
Independent source comparison success alone does not clear this release guard.
