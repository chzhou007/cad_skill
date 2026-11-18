# Anchor identity and the limit of linear-corridor corroboration

Use `audit_corridor_anchor_dependence.py` when explaining how many independent
anchors constrain a source-checked corridor, or when testing sensitivity to
equipment labels. It is a read-only audit of the explicit current native
corridor mode, not another correspondence acceptance gate.

Equipment captions supply identity candidates. A usable anchor also needs
source-checked device ownership, separate supply/return service paths to true
Ts, the same floor/system and unique native pipe coverage in both views. Never
replace that chain with text proximity, an equal edge count, drawing direction
or labels copied from the already fused graph.

The corridor mapper's minimum of three equipment anchors is an implementation
precondition, not a confidence threshold. All-pair order comparisons share the
same anchors and are correlated. A complete reversal of every device label on
a straight chain can preserve all order comparisons. Pairwise label swaps can
therefore all be rejected while that coherent counterexample remains possible.
Exact native identity/ownership evidence, or separately proved asymmetric
network context, must resolve it. Do not invent left/right or screen-direction
rules: plan and axis projections may legitimately reverse their geometry.

```
python audit_corridor_anchor_dependence.py --mapping-run CURRENT_CORRIDOR_RUN --output NEW_AUDIT.json
```

The audit pins mapping/receipt, source/local graphs, inventory, policy and native
implementation hashes. It rereads both CAD files through the Chinese-readable
source reader and reproduces each corridor's geometry, native path coverage
and complete mapping records. It does not rerun the inventory's full ancestor
chain: the independent formal inventory/mapping replay remains prerequisite
evidence with its own scope.

Report equipment counts, service-anchor counts, mapped-path counts and corridor
group counts separately. Include native main LINE handles, every device's two
view T/branch paths, all pair-swap outcomes and coherent reversal outcomes.
Retiring one anchor checks the remaining routes; this audit does **not** predict
the withheld device's owner or T. A full-network hidden-anchor prediction is a
different test and cannot be claimed from these reduced-corridor results.

SH16 09's current four groups contain 8/8/8/6 devices: 30 devices, 60 service
anchors and 112 path scopes. The real audit rejects 99 pair-label swaps but
does not reject the eight full-reversal service scenarios by order alone.
These are deterministic counterexamples, not a measured error probability or
evidence of an actual mismatch. Preserve the original source labels and
ownership proofs; do not reopen answered HIL items merely because an audit
exposes this general limitation.

Run `test_audit_corridor_anchor_dependence.py` and the unchanged source-order
and current-corridor tests. Native geometry replay, complete ancestry, full-floor
connectivity, DN/length fusion, publication and HIL remain separate states.
