---
name: orchestrate-cad-drawing-pipeline
description: Route multi-drawing CAD conversion through equipment/material recognition, family-specific pipe topology, architectural context and HIL visualization. Use for new CAD batches, mixed drawing families, pipeline configuration or cross-skill regression and delivery. Each drawing remains an independent task; specialized skills own their outputs.
---

# CAD drawing pipeline

Version: **1.1.1**. This is the workflow entry point. Use a fixed dependency backbone with multi-label branches, not a single universal CAD recognition pass. Read [contracts](references/contracts.md) and the relevant source-family profile before processing. `scripts/pipeline.py` creates and validates task plans; it does not claim to be a universal CAD recognition engine or automatically execute every branch.

## Mandatory source comparison stage

Every pipe task now requires source_comparison after topology/applicable architecture and before final visualization/HIL. See the pipe owner’s [semantic reconciliation contract](../build-cad-pipe-topology/references/source-semantic-reconciliation.md). A preview renderer may support internal comparisons; it is not final HIL. pipeline.py validates native evidence hashes, graph freshness and family dispositions. Missing rounds or unconsumed algorithm families keep the task pending; invalid evidence fails. Existing plans must be replanned under the new stage schema. No automatic human confirmation.

## Execute

1. Freeze native sources and references, hash inputs and inventory units, layers, nested blocks, attributes, text, curves, xrefs and unsupported objects. Preserve WCS and source instance chains. Shared parsing is read-only and semantically neutral: no gap healing, wall closure or T inference here.
2. Classify drawing, regions and entities with multiple evidence-backed tags. Resolve base library → center profile → drawing-family profile → drawing-local verified evidence. Local overrides require provenance, scope and regression; conflicting types, units or ports stay pending. Unknown families never fall through to an arbitrary extractor.
3. Extract equipment/material candidates and reference parameters before pipe topology; parameters remain references until bound to a source instance. Execute pipe-family and architecture branches separately after their dependencies are ready. Independent drawing tasks may run concurrently using exclusive output directories and immutable shared inputs.
4. Delegate pipe semantics to `build-cad-pipe-topology`, building context to `extract-cad-building-context`, and completed-data rendering/HIL/Pair to `visualize-cad-pipe-topology`. Only pipe normalization may heal verified pipe gaps, remove pipe overshoots or identify T nodes. Architectural openings must remain openings. Viewer never adds graph connections. A child skill returns artifacts to this orchestrator, not recursively to the orchestrator or another copy of itself.

   In orchestrated mode disable a converter's automatic final viewer handoff (for `run_alignment.py`, pass `--without-visualization`). Prepare building context from the completed raw graph with the building skill CLI, then invoke the viewer exactly once with `--building-context`; include `--parameters` for a task/source-bound effective parameter artifact. Standalone conversion retains its existing automatic viewer handoff. Do not generate two viewers or treat a branch's return as a request to restart the pipeline.
5. Validate source identities, units, coordinate transforms, object ownership, component conservation and source coverage. Record every branch as completed, not_applicable, pending or failed, with evidence. Technical checks do not create human errors or Finish Review confirmations. Fix deterministic defects; preserve source ambiguity as pending. Deliver inspection packages with honest unresolved status.
6. Render and inspect representative native CAD/topology regions, including prior failure cases. Export an offline Pair and verify crop, symbols and comments. HIL remains error-only annotation, immediate comment entry and one whole-task Finish Review. No per-object pass clicks. Each task retains independent review. Semantic source/graph/parameter/building changes invalidate confirmation; style changes do not. Keep old annotations as history, never migrate confirmations automatically.
7. Package version locks, inputs, node/edge/component data, branch receipts, audit and regression report, viewer and local launch instructions. Cross-sheet hydraulic integration is a separate authorized derived product, never a silent task merge. Large physical equipment retains resistance and supply/return evidence; only proven meter measurement branches may be omitted from a calculation projection. Do not infer missing physical ports from proximity or another sheet.

## Runnable coordination

`python scripts/pipeline.py plan --config batch.json --output NEW_DIRECTORY` freezes configuration and referenced profile files and writes one independent task plan per drawing. Existing directories are refused.

After executing each applicable specialized stage, fill its receipt (see contracts). Run `python scripts/pipeline.py validate --run RUN_DIRECTORY`; exit 0 means required artifact contracts passed, 2 means pending, 1 means failed. This is technical preflight, never human review. Planning starts pending; do not mark extraction completed merely because routing succeeded.

Run `python scripts/verify_dependencies.py` before generation. Building extraction has one canonical implementation in its owning skill. The viewer's portable vendor copy is generated from it, recorded by SHA256 and verified; run `--sync` only when deliberately updating that dependency. Then execute regression in both owners. Do not edit the vendor copy independently.

## Change impact

Profile-only changes: all affected drawings of that family, plus a negative family. Shared geometry/parser changes: all graph families and architecture exclusion cases. Rendering/Pair/HIL changes: all affected output types plus persistence and semantic-identity tests. Compare connectivity, ports, source/component identity and local native geometry, not only counts. Keep failures and untested drawings in the batch report. See [SH16 routing](references/sh16-routing.md), an example rather than universal defaults.

Historical source coverage v1.0.1 introduced conversion v1.12.0. Current dependency lock uses conversion instructions v1.12.2, visualization instructions v2.8.4 HIL and building instructions v1.1.2 (building engine v1.1.1). Require full-layer input inventory separately from known graph/component conservation. Every physical normalization change requires equipment-port, T and adjacent-edge reconstruction before handoff.

Source-group gap gate v1.0.2: conversion v1.12.1 discovers physical gap evidence before service filters. Source group is distinct from hydraulic service. A crossing-proven same-layer gap blocked only by unverified group is a blocking profile/input issue, not a generic pending external endpoint. Require full final span coverage, then recompute T and edges.

All-task refresh v1.0.3: after a shared normalization update, rerun every applicable pipe-family task and record not_applicable reference/support branches separately. Exact source geometry/connectivity equivalence may retain established IDs and enrichments; archive the fresh reconstruction and its canonical ID mapping. Validate node-system filter coverage, including isolated pending equipment, before declaring every task updated. Launch local servers sequentially to avoid concurrent port-scan/bind races; processing tasks may still run independently.

## Log consolidation (2026-10-27)

Read [log-driven routing and whole-batch refresh](references/log-driven-refresh.md) for expert feedback, cross-skill ownership and any request to update all tasks. Instruction/handoff revision only; the validated geometry/rendering algorithms from the previous release are retained.

Portable review v1.0.5: copy the viewer-owned guarded start.cmd/launch_review.py into batch distributions. Default to a selected drawing; make launching all services explicit. Include dependency/file diagnostics and preserve error output. Do not infer memory exhaustion from a closing console; distinguish remote runtime failure from browser rendering. Startup-only updates preserve data and annotations and may be delivered as an overlay patch.

