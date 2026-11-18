# Trace unknown DN to shared upstream evidence before HIL

Run `plan_DN_readiness_trace.py --manifest MANIFEST --DN-run QUALIFIED_LOCAL_RUN
--output NEW` after complete local DN reading. The entry checks the exact local
receipt/result and native graph/source/component hashes, then records one
readiness outcome for every edge. It does not rerun the source stage or assign
DN, length, new connections, physical pipe identity or correspondence.

Group unresolved edges only by same-service incidence at current source-checked
Ts. These are diagnostic groups, not proven DN-transfer paths. Never traverse
equipment to combine supply and return. Preserve typed non-node source
boundaries without creating nodes for them.

Report actual annotation barriers, missing native T evidence, unverified pipe
paths, distinct known through-DN at an unassigned branch, and reviewed scope
boundaries. The nearest known value is not an answer. A value confirmed for an
adjacent source scope does not automatically cover a branch. Keep the complete
group and its frontier source lineage, instead of asking one question per edge.

Route deterministic native T/path failures back to extraction. Reuse existing
common semantic questions for annotation families; do not turn every trace group
into a new HIL question. New actual semantic decisions still require a large
native CAD locator and local Pair. Do not expand prior expert answers beyond
their original scope.

Run `--verify-output RUN` or `pipeline.py validate-plan-DN-readiness-trace
--trace-run RUN` to reproduce the trace from its exact pinned inputs. This is
artifact trace replay, not source-owner reconstruction or topology acceptance.
Changes in local topology, source evidence or DN results invalidate the trace.

SH16 current batch: 629 edges, 59 unresolved in 18 incidence groups; 55 have an
annotation frontier, two have missing source-T evidence, and two are unassigned
branches at a DN450/DN200 transition. Three-floor scope and per-edge causes are
reported separately; 47 third-floor unknowns share compound-label frontiers.
