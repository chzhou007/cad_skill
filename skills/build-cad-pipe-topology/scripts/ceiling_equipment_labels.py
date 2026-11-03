"""Label identity for SH16 ceiling equipment.

A label inside the source bounds is that block's candidate. A label only
inside the expanded box is a candidate when no other block selected it.
A shared label stays unresolved. This does not create a supply or return port.
"""


def _covers(bounds, label, pad):
    (x0, y0), (x1, y1) = bounds
    return x0 - pad <= label["x"] <= x1 + pad and y0 - pad <= label["y"] <= y1 + pad


def _selected(block, labels, tolerance, halo):
    inside = [label for label in labels if _covers(block["bounds"], label, tolerance)]
    if inside:
        return inside
    return [label for label in labels if _covers(block["bounds"], label, halo)]


def bind_ceiling_equipment_labels(blocks, labels, tolerance=0.05, halo=600.0):
    selected = [_selected(block, labels, tolerance, halo) for block in blocks]
    owners = {}
    for block, hits in zip(blocks, selected):
        for text in {label["text"] for label in hits}:
            owners.setdefault(text, []).append(block["source_handle"])
    rows = []
    for block, hits in zip(blocks, selected):
        texts = [label["text"] for label in hits]
        shared = len(texts) == 1 and owners[texts[0]] != [block["source_handle"]]
        status = "unique_bounded_source_label" if len(texts) == 1 and not shared else "label_unresolved"
        rows.append({
            "source_handle": block["source_handle"],
            "label_candidates": texts,
            "association_status": status,
            "connection_status": "ports_unresolved",
        })
    return rows
