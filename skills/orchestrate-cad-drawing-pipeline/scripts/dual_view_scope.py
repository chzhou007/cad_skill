"""S0 scope lock for the SH16 dual-view program.

A reproduced unit rule is not a correct drawing. Local topology, isometric
topology and cross-view fusion stay independent. A local connection change
makes mapping, diameter inheritance and attribute fusion stale.
"""

from __future__ import annotations

import json
from pathlib import Path

STATUSES = {
    "reproduced",
    "to_fix",
    "fixed_pending_regression",
    "source_ambiguity",
    "not_applicable",
}
LAYERS = ("plan_topology", "isometric_topology", "cross_view_fusion")
REQUIRED_GROUPS = (
    "source_elements",
    "geometry_connection",
    "equipment_ports",
    "boundary_riser",
    "components_attributes",
    "main_detail_context",
    "completeness_delivery",
    "expert_rules",
    "dual_view",
    "generalization",
)
REQUIRED_FIELDS = (
    "id",
    "group",
    "source",
    "entry",
    "tests",
    "drawings",
    "status",
    "evidence",
    "drawing_correct",
)
MAPPING_KINDS = ("equipment", "port", "riser", "path")
UNTRACKED_TEST = "not-in-tracked-tree"


class ScopeError(ValueError):
    pass


def load_ledger(path, root=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_ledger(data, root)
    if errors:
        raise ScopeError("; ".join(errors))
    return data


def validate_ledger(data, root=None):
    errors = []
    if not isinstance(data, dict):
        return ["ledger must be an object"]
    if data.get("historical_baseline_is_correct") is not False:
        errors.append("historical baseline must stay explicitly incorrect as a correctness claim")
    commit = (data.get("code_baseline") or {}).get("commit")
    if not commit:
        errors.append("code baseline commit is required")
    if list(data.get("layers") or []) != list(LAYERS):
        errors.append("plan, isometric and fusion layers must stay independent and in that order")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        return errors + ["items must be a non-empty list"]
    seen = set()
    groups = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append("item must be an object")
            continue
        item_id = item.get("id") or "<missing>"
        if not item.get("id") or item["id"] in seen:
            errors.append(f"duplicate or empty id: {item_id}")
        seen.add(item.get("id"))
        groups.add(item.get("group"))
        for field in REQUIRED_FIELDS:
            value = item.get(field)
            if value is None or value == "" or value == []:
                errors.append(f"{item_id}: missing {field}")
        if item.get("status") not in STATUSES:
            errors.append(f"{item_id}: invalid status")
        if item.get("drawing_correct") is not False:
            errors.append(f"{item_id}: S0 cannot mark a drawing correct")
        tests = item.get("tests")
        if item.get("status") == "reproduced":
            if not isinstance(tests, list) or UNTRACKED_TEST in tests:
                errors.append(f"{item_id}: a reproduced rule needs tracked tests")
            elif root is not None:
                for test in tests:
                    if not (Path(root) / test).is_file():
                        errors.append(f"{item_id}: test file missing: {test}")
        elif isinstance(tests, list) and root is not None:
            for test in tests:
                if test != UNTRACKED_TEST and not (Path(root) / test).is_file():
                    errors.append(f"{item_id}: test file missing: {test}")
    missing = [group for group in REQUIRED_GROUPS if group not in groups]
    if missing:
        errors.append("missing groups: " + ", ".join(missing))
    return errors


def mapping_link(kind, plan_ids, isometric_ids, evidence_ids):
    if kind not in MAPPING_KINDS:
        raise ScopeError(f"unknown mapping kind: {kind}")
    if not plan_ids or not isometric_ids or not evidence_ids:
        raise ScopeError("mapping needs both views and source evidence")
    return {
        "kind": kind,
        "plan_ids": list(plan_ids),
        "isometric_ids": list(isometric_ids),
        "evidence_ids": list(evidence_ids),
        "state": "current",
    }


def fusion_record(plan, isometric, mapping, attributes):
    for record, expected in ((plan, "plan_topology"), (isometric, "isometric_topology")):
        if record.get("layer") != expected or not record.get("content_sha256"):
            raise ScopeError("fusion must cite both local topology hashes")
    if not mapping:
        raise ScopeError("fusion requires an explicit mapping")
    return {
        "layer": "cross_view_fusion",
        "plan_sha256": plan["content_sha256"],
        "isometric_sha256": isometric["content_sha256"],
        "mapping": mapping,
        "attributes": attributes,
        "state": "current",
        "human_confirmation": "none",
    }


def invalidate_dependents(record, changed_layers):
    changed = set(changed_layers)
    if not changed <= set(LAYERS):
        raise ScopeError("unknown layer in invalidation")
    updated = json.loads(json.dumps(record))
    if changed & {"plan_topology", "isometric_topology"}:
        for key in ("mapping", "diameter_inheritance", "attribute_fusion"):
            if key in updated:
                updated[key]["state"] = "stale"
                updated[key]["reason"] = "local topology changed; recompute before use"
        updated["state"] = "stale"
        updated["human_confirmation"] = "invalidated_keep_history"
    return updated
