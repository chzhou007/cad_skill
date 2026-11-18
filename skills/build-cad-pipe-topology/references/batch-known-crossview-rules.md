# Batch application of inherited CAD rules

Use this entry after repeated source cases establish a rule. Run the complete
drawing/floor batch before requesting more individual judgments. A semantic
exception belongs in the grouped review queue; it must not stop unrelated
equipment, mains or floors.

`apply_crossview_rule_batch.py --manifest MANIFEST --output NEW_DIRECTORY`
consumes fixed native inventory, source identity, prior attribute and reviewed
DN receipts plus each floor's metric policy. `--verify-output DIRECTORY`
independently replays native inputs. Preserve all original feature assets;
edited receipt/pass flags are not source evidence.

Create a native identity receipt with `build_native_caption_identity.py
--source SOURCE --graph GRAPH --devices CANONICAL_COMPONENTS --policy POLICY
--output NEW_DIRECTORY`. The policy pins all three inputs, the typed equipment
layer and both display font profiles. This producer performs the reference and
component migration; no hand-edited intermediate graph is required.

1. Read Chinese strictly. Apply inherited local geometry, wave/circle,
   equipment/port and component rules through the family rebuild.
2. Batch equipment identities. Exploded bodies use complete connected native
   outlines and two pinned independent fonts with bounded width uncertainty.
   Reuse `resolve_rotated_equipment_labels.measure_caption/footprint_candidates`.
   Text insertion-point distance can reverse adjacent labels. A complete closed
   identity permutation on connected equipment requires explicit node, port and
   component reference migration. Preserve pipe IDs, coordinates, paths,
   services, native component handles and old name history. Ambiguous footprints
   remain unresolved.
3. Reuse fresh plan and axis service inventories. A proved identity permutation
   can move body/service evidence to its correct current caption only after
   exact path/service preservation and fresh graph-route checks. Historical
   proof hashes remain historical; never rewrite them as current ones.
4. Reuse full-floor anchored network matching. Where views differ in detail,
   apply only unique same-service junction relations supported by at least two
   already matched neighbours, then direct-main matching. Keep unmatched,
   parallel and competing paths. Do not connect wave ends to nearest mains or
   infer a remote main/detail alias from order alone.
5. Batch native path and metric checks. Existing guards exclude unmeasured
   detail expressions, unsupported split paths, unshown equipment connectors
   and inline interiors. Record metric exceptions instead of zero values or
   cancelling the batch.
6. Apply reviewed DN boundaries through the inherited kernel. Preserve original
   labels and unaffected scopes. Plan horizontal DN150 and equipment drop DN80
   domains remain separate.

Every current axis edge must appear exactly once in the outcome partition.
Distinguish matched path candidates, prior partial scopes needing replay,
vertical/mixed scopes, mapping conflicts and missing local/main-detail paths.
Report whole-edge DN+length separately from partial XY. A matched path is not
attribute fusion, publication or human acceptance.

Expand proved main/detail and omitted-route conditions into shared code. A
missing formal entry is implementation work, not another expert question.
Actual ambiguous/conflicting source relations enter the review page with a
large native locator and local Pair.

Tests: `test_native_exploded_caption_identity.py`,
`test_batch_apply_crossview_rules.py`, `test_batch_rule_contract.py`,
`test_apply_crossview_rule_batch.py`, and inherited caption, anchored-network,
native projection and DN boundary tests.
