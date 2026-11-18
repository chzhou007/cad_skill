import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from confirm_crossview_paths import sha
from plan_calibrated_DN_scopes import verify_topology_parent


class SideviewDNParentTests(unittest.TestCase):
    def test_new_root_and_edge_claim_replay_current_layer_before_old_parent(self):
        for graph in [dict(sourceSideviewEquipmentOwnership={},sourceLayoutEquipmentOwnership={'records':[1]}),dict(edges=[dict(source_sideview_equipment_interface={})])]:
            with tempfile.TemporaryDirectory() as folder:
                p=Path(folder)/'graph_with_edges.json';p.write_bytes(b'fixed graph');audit=dict(output_graph_sha256=sha(p))
                with patch('reconstruct_sideview_equipment_ownership.verify_output',return_value=audit) as current,patch('plan_calibrated_DN_scopes.verify_ownership_output') as old:
                    self.assertEqual(verify_topology_parent(p,graph),audit)
                current.assert_called_once_with(p.parent);old.assert_not_called()

    def test_bad_or_missing_new_evidence_never_falls_back_to_retained_old_root(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'graph_with_edges.json';p.write_bytes(b'fixed graph');graph=dict(sourceSideviewEquipmentOwnership={},sourceLayoutEquipmentOwnership={'records':[1]})
            for mode in ('mismatch','missing'):
                with patch('reconstruct_sideview_equipment_ownership.verify_output',return_value=dict(output_graph_sha256='OTHER'),side_effect=ValueError('missing new native evidence') if mode=='missing' else None),patch('plan_calibrated_DN_scopes.verify_ownership_output') as old:
                    with self.assertRaises(ValueError):verify_topology_parent(p,graph)
                old.assert_not_called()

    def test_legacy_ownership_entry_retains_its_verifier_and_hash_check(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'graph_with_edges.json';p.write_bytes(b'fixed graph')
            with patch('plan_calibrated_DN_scopes.verify_ownership_output',return_value=dict(output_graph_sha256=sha(p))) as old,patch('reconstruct_sideview_equipment_ownership.verify_output') as current:
                verify_topology_parent(p,dict(sourceLayoutEquipmentOwnership={'records':[1]}))
            old.assert_called_once_with(p.parent);current.assert_not_called()
            with patch('plan_calibrated_DN_scopes.verify_ownership_output',return_value=dict(output_graph_sha256='OTHER')):
                with self.assertRaisesRegex(ValueError,'ownership differs'):verify_topology_parent(p,{})


if __name__=='__main__':unittest.main()
