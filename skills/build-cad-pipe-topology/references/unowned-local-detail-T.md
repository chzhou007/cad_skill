# Read local detail connectivity before requiring equipment ownership

Use `rebuild_local_detail_full_plan_DN.py --manifest INPUT --output NEW_DIRECTORY`
and `pipeline.py validate-local-detail-full-plan-DN --batch-run DIRECTORY`.
This entry includes all previous annotation, source lineage, confirmed circles,
overlap, wave and turning-main DN continuity rules.

An existing three-edge native detail T is readable even if its terminal has
not yet been attached to a real equipment instance. Requiring an equipment
owner before reading the local pipe incidence confuses two separate tasks,
creates false provider gaps and loses applicable DN inheritance.

The new adapter reuses `canonicalize_confirmed_sideviews.verify_tee` on the
current graph, source LINEs and its existing circle-radius exclusion evidence.
Require exactly three same-service incident edges, one unique circle-rim
branch and one terminal (node or non-node boundary). Revalidate unique circle,
native LINE identity and graph-to-source segments. Preserve all original
coordinates, native XYZ and incidence. Never use a projected circle radius
or native Z as measured physical pipe length.

The proof certifies only this local T. It does not establish equipment owner,
main/detail equivalence, source scale, physical port or connector length.
Existing reviewed-sideview equipment ownership still requires its complete
original alias, Pair and reply contract. Ordinary crossings, fourways, mixed
systems, duplicated native lines/circles and stale rim evidence remain barred.

`test_native_local_detail_T_evidence.py` covers rotation/mirror, node/boundary,
branch-only no-backflow, nonzero native Z, source ambiguity, complete entry
composition and exact prior plain-source behavior. The gate test guards the
semantic boundary. Replay all applicable SH16 local plans and all registered
historical tests before installing; axis fusion, LF20 and HIL are separate.
