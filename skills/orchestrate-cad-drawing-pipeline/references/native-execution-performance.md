# Native execution: measure, batch, preserve proofs

For unchanged completed artifacts, the separate application entry
`pipeline.py reuse-native-artifact` supports content-checked reuse across jobs.
See [verified artifact reuse](verified-artifact-reuse.md). The default native
runtime described below still performs its original per-job native controls;
warm artifact reuse must not be reported as a fresh native replay or a cold-build
speedup. New inputs/rules and milestone verification retain full reconstruction.

The default native runtime batches seven hash-matching immutable ancestry owners
in one process. Each owner is completely reconstructed on its first call.
Later calls rehash the complete actual file/probe/directory closure before using
an independent result copy; changed bytes, including same-size/same-timestamp
edits, invalidate it. Nested captures merge their transitive dependencies into
both the batch and the original replay observer. Untracked effects disable reuse.
Four explicitly pinned legacy Python producers use the existing in-process
adapter, retaining their original output comparisons. Unknown commands still run
normally. No pass result or parse is imported from an older job.

Set `CAD_NATIVE_OWNER_REUSE=0` for the original owner-call control, or
`CAD_NATIVE_OWNER_BATCH_VERSION=1` explicitly for that default. Optional version 2
also covers pre-imported aliases and current topology, full-plan DN, cross-view, ordered-path and
member-projection ancestry; it restores both definitions and imported aliases
on exit. It was not faster for the complete repeated SH16 job (about 417 versus
419 seconds), so do not promote its cold-call speedup to a default-runtime gain.
Additional arguments and unmatched implementations retain original execution.
The default cache retains 24 owners; version 2 retains 64, discarded at runtime
exit. Internal dependency validation performs fresh reads without recursively
tracing those same reads; the complete child closure, including uncacheable
effects, is explicitly merged into its parent. Nested captures inherit only
their parent's already observed owned scratch roots; unrelated writes still
disable reuse. Live scratch roots block reuse until cleanup. Native geometry remains in a
single coordinator thread; independent jobs use the shared process
budget below. Preserve the existing projection loader when adding owner hooks.
Report first reconstruction, repeated-owner calls and the entire job separately.
Increasing CPU/RAM utilization is not itself evidence of faster completion.

The default isolated single-thread runtime also enables the inherited C-backed
plain-graph clone. It preserves mutable isolation, container aliases and cycles;
explicit memo/custom objects keep standard deepcopy, and a runtime with other
threads keeps the standard path. `CAD_NATIVE_GRAPH_COPY=0` is its control.
This is separate from the selected-edge projection copy optimization.

The formal `pipeline.py validate-*` entry, `full_batch_plan_attribute_gate.check`
and `build_visualization.build` use `default_native_runtime` automatically.
The default is min(22, CPU count minus two) processes, with a minimum of one.
Set `CAD_NATIVE_WORKERS` to 1..32 to control concurrency. Set
`CAD_NATIVE_PARALLEL=0` for the original serial control. Nested entries share
one runtime; a service starts only when a qualifying native scope needs it.
Small fixtures and unsupported/transformed scopes use the original owner call.

Workers retain native CAD and graph inputs during the job. Source path, source
SHA256, graph path, graph SHA256 and unchanged geometry kernel hashes bind every
batch and reuse. Exact current graph values must match the pinned input. Cache
entries are ephemeral and bounded; changed inputs invalidate reuse. Every
original owner verifier still executes and compares its original receipts.
Do not reuse a historical pass flag or silently omit failed rows.

The projection value backend is restricted to the unchanged `projected_coverage`
kernel. Only its selected edge is copied for mutation; all other graph fields
remain read-only. Canonical JSON prefix/suffix hashing is used only when identity
and shape guards prove equivalence to the original encoder. Unsupported shapes
fall back. Copy/hash functions are restored even on exceptions. Never enable
this copy strategy for arbitrary graph mutation algorithms.

Historical Python namespaces remain in one main thread per geometry owner.
The coordinator owns an isolated subprocess service, not geometry threads.
Independent regression test subprocesses run concurrently via
`feature_impact.run_selected`; the default is min(22, CPU count minus two),
overridable by `CAD_TEST_WORKERS` or `feature_impact.py --workers N`.
Flat same-skill suites are sharded, rather than assigning the whole skill to
one process. Recursive package discovery keeps its original discovery owner.
`workers=1` retains the serial module/discovery control.
Each child receives the tested sibling skill script paths explicitly, so a
shard cannot depend on another test first importing an orchestration dependency.

Long viewer test modules listed in `assets/test-execution-policy.json` can use
separate independent methods. Exact module bytes must match the policy pin;
a disposable subprocess enumerates actual unittest IDs. Module/class fixtures,
custom loaders, imported test classes or changed module bytes retain original
whole-module execution. No tests or assertions are removed. Child tests receive
one native/test worker and one BLAS thread, so nested pools do not multiply.
No tests, native source checks or semantic acceptance gates are skipped.

For independent drawing/stage owners, use `scripts/run_native_task_batch.py
--manifest MANIFEST --output NEW --cores 22 --monitor`. The operator-authored
UTF-8 JSON has `schema_version:1` and `jobs`; each job supplies `id`, argument-array
`command`, absolute `cwd`, `cores`, optional `depends_on`, pinned `inputs` mapping
absolute files to SHA256, and disjoint absolute `outputs`. Default success exit
codes are `[0]`; explicitly declare others only when the owner documents them.
Three independent floor owners can each reserve seven cores under a 22-core
budget. Do not run three independent 22-process pools. Dependent stages wait;
failed descendants are blocked while unrelated drawings finish. Every job gets
its own log, exit code and elapsed time; the batch retains all outcomes, checks
input hashes before/after and binds its manifest/implementation. `--monitor`
records the process tree's CPU and RSS in a sibling resources JSON. This schedule
does not introduce source-result caches or new CAD connectivity.

Keep original drawing owners and receipts immutable. Do not schedule overlapping
output trees. Never run mapping before required local-topology/source checks just
to occupy cores. Idle resource headroom alone does not imply a fivefold elapsed
speedup. Measure wall time, sustained/peak CPU and exact results separately;
additional RAM is useful only when it avoids proven repeated work.

For a standalone complete family use
`native_projection_batch.py --manifest MANIFEST --output NEW --workers 22`, then
`pipeline.py validate-native-projection-batch --projection-run NEW`.
`run_native_accelerated_v1.py --help` exposes the job wrapper and optional resource
monitor; psutil is required only for monitoring. Normal execution uses the
existing CAD environment and standard-library process management.

Measure identical inputs and compare every native proof hash, not counts alone.
The SH16 baseline covers all172 restored native block branches. Separately record
first-call and resident-worker timings, peak CPU and summed worker RSS. Peak is
not average; summed RSS can include shared pages. Microbenchmark speedups are
not whole-pipeline speedups. Do not mutate frozen live producers or restart
successful stages merely because a command exceeded an interactive timeout.

## Repeated strict native source reads within one job

`default_native_runtime` also retains bounded, job-local parse snapshots for the
unchanged `source_readability.read_source` owner. The original parser creates each
snapshot in this process. Every subsequent call receives an independent Drawing
clone, rechecks current source bytes and still executes the strict Chinese scan.
Consumer edits cannot contaminate later reads. Changed source bytes invalidate
that path's snapshot and reparse; the original source-owner receipt checks still
decide whether changed input is admissible. No historical pass or serialized file
is loaded. Unknown readers/arguments and unpicklable documents use the original
parser. The in-memory payload budget is 512 MiB; this is not total process RSS.
Set `CAD_NATIVE_SOURCE_SNAPSHOTS=0` for a same-session parser control, or
`CAD_NATIVE_PARALLEL=0` for the original complete runtime control. First parsing
and snapshot construction cost time; qualify repeated source jobs with measured
wall time and complete native output bytes before claiming a speedup.

## Bounded DXF allocation and exact serialization reuse

Inside the isolated native reader, a short allocation window pauses cyclic GC
only while the original DXF parser or an internal snapshot pickle runs. Reference
counting remains active. The caller's GC enablement and thresholds are preserved,
including on exceptions; normal cyclic collection resumes immediately afterward.
Projection workers use the same window for their unchanged strict source reader.
Every read still executes the original Chinese checks and input hash checks.
Set `CAD_NATIVE_ALLOCATION_GC=0` for the original allocation control. Include final
collection and process-tree RSS when measuring complete owner performance.

The pinned projection backend also reuses canonical JSON serialization, never a
geometry proof or verifier pass. Fresh internal protocol-5 tokens inspect every
graph value and dictionary order on every call. Exact unchanged subtrees can be
reused even while another edge is rebuilt. Builtin JSON types alone qualify;
unknown values retain the original serializer. Envelope bytes are bounded to
64 MiB and subtree bytes to 32 MiB per process. Runtime close clears the main
process cache; owned worker exit clears worker caches. No token is unpickled and
no serialized snapshot or pass flag is loaded from disk.
Set `CAD_NATIVE_SERIALIZATION_REUSE=0` for the original serializer control.

Exact subtree encoding also covers `batch_native_path_coverage`'s read-only
per-path graph projection entry. The unchanged original encoder remains the
fallback for empty/unsupported graph shapes; every current value and key order
is retokenized before reuse. This changes serialization work only, retaining
every native path reader and output byte. `CAD_NATIVE_PATH_SERIALIZATION=0`
disables this entry alone. Qualify complete owners as well as microbenchmarks.

The SH16 172-edge changing-graph serialization benchmark measured 21.58 to
3.82 seconds (5.65x) with every projected graph hash identical. This isolates
serialization, not complete reconstruction. The DXF clone probe measured about
2.7 to 0.4 seconds before cleanup, and about 3.7 to 1.9 seconds including cleanup.
The full original 08 owner with only the allocation change measured 96.42 to
89.75 seconds. Do not promote those local gains into a fivefold pipeline claim.
Schedule independent floor owners under a shared budget and report actual full
batch timing separately. Never enlarge a pool beyond the shared budget merely
to increase CPU or retain unused memory merely to increase RAM utilization.
