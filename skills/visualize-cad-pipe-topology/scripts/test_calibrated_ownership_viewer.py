import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from build_visualization import verified_ownership_ancestor
from source_evidence import terminal_geometry
from test_source_evidence import ConfirmedInterfaceNativeGeometry


class OwnershipAncestorTests(unittest.TestCase):
    def test_source_scope_composition_mode_is_replayed_by_its_own_verifier(self):
        from calibrated_ownership_scope_composition import MODE
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'graph.json';parent=Path(folder)/'parent.json';g=dict(sourceLayoutEquipmentOwnership={'records':[1]})
            p.write_text(json.dumps(g));parent.write_text('{}');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            (Path(folder)/'calibrated-equipment-ownership-audit.json').write_text(json.dumps({'mode':MODE}))
            audit=dict(mode=MODE,output_graph_sha256=sha(p),parent_graph=dict(path=str(parent),sha256=sha(parent)))
            with patch('calibrated_ownership_scope_composition.verify_output',return_value=audit) as current,patch('calibrated_equipment_interface_ownership.verify_output') as old:
                self.assertEqual(verified_ownership_ancestor(p,g)[0],parent)
            current.assert_called_once_with(p.parent);old.assert_not_called()
    def test_unbound_edge_claim_and_missing_proof_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'graph.json';p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'lacks verified'):verified_ownership_ancestor(p,dict(edges=[dict(source_layout_equipment_interface={'x':1})]))
            with self.assertRaises(FileNotFoundError):verified_ownership_ancestor(p,dict(sourceLayoutEquipmentOwnership={'x':1}))

    def test_native_replay_parent_and_exact_current_graph(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'graph.json';parent=Path(folder)/'parent.json';g=dict(sourceLayoutEquipmentOwnership={'records':[1]})
            p.write_text(json.dumps(g));parent.write_text('{}');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            audit=dict(output_graph_sha256=sha(p),parent_graph=dict(path=str(parent),sha256=sha(parent)))
            with patch('calibrated_equipment_interface_ownership.verify_output',return_value=audit):
                self.assertEqual(verified_ownership_ancestor(p,g)[0],parent)
                with self.assertRaisesRegex(ValueError,'differs'):verified_ownership_ancestor(p,dict(g,display_edit=True))
                parent.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError,'parent changed'):verified_ownership_ancestor(p,g)

    def test_calibrated_marker_remains_native_without_forged_human_confirmation(self):
        fixture=ConfirmedInterfaceNativeGeometry();fixture.setUp()
        record=fixture.e.pop('confirmed_equipment_interface');record.pop('confirmation')
        record.update(equipment_id='D',edge_id='E',system='supply',status='source_calibrated_logical_ownership',human_accepted=False,
            endpoint_snapshot=dict(start_node_id='T',end_node_id='D',attribute_paths=[[[3,0],[3,4]]]))
        fixture.e['attribute_paths']=[[[3,0],[3,4]]];fixture.e['source_layout_equipment_interface']=record
        fixture.g.update(kind='calibrated_source_equipment_interface',remote_continuation_confirmed=False)
        self.assertEqual(len(fixture.call()),5);self.assertNotIn('confirmation',record)
        for key,value in [('human_accepted',True),('physical_port_verified',True),('equipment_id','OTHER')]:
            altered=copy.deepcopy(fixture.e);altered['source_layout_equipment_interface'][key]=value
            with self.assertRaises(ValueError):terminal_geometry(fixture.doc,fixture.g,{'D':fixture.n},{'E':altered})
        fixture.g['kind']='confirmed_equipment_interface'
        with self.assertRaises(ValueError):fixture.call()


if __name__=='__main__':unittest.main()
