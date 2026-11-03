import unittest

from ceiling_edge_types import ceiling_edge_type, endpoint_role


def node(node_id, node_type, subtype=None):
    row = {"node_id": node_id, "node_type": node_type}
    if subtype is not None:
        row["subtype"] = subtype
    return row


class CeilingEdgeTypeTest(unittest.TestCase):
    def test_riser_and_unresolved_terminal_are_not_physical_tees(self):
        tee = node("T001", "tee", "physical_tee")
        riser = node("RIF001", "virtual_equipment", "out_of_plane_riser")
        pending = node("UT0001", "virtual_equipment", "unresolved_source_terminal")
        junction = node("UT0002", "virtual_equipment", "pending_source_junction")
        vif = node("VIF001", "virtual_equipment", "out_of_plane_interface")
        self.assertEqual(ceiling_edge_type(tee, riser), "tee_to_virtual_equipment")
        self.assertEqual(ceiling_edge_type(tee, pending), "tee_to_virtual_equipment")
        self.assertEqual(ceiling_edge_type(tee, junction), "tee_to_virtual_equipment")
        self.assertEqual(ceiling_edge_type(tee, vif), "tee_to_virtual_equipment")
        self.assertEqual(ceiling_edge_type(tee, dict(tee, node_id="T002")), "tee_to_tee")

    def test_role_records_the_virtual_endpoint_and_adds_no_port(self):
        role = endpoint_role(node("UT0001", "virtual_equipment", "pending_source_junction"))
        self.assertEqual(role["kind"], "virtual_equipment")
        self.assertEqual(role["id"], "UT0001")
        self.assertNotIn("port_id", role)

    def test_existing_equipment_endpoint_is_not_relabeled_as_a_tee(self):
        tee = node("T001", "tee", "physical_tee")
        equipment = node("CRAH-4#-2-2", "equipment", "CRAH")
        equipment["connection_status"] = "ports_unresolved"
        self.assertEqual(ceiling_edge_type(tee, equipment), "tee_to_equipment")

    def test_unknown_node_type_fails(self):
        tee = node("T001", "tee")
        with self.assertRaises(ValueError):
            ceiling_edge_type(tee, {"node_id": "L1", "node_type": "label"})


if __name__ == "__main__":
    unittest.main()
