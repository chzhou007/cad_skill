import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from build_visualization import verified_identity_ancestor,native_equipment_display_handles,normalize_instance_position,normalize_legacy_component_inventory,native_component_display_reference
import ezdxf

class IdentityAncestorTests(unittest.TestCase):
    def test_sparse_canonical_component_reference_requires_native_insert_identity(self):
        doc=ezdxf.new();block=doc.blocks.new('VALVE');block.add_line((0,0),(10,0));insert=doc.modelspace().add_blockref('VALVE',(0,0))
        row=dict(source_kind='block_reference',source_handle=insert.dxf.handle,source_block_name='VALVE')
        self.assertEqual(native_component_display_reference(row,doc,'S','S'),insert.dxf.handle);self.assertNotIn('source_top_handle',row)
        self.assertIsNone(native_component_display_reference(row,doc,'wrong','S'))
        row['source_block_name']='OTHER';self.assertIsNone(native_component_display_reference(row,doc,'S','S'))
    def test_legacy_component_adapter_requires_exact_counts_and_names(self):
        graph={'edges':[dict(edge_id='E',equipment_counts={'valve':1},equipment_names=['V'])]};rows=[dict(edge_id='E',equipment_type='valve',device_name='V')]
        self.assertEqual(normalize_legacy_component_inventory(graph,rows),['E']);self.assertEqual(graph['edges'][0]['equipment_inventory'][0]['device_names'],['V']);self.assertFalse(graph['legacyInventoryDisplayAdapter']['physical_assignment_changed'])
        for key,value in [('equipment_counts',{'valve':2}),('equipment_names',['OTHER'])]:
            bad={'edges':[dict(edge_id='E',equipment_counts={'valve':1},equipment_names=['V'])]};bad['edges'][0][key]=value
            with self.assertRaisesRegex(ValueError,'differs'):normalize_legacy_component_inventory(bad,rows)
    def test_sparse_native_audit_uses_its_source_anchor_only_for_display(self):
        row=dict(x='3.5',y='7',edge_distance='.5',edge_id='E')
        normalize_instance_position(row,'component');self.assertEqual((row['assignment_x'],row['assignment_y']),(3.5,7));self.assertEqual(row['edge_id'],'E')
        row=dict(x=3,y=7,assignment_x=4,assignment_y=8,edge_distance=.5)
        normalize_instance_position(row,'component');self.assertEqual((row['assignment_x'],row['assignment_y']),(4,8));self.assertNotIn('display_assignment_basis',row)
        with self.assertRaisesRegex(ValueError,'incomplete'):normalize_instance_position(dict(x=3,y=7,assignment_x=4,edge_distance=.5),'component')
    def test_native_body_display_does_not_require_hand_edits_or_imply_ports(self):
        doc=ezdxf.new();block=doc.blocks.new('BODY');block.add_lwpolyline([(0,0),(10,0),(10,10),(0,10)],close=True);insert=doc.modelspace().add_blockref('BODY',(0,0))
        node=dict(node_id='EQ',node_type='equipment',source_handle=insert.dxf.handle,source_block='BODY',x=5,y=5,connection_status='ports_unresolved')
        self.assertEqual(native_equipment_display_handles(node,doc,'S','S'),[insert.dxf.handle]);self.assertEqual(node['connection_status'],'ports_unresolved');self.assertNotIn('display_source_handles',node)
        self.assertEqual(native_equipment_display_handles(node,doc,'wrong','S'),[])
        node['x']+=1;self.assertEqual(native_equipment_display_handles(node,doc,'S','S'),[])
    def test_unbound_node_flag_and_missing_stage_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            graph=Path(folder)/'graph.json';graph.write_text('{}')
            with self.assertRaisesRegex(ValueError,'lack verified'):verified_identity_ancestor(graph,dict(nodes=[dict(source_identity_evidence=dict(rule='robust_rotated_caption_footprint'))]))
            with self.assertRaises(FileNotFoundError):verified_identity_ancestor(graph,dict(sourceEquipmentIdentityResolution={'claim':True}))
    def test_independent_native_replay_and_unchanged_parent_are_required(self):
        with tempfile.TemporaryDirectory() as folder:
            graph=Path(folder)/'graph.json';parent=Path(folder)/'parent.json';data={'sourceEquipmentIdentityResolution':{'records':[1]}}
            graph.write_text(json.dumps(data));parent.write_text('{}');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            audit=dict(output_graph_sha256=sha(graph),parent_graph=dict(path=str(parent),sha256=sha(parent)))
            with patch('resolve_rotated_equipment_labels.verify_output',return_value=audit):
                self.assertEqual(verified_identity_ancestor(graph,data)[0],parent)
                with self.assertRaisesRegex(ValueError,'differs'):verified_identity_ancestor(graph,dict(data,changed=True))
                parent.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError,'parent changed'):verified_identity_ancestor(graph,data)

if __name__=='__main__':unittest.main()
