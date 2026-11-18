# Reuse inherited annotation readers in the full-plan batch

Use `rebuild_inherited_full_plan_DN.py --manifest INPUT --output NEW_DIRECTORY`,
then `pipeline.py validate-inherited-full-plan-DN --batch-run DIRECTORY`.
This versioned entry reuses the complete local-parent/DN producer, ordered
native LINE F reader and calibrated scalar reader. Their historical code and
process globals remain unchanged; older receipts retain their original entry.

Each plan may add hash-pinned `inherited_annotation_inputs`:

- `F_origin`: original same-source DN-scope policy with `groups[].line_F_frames`.
  Replay every selected native stem, two bars, text poses and two current pipe
  owners through `native_line_f_diameter_evidence.collect`. Automatic absence
  of an F detection does not establish that the source contains no F frame.
  Consume texts and all proved strokes before scalar attribution/leader guards.
  Rotation, mirror, reversed strokes and negative OCS retain the inherited
  source rules. The F frame assigns attributes, never connects the two pipes.
- `calibration_policy` and `calibration_origin_graph`: pin the actual original
  control graph. Check unchanged targets before any control exception. Screen
  every original control against current source geometry; exclude only controls
  whose original scope no longer binds, recording each reason. All remaining
  controls enter the original collector without filtering by DN or normal side.
  It still requires four independent source LINEs, both services, two directions,
  the same exact text profile and a consistent side. Original control fragments
  are replayed natively; they never become whole current-edge DN values.

The output keeps one record per current plan edge, native F/calibration evidence,
all rejected controls and bounded reviewed values. A missing reader entry is
implementation work, not a new expert question. A newly exposed conflict with
an old value remains a conflict until its source/extent is resolved; old result
agreement alone is not correctness evidence.

SH16 source regression: first-floor BA64/BA65/BA66 with BA62/BA63 is a rotated F;
the second-floor 12E60/12E61 pair uses the inherited same-profile side calibration.
Keep the original question answers and unrelated third-floor DN scopes intact.
Run `test_full_plan_DN_inherited_annotations.py` and the registered inherited
F, scalar, calibration, DN, component, geometry and pipeline suites. Native
whole-plan replay, mapping, attribute fusion and HIL are separate checks.
# Independent current full-plan replay

Use `verify_inherited_plan_DN_semantics.py --verify-output DIRECTORY` or the
formal `pipeline.py validate-inherited-full-plan-DN --batch-run DIRECTORY` entry
for historical inherited-DN receipts. Keep the original producer bytes and its
implementation identity. Check the recorded output byte hash and all original
inputs, freshly recompute every local plan, then compare complete canonical JSON
values. Object key order and tuple/list storage may differ; array ordering,
number representation, missing fields and every source/lineage value stay strict.
This fixes serialization-order failures without accepting edited pass flags or
altering any DN, topology or source evidence.

