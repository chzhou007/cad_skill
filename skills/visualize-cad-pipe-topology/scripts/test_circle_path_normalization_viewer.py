import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from build_visualization import verified_circle_path_ancestor
from source_evidence import terminal_geometry
from test_source_evidence import ConfirmedInterfaceNativeGeometry

class CircleViewerTests(unittest.TestCase):
    def test_native_interface_reuses_parent_ownership_only_after_circle_source_replay(self):
        import copy
        f=ConfirmedInterfaceNativeGeometry();f.setUp()
        record=f.e.pop('confirmed_equipment_interface');record.pop('confirmation')
        before=dict(start_node_id='T',end_node_id='D',system='supply',attribute_paths=[[[3,0],[3,4]]])
        record.update(equipment_id='D',edge_id='E',system='supply',status='source_calibrated_logical_ownership',human_accepted=False,source_sha256='S',endpoint_snapshot=copy.deepcopy(before))
        f.e.update(source_layout_equipment_interface=record,attribute_paths=[[[3,1],[3,4]]],physical_length='unknown',path_length_complete=False)
        f.e['source_circle_path_normalization']=dict(node_id='T',source_sha256='S',human_accepted=False,physical_connector_length=None,input_snapshot=before,output_snapshot=dict(before,attribute_paths=copy.deepcopy(f.e['attribute_paths'])))
        f.g.update(kind='calibrated_source_equipment_interface',remote_continuation_confirmed=False)
        with patch('native_circle_rim_junction_evidence.collect',return_value={}) as native:
            self.assertEqual(len(f.call()),5);native.assert_called_once()
        with patch('native_circle_rim_junction_evidence.collect',side_effect=ValueError('source contact not reproducible')):
            with self.assertRaisesRegex(ValueError,'not reproducible'):f.call()
        f.e['attribute_paths'][0][0]=[99,99]
        with self.assertRaisesRegex(ValueError,'snapshot'):f.call()

    def test_edge_claim_requires_root_and_parent_replay(self):
        with self.assertRaises(ValueError):verified_circle_path_ancestor(Path('missing'),dict(edges=[dict(source_circle_path_normalization={'edge_id':'E'})]))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);parent=root/'parent.json';parent.write_text('{}');child=root/'graph_with_edges.json';g=dict(sourceCirclePathNormalization={'records':[1]});child.write_text(json.dumps(g))
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            audit=dict(parent_graph=dict(path=str(parent),sha256=sha(parent)),output_graph_sha256=sha(child))
            with patch('normalize_plan_circle_paths.verify_output',return_value=audit):self.assertEqual(verified_circle_path_ancestor(child,g),(parent,audit))
            parent.write_text('{"changed":true}')
            with patch('normalize_plan_circle_paths.verify_output',return_value=audit):
                with self.assertRaises(ValueError):verified_circle_path_ancestor(child,g)

if __name__=='__main__':unittest.main()
