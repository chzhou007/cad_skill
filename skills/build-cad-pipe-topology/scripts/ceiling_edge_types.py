"""Edge types for SH16 ceiling sheets 08-10.

The label follows the endpoint node records already built from source
contacts. It does not create a port, move geometry, or connect equipment
whose connection_status is still unresolved.
"""

_KINDS = {
    "tee": "tee",
    "equipment": "equipment",
    "virtual_equipment": "virtual_equipment",
}


def endpoint_role(node):
    kind = _KINDS.get(node.get("node_type"))
    if kind is None:
        raise ValueError("unknown node type: " + str(node.get("node_type")))
    if not node.get("node_id"):
        raise ValueError("endpoint node has no id")
    return {"kind": kind, "id": node["node_id"], "subtype": node.get("subtype")}


def ceiling_edge_type(start_node, end_node):
    kinds = {endpoint_role(start_node)["kind"], endpoint_role(end_node)["kind"]}
    if "equipment" in kinds:
        return "tee_to_equipment"
    if "virtual_equipment" in kinds:
        return "tee_to_virtual_equipment"
    return "tee_to_tee"
