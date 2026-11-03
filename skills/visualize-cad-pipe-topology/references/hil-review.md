# HIL review v2

The runtime remains local Python plus a browser. Do not install a database, npm runtime or cloud service. `hil_server.py` adds versioned JSON storage and pair ZIP generation to the existing loopback server.

## Review interaction

Review mode selects nodes and edges only. A node selection does not implicitly select its incident edges; normal network tracing is separate. Shift-click toggles membership. Box select collects displayed nodes and intersecting edges and retains the drawn region, including an empty region for missing objects.

Mark Error opens the annotation dialog immediately. Save commits a group; Cancel creates no record. Notes accept any language and are rendered as escaped text. The UI remains English. Existing equipment/component details remain source context, not separate annotation categories.

Click an issue to locate it in both panes; Edit changes the note. To adjust targets, locate the issue, change the canvas selection or draw a new box, then choose Edit and Use current selection / region. Remove retires the issue; Undo can restore it. Closing requires a conclusion, archives its active error status and invalidates whole-dataset confirmation.

Finish Review applies to all floors and systems, including hidden items. It requires a reviewer and states: “All items other than the marked errors have been reviewed and confirmed.” It is an explicit human attestation, not a claim generated from automatic geometry checks. Five SH16 degree hints are not automatically marked errors.

Adding/removing groups or changing nodes, edges, region or closure invalidates confirmation. Editing notes alone or importing explanations does not. Changed issue content increments issueRevision; explanations for older issue revisions are retained as historical references.

## Identity and persistence

Dataset identity is SHA256 of canonical JSON containing projectId and the graph, devices, ports, main_dxf and legend_dxf source hashes. Display configuration, frontend template and preferred port are excluded; graph/source changes are not.

Files live in `annotations/<datasetId>/review.json` and `history/<revision>.json`, outside the static public tree. JSON writes use temporary files and atomic replacement. Retired issues preserve evidence for undo. Export backup downloads current records, including history references; folder-level copying is the complete local archive.

Do not copy annotations into a new generated release by default. Deliver a pristine, unconfirmed viewer and place illustrative annotations/pairs under explicitly named examples. New graph data must not inherit old global confirmations or map annotations using object ID alone.

## Local API

- GET /api/review returns schemaVersion, datasetId, revision, errors, confirmation, historicalResponses and retiredIssues.
- PUT /api/review accepts baseRevision and document; optional confirm/reviewer creates a global attestation. invalidateConfirmation explicitly clears an imported backup's confirmation. Stale revisions return 409; UI retains pending edits for backup/reload.
- POST /api/expert accepts baseRevision and response (single result or responses array). Results identify responseId, datasetId, issueId, issueRevision, expertName, verdict, reason, expectedConnection and suggestion. Repeated response IDs are ignored. Wrong dataset/issue revision is retained as historical, never applied to the current graph.
- POST /api/pairs accepts baseRevision and selected issue revisions, matching crop bounds, local source metadata and eight client-rendered assets. Server checks record versions and creates the ZIP.

Writes require JSON and same-origin localhost/127.0.0.1 requests; body limit is 64 MiB. Review storage paths are generated internally. SVG pairs reject scripts, event attributes and external references.

## Portable expert pairs

Each issue folder contains CAD/topology original and annotated SVG/PNG, issue.json, context.json, review.html and expert-response-template.json. The client filters source-vector entities by bounding-box intersection before export; changing only the outer viewBox is insufficient. Vector IDs are scoped by source hash; absent native handles stay null rather than being invented. Source text is omitted consistently with the viewer; exports are not native DXF.

Preview uses identical bounds for both panes and permits Fit issue + context or Use current viewport. Up to six issues are rendered per ZIP download to limit request and browser memory; larger selections produce numbered ZIPs. Any single oversized request fails visibly, leaving records intact.

Open review.html offline to view the pair and fill an explanation; download JSON and import it into the originating viewer. Human notes and expert explanations are separate. Import does not change graph data, close an issue or accept the expert judgment automatically.

## Validation

Run scripts/test_hil.py, scripts/test_hil_frontend.mjs and existing scripts/test_builder.py. Browser-test actual group/region selection, cancel/save, Chinese and special characters, filters plus global confirmation, note-only preservation, structural invalidation, save failures/conflicts, reload, PNG/SVG ZIP exports, offline expert form and import. Run a non-SH16 fixture as well as SH16. Never ship QA attestations as the user's completed review.
