"""Dual-view diameter and length rules.

These functions do not read a drawing and do not repair either topology.
They only accept values that already have a proven same-system connection
or an explicit source view. Unknown stays null. Zero is not a placeholder.
"""

from __future__ import annotations

DIFF_KINDS = (
    "plan_only",
    "isometric_only",
    "branch_mismatch",
    "system_conflict",
    "riser_break",
)


class AttributeError(ValueError):
    pass


def record_difference(kind, plan_evidence, isometric_evidence):
    if kind not in DIFF_KINDS:
        raise AttributeError(f"unknown difference kind: {kind}")
    if not plan_evidence or not isometric_evidence:
        raise AttributeError("both views keep their own evidence")
    return {
        "kind": kind,
        "plan_evidence": plan_evidence,
        "isometric_evidence": isometric_evidence,
        "disposition": "unresolved",
        "may_overwrite_other_view": False,
    }


def inherit_diameter(segments):
    """Inherit one direct diameter through proven same-system links.

    A new direct diameter stays on its own segment. Two different direct
    values in one proven component are a conflict: neither side is rewritten
    and unknown segments are not filled. Unproven links block inheritance.
    """

    index = {}
    for segment in segments:
        if segment["id"] in index:
            raise AttributeError(f"duplicate segment: {segment['id']}")
        if segment.get("direct_diameter") == 0:
            raise AttributeError("unknown diameter must not be stored as zero")
        index[segment["id"]] = segment
    adjacent = {segment_id: set() for segment_id in index}
    for segment in segments:
        for link in segment.get("links", []):
            other = index.get(link["id"])
            if other is None:
                raise AttributeError(f"dangling link from {segment['id']} to {link['id']}")
            if link.get("proven") and other["system"] == segment["system"]:
                adjacent[segment["id"]].add(other["id"])
                adjacent[other["id"]].add(segment["id"])

    seen = set()
    result = {}
    for start in index:
        if start in seen:
            continue
        stack = [start]
        component = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.append(current)
            stack.extend(adjacent[current] - seen)
        directs = {}
        for segment_id in component:
            value = index[segment_id].get("direct_diameter")
            if value is not None:
                directs.setdefault(value, []).append(segment_id)
        distinct = list(directs)
        conflict = len(distinct) > 1
        for segment_id in component:
            own = index[segment_id].get("direct_diameter")
            if conflict:
                status = "conflict"
                value = own
                chain = [item for ids in directs.values() for item in ids]
            elif own is not None:
                status = "direct"
                value = own
                chain = [segment_id]
            elif len(distinct) == 1:
                status = "inherited"
                value = distinct[0]
                chain = directs[value] + [segment_id]
            else:
                status = "unknown"
                value = None
                chain = []
            result[segment_id] = {
                "value": value,
                "status": status,
                "chain": chain,
                "system": index[segment_id]["system"],
            }
    return result


def physical_length(orientation, source_view, value, method):
    """Horizontal length comes from the plan. Vertical length comes from the isometric."""

    expected = {"horizontal": "plan", "vertical": "isometric"}
    if orientation not in expected:
        raise AttributeError(f"unknown orientation: {orientation}")
    if value == 0:
        raise AttributeError("unknown length must not be stored as zero")
    accepted = source_view == expected[orientation] and value is not None and bool(method)
    return {
        "value": value if accepted else None,
        "source_view": source_view,
        "method": method,
        "expected_source": expected[orientation],
        "completeness": "complete" if accepted else "incomplete",
    }
