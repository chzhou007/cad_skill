# Axis floor labels: source-main reconciliation

A global drawing-Y partition can split one planar main at a tee. Equipment body anchors also need not be physical elevation points. Treat finite datum extent, anchor meaning and topology as distinct evidence.

The scoped SH16 11 T306 case uses the two opposite spans of native LINE 1552A. E0580 is covered by 1552A; E0581 is covered by 15534, 15535 and 1552A. These paths contain no vertical source segment. Their flanking nodes T173 and T172 carry floor label 2. The scoped same-system component agrees with three independently read native equipment captions in plan 09 and axis 11, and plan title 2BD43 explicitly states 二层顶部水管平面图. Eight explicitly source-witnessed long vertical graph spans bound the component search; they do not certify installed risers or length.

`repair_source_floor_labels.py` changes only T306's graph floor label 3 to 2 and the corresponding floor_start/floor_end metadata of E0580, E0581 and E0582. Connectivity, IDs, the third branch's interpretation, component ownership and all length/diameter data are preserved. A matching caption does not establish device ports or formal cross-view path mapping. Physical floor and whole-graph acceptance remain separate.

The floor stage runs after final source-block attachment and before the upstream-joint system stage. Its audit pins both native drawings, graph and policy. The subsequent upstream verifier reproduces its predecessor before replaying component ownership, so removing a conflict record alone cannot establish a valid result. Downstream diagnostics must target the new graph hash.

Snapshot: the full source entry at `E:/codex/CAD/work/feature-regression-registry/sh16-11-floor-upstream-integrated-v1` reproduced graph SHA-256 `ba2cb93b6f16e1457e93cfa3731831261029f7f443c4e716bc166d72cfd296a6`. It retains 424 nodes, 576 edges and 1560 component instances. Candidate cross-floor edges become 8 rather than the earlier 11, because the three scoped edges no longer have different endpoint floor labels. This is not installed-length acceptance. Full mapping, source comparison and human review remain pending.

The equipment datum report preserves all 92 records in two interpretation families: 86 anchors outside the claimed native baseline span (48 unresolved numeric comparisons and 38 numeric-match controls), and 6 in-span unresolved comparisons. Grouping preserves all 54 unresolved records; it changes no equipment floors and does not hand 54 homogeneous issues directly to experts.

Run `test_repair_source_floor_labels.py`, `test_upstream_joint_entry.py`, source comparison, equipment datum and viewer-builder regressions. Inspect the native overview and before/after pair in `E:/codex/CAD/work/feature-regression-registry/sh16-11-t306-floor-source-pair-v2`.
