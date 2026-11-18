import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from build_visualization import verified_sideview_ownership_ancestor
from source_evidence import sideview_interface_glyph,terminal_geometry
from test_source_evidence import ConfirmedInterfaceNativeGeometry


class SideviewOwnershipViewerTests(unittest.TestCase):
    def test_ancestry_replays_exact_current_then_returns_old_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'graph.json';parent=root/'parent.json';g=dict(sourceSideviewEquipmentOwnership={})
            p.write_text(json.dumps(g));parent.write_text('{}');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            audit=dict(output_graph_sha256=sha(p),parent_graph=dict(path=str(parent),sha256=sha(parent)))
            with patch('reconstruct_sideview_equipment_ownership.verify_output',return_value=audit) as replay:
                self.assertEqual(verified_sideview_ownership_ancestor(p,g),(parent,audit));replay.assert_called_once_with(p.parent)
                with self.assertRaisesRegex(ValueError,'differs'):verified_sideview_ownership_ancestor(p,dict(g,edited=True))
                parent.write_text('changed')
                with self.assertRaisesRegex(ValueError,'parent changed'):verified_sideview_ownership_ancestor(p,g)

    def test_edge_without_stage_cannot_fall_back(self):
        with self.assertRaisesRegex(ValueError,'lacks verified'):
            verified_sideview_ownership_ancestor(Path('unused'),dict(edges=[dict(source_sideview_equipment_interface={})]))

    def test_native_detail_glyphs_keep_both_endpoint_roles_and_original_coordinates(self):
        for boundary in (False,True):
            f=ConfirmedInterfaceNativeGeometry();f.setUp();original=f.e.pop('confirmed_equipment_interface')['original_interface']
            record=dict(equipment_id='D',edge_id='E',interface_side='end',original_canonical_interface_id='B' if boundary else 'V1',
                original_canonical_interface_kind='non_node_boundary' if boundary else 'node',
                original_canonical_endpoint=dict(boundary_id='B',legacy_node=original) if boundary else original,
                endpoint_floor_evidence={'floor':2})
            f.e['source_sideview_equipment_interface']=record;graph=dict(metadata={'source_sha256':'S'},nodes=[f.n],edges=[f.e])
            with patch('native_sideview_equipment_branch_evidence.validate_owner',return_value=record):
                glyph=sideview_interface_glyph(graph,f.e);before=copy.deepcopy(graph)
                self.assertEqual(len(terminal_geometry(f.doc,glyph,{'D':f.n},{'E':f.e},graph=graph)),5)
                self.assertEqual(graph,before);self.assertFalse(glyph['remote_continuation_confirmed'])
                with self.assertRaisesRegex(ValueError,'complete ownership'):terminal_geometry(f.doc,glyph,{'D':f.n},{'E':f.e})
                glyph['system']='return'
                with self.assertRaisesRegex(ValueError,'identity differs'):terminal_geometry(f.doc,glyph,{'D':f.n},{'E':f.e},graph=graph)
                glyph['system']='supply';f.e['path_points'][-1]=[8,4]
                with self.assertRaisesRegex(ValueError,'endpoint'):terminal_geometry(f.doc,glyph,{'D':f.n},{'E':f.e},graph=graph)

    def test_stale_owner_is_rejected_before_source_display(self):
        with patch('native_sideview_equipment_branch_evidence.validate_owner',side_effect=ValueError('stale alias')):
            with self.assertRaisesRegex(ValueError,'stale alias'):sideview_interface_glyph({'metadata':{}},{})

    def test_legacy_boundary_pipe_handle_is_not_misrepresented_as_full_interface_glyph(self):
        f=ConfirmedInterfaceNativeGeometry();f.setUp();original=f.e.pop('confirmed_equipment_interface')['original_interface']
        pipe=f.doc.modelspace().add_line((3,0),(3,4),dxfattribs={'layer':'空调冷冻水供水'})
        f.e['source_handles']=[pipe.dxf.handle]
        boundary=dict(boundary_id='B',kind='expert_non_node_source_boundary',x=3,y=4,source_pipe_handle=pipe.dxf.handle,source_circle_handle=original['source_handle'],legacy_node=dict(original,source_handles=[pipe.dxf.handle]))
        record=dict(equipment_id='D',edge_id='E',interface_side='end',original_canonical_interface_id='B',original_canonical_interface_kind='non_node_boundary',original_canonical_endpoint=boundary,endpoint_floor_evidence={'floor':2})
        f.e['source_sideview_equipment_interface']=record;graph=dict(metadata={'source_sha256':'S'},nodes=[f.n],edges=[f.e])
        with patch('native_sideview_equipment_branch_evidence.validate_owner',return_value=record):
            glyph=sideview_interface_glyph(graph,f.e)
            self.assertEqual(glyph['native_glyph_scope'],'recorded_boundary_circle_only')
            self.assertEqual(glyph['source_handles'],[original['source_handle']])
            self.assertEqual(len(terminal_geometry(f.doc,glyph,{'D':f.n},{'E':f.e},graph=graph)),1)
            circle=f.doc.entitydb[original['source_handle']];circle.dxf.center=(3.4273,4,0)
            self.assertEqual(len(terminal_geometry(f.doc,glyph,{'D':f.n},{'E':f.e},graph=graph)),1)
            circle.dxf.center=(4.1,4,0)
            with self.assertRaisesRegex(ValueError,'center changed'):terminal_geometry(f.doc,glyph,{'D':f.n},{'E':f.e},graph=graph)
            circle.dxf.center=(3,4,0)
            boundary['source_glyph_handles']=original['source_handles'][1:]
            glyph=sideview_interface_glyph(graph,f.e);self.assertEqual(len(glyph['source_handles']),5)
            self.assertEqual(len(terminal_geometry(f.doc,glyph,{'D':f.n},{'E':f.e},graph=graph)),5)
            boundary['source_glyph_handles']=[]
            with self.assertRaises(ValueError):sideview_interface_glyph(graph,f.e)


if __name__=='__main__':unittest.main()
