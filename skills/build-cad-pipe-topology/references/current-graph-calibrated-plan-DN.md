# Calibrated plan DN after path reconstruction

Use `junction_rebased_plan_DN_scopes.py` after current native corridor mapping.
It reuses the established native text catalog, through-T/branch-override
inheritance, qualified component-DN and source path readers. Every original
branch/main scope must match exactly one current mapped group. Do not fuse DN
into the axis graph or derive installed lengths at this stage.

Keep calibration controls separate from target bindings. A control formerly on
a short edge may now lie on a longer merged path. Replacing its old edge ID
with the whole merged ID expands annotation competition. Do not suppress the
resulting unparsed/ambiguous DN guard or drop troublesome controls.

`current_graph_calibrated_dn.py` replays original control fragments directly
against the native source and binds targets in the current graph. Each retired
control requires an exact archived fragment and current source-owner alias;
unchanged controls retain their source geometry. Changed target geometry needs
a dedicated segment binding and is rejected by this mode. Original and current
graph hashes, control roles and source handles remain explicit. Control evidence
does not assign DN to the whole merged edge.

The inherited collector runs in an explicit private dependency namespace: only
its control-source reader uses original fragment scopes. Its target annotation,
text profile, independent-control and ambiguity guards remain unchanged.
Historical collector globals, graphs, policies and accepted receipts are not
modified. Targets never become controls. Recompute the complete current source
catalog and all selected through-T domains before reporting current DN values.

```
python junction_rebased_plan_DN_scopes.py --mapping-run MAPPING --origin-scope OLD_SCOPE --origin-calibration OLD_CALIBRATION --origin-graph OLD_GRAPH --policy POLICY --output OUTPUT
python pipeline.py validate-plan-DN --diameter-run OUTPUT
```

The policy pins the mapping/receipt and all three original configuration inputs.
The original graph must be the exact ancestor named by the current mapping.
Qualified component DN is read again on the current graph, preserving its
native template fingerprint, leaders and component owners; it is excluded from
pipe-DN inheritance only after that proof succeeds. Unknown/conflicting pipe
values remain unknown, and parenthetical source numbers are not lengths.

For SH16 09, retain all20 independent original controls and the two explicitly
calibrated targets. A naive whole-edge control rebase is a retained negative
case; native fragment replay preserves the original scope and target guards.
That binding proof alone does not accept current T inheritance or axis extents.
Run the control-fragment, current-DN topology and actual pipeline gate tests,
then independently replay the real DN output. XY metrics, view comparison,
complete-parent fusion, publication and HIL remain separate dependencies.
