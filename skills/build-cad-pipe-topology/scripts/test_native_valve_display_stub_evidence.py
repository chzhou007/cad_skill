import copy,unittest
import ezdxf
from native_line_path_evidence import LAYERS
from native_valve_display_stub_evidence import collect,replay_normalization,qualify


def fixture(rotation=0,mirror=1):
    doc=ezdxf.new('R2018');shape=doc.blocks.new('H-PICPNT-87')
    for a,b in [((-10,-10),(10,-10)),((10,-10),(10,10)),((10,10),(-10,10)),((-10,10),(-10,-10))]:shape.add_line(a,b)
    body=doc.blocks.new('BODY');a=body.add_line((-100,0),(0,0),dxfattribs=dict(layer=LAYERS['supply']));b=body.add_line((0,0),(0,100),dxfattribs=dict(layer=LAYERS['supply']))
    valve=body.add_blockref('H-PICPNT-87',(40,0));attached=body.add_line((0,0),(30,0),dxfattribs=dict(layer=LAYERS['supply']));free=body.add_line((50,0),(70,0),dxfattribs=dict(layer=LAYERS['supply']))
    root=doc.modelspace().add_blockref('BODY',(200,300),dxfattribs=dict(rotation=rotation,xscale=mirror));matrix=root.matrix44()
    path=[[matrix.transform((*p,0)).x,matrix.transform((*p,0)).y] for p in [(-100,0),(0,0),(0,100)]]
    edge=dict(edge_id='PIPE',system='supply',source_insert_handle=root.dxf.handle,attribute_paths=[path],source_native_block_branch=dict(source_insert_handle=root.dxf.handle,endpoint_snapshot=dict(attribute_paths=copy.deepcopy([path]))))
    graph=dict(metadata=dict(source_sha256='S'),edges=[edge]);selection=dict(root_handle=root.dxf.handle,valve_handle=valve.dxf.handle,free_line_handle=free.dxf.handle,attached_line_handle=attached.dxf.handle,expected_valve_name='H-PICPNT-87')
    policy=dict(source_sha256='S',graph_sha256='G',system_layers={v:k for k,v in LAYERS.items()},selections=[selection])
    return doc,graph,policy


class NativeDisplayStubEvidenceTests(unittest.TestCase):
    def test_opposite_stem_qualified_only_after_actual_inherited_attached_stem_removal(self):
        for rotation,mirror in [(0,1),(90,1),(180,-1),(270,-1)]:
            doc,g,p=fixture(rotation,mirror);before=copy.deepcopy(g);r=collect(doc,g,p,'S','G')
            self.assertEqual(g,before);self.assertEqual(len(r['records']),1);self.assertEqual(r['inherited_turn_display_removals'],1)
            item=r['records'][0];self.assertTrue(item['excluded_only_from_DN_pipe_competition']);self.assertEqual(item['current_graph_corner']['edge_id'],'PIPE');self.assertEqual(r['DN_values_assigned'],0)
    def test_real_pipe_at_free_endpoint_or_active_graph_stem_is_never_excluded(self):
        for case in ('source_connected','active_graph'):
            doc,g,p=fixture();root=doc.entitydb[p['selections'][0]['root_handle']];children={e.source_of_copy.dxf.handle:e for e in root.virtual_entities()};line=children[p['selections'][0]['free_line_handle']]
            if case=='source_connected':
                tail=line.dxf.end;doc.modelspace().add_line(tail,(tail.x,tail.y+100),dxfattribs=dict(layer=LAYERS['supply']))
            else:g['edges'].append(dict(edge_id='ACTIVE',system='supply',attribute_paths=[[list(line.dxf.start)[:2],list(line.dxf.end)[:2]]]))
            with self.subTest(case=case),self.assertRaises(ValueError):collect(doc,g,p,'S','G')
    def test_unproven_or_wrong_sibling_and_symbol_cannot_remove_a_competitor(self):
        for case in ('no_removal','wrong_sibling','unknown_symbol','duplicate'):
            doc,g,p=fixture()
            if case=='no_removal':
                n=replay_normalization(doc,p['system_layers']);n['removals']=[]
                with self.assertRaisesRegex(ValueError,'inherited'):qualify(doc,g,p['selections'][0],n)
                continue
            if case=='wrong_sibling':p['selections'][0]['attached_line_handle']=p['selections'][0]['free_line_handle']
            elif case=='unknown_symbol':p['selections'][0]['expected_valve_name']='UNKNOWN'
            else:p['selections'].append(copy.deepcopy(p['selections'][0]))
            with self.subTest(case=case),self.assertRaises(ValueError):collect(doc,g,p,'S','G')
    def test_long_changed_Z_or_disconnected_graph_corner_remains_pending(self):
        for case in ('long','Z','corner','missing_snapshot'):
            doc,g,p=fixture();item=p['selections'][0]
            if case=='long':doc.entitydb[item['free_line_handle']].dxf.end=(500,0,0)
            elif case=='Z':doc.entitydb[item['free_line_handle']].dxf.start=(50,0,1)
            elif case=='corner':g['edges'][0]['attribute_paths']=[[[100,300],[200,300],[300,300]]];g['edges'][0]['source_native_block_branch']['endpoint_snapshot']['attribute_paths']=copy.deepcopy(g['edges'][0]['attribute_paths'])
            else:g['edges'][0]['source_native_block_branch']['endpoint_snapshot']={}
            with self.subTest(case=case),self.assertRaises(ValueError):collect(doc,g,p,'S','G')
    def test_private_legacy_replay_does_not_change_another_pipeline_global_layer_detector(self):
        from legacy_v17 import analyze_graph as legacy
        before=legacy.get_system_layers;doc,g,p=fixture();collect(doc,g,p,'S','G');self.assertIs(legacy.get_system_layers,before)
    def test_wrong_source_binding_or_layers_is_rejected_before_qualification(self):
        for case in ('source','graph','layers'):
            doc,g,p=fixture()
            if case=='source':p['source_sha256']='OTHER'
            elif case=='graph':p['graph_sha256']='OTHER'
            else:p['system_layers']={'ARCH':'supply'}
            with self.subTest(case=case),self.assertRaises(ValueError):collect(doc,g,p,'S','G')


if __name__=='__main__':unittest.main()
